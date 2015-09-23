#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

import datetime
import traceback
import simplejson

from aws_federation_proxy import (
    AWSFederationProxy,
    ConfigurationError,
    AWSError,
    PermissionError
)
from functools import wraps
from yamlreader import yaml_load
from bottle import route, abort, request, response, error, default_app
from aws_federation_proxy.util import setup_logging


def with_exception_handling(old_function):
    """Decorator function to ensure proper exception handling"""
    @wraps(old_function)
    def new_function(*args, **kwargs):
        try:
            result = old_function(*args, **kwargs)
        except ConfigurationError as err:
            abort(404, err)
        except AWSError as err:
            abort(502, err)
        except PermissionError as err:
            abort(403, err)
        except Exception:
            message = traceback.format_exc()
            abort(500, "Exception caught {0}".format(message))
        return result
    return new_function


def initialize_federation_proxy(user=None):
    """Get needed config parts and initialize AWSFederationProxy"""
    config_path = request.environ.get('CONFIG_PATH')
    if config_path is None:
        raise Exception("No Config Path specified")
    config = yaml_load(config_path)
    account_config_path = request.environ.get('ACCOUNT_CONFIG_PATH')
    if account_config_path is None:
        raise Exception("No Account Config Path specified")
    account_config = yaml_load(account_config_path)

    if user is None:
        user = get_user(config['api']['user_identification'])

    handler_config = config.get('logging_handler')
    try:
        logger = setup_logging(handler_config, logger_name='AWSFederationProxy')
    except Exception as exc:
        raise ConfigurationError(str(exc))
    proxy = AWSFederationProxy(user=user, config=config,
                               account_config=account_config, logger=logger)
    return proxy


def get_user(user_config):
    """
    user_config = {
        'environment_field': REMOTE_USER
    }
    """
    field = user_config['environment_field']
    if field in request.environ:
        return request.environ[field]

    raise Exception("No {0} specified".format(field))


def build_credentials_dict(credentials):
    """Convert AWS Credential object to a dict"""
    return {
        'Code': 'Success',
        'Type': 'AWS-HMAC',
        'AccessKeyId': credentials.access_key,
        'SecretAccessKey': credentials.secret_key,
        'Token': credentials.session_token,
        'Expiration': credentials.expiration,
        'LastUpdated': datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    }


@error(403)
@error(404)
@error(500)
@error(502)
def get_error_json(err):
    try:
        proxy = initialize_federation_proxy()
    except Exception:
        user = "Unknown User"
    else:
        user = proxy.user
    response_dict = {
        "status": err.status_code,
        "error": err.status,
        "exception": None,
        "message": str(err.body),
        "traceback": err.traceback
    }
    response.set_header('X-Username', user)
    response.content_type = 'application/json; charset=utf-8'
    return simplejson.dumps(response_dict)


def get_proxy_return_json(user=None):
    """A decorator to set up the proxy and convert output into JSON"""
    def decorator(old_function):
        @wraps(old_function)
        def new_function(*args, **kwargs):
            proxy = initialize_federation_proxy(user=user)
            response.set_header('X-Username', proxy.user)
            return_value = old_function(proxy, *args, **kwargs)
            response.content_type = 'application/json; charset=utf-8'
            return simplejson.dumps(return_value)
        return new_function
    return decorator


@route("/status")
@with_exception_handling
@get_proxy_return_json(user='monitoring')
def get_monitoring_status(proxy):
    """Return status page for monitoring"""
    return {"status": "200", "message": "OK"}


@route('/account')
@with_exception_handling
@get_proxy_return_json()
def get_accountlist(proxy):
    """Return a dict-of-lists of all accounts and roles for the current user"""
    def role_set_to_list(role_set):
        """Convert a set of (role, reason) tuples to a list of roles"""
        return [role for role, reason in role_set]
    accounts_and_roles_with_sets = proxy.get_account_and_role_dict()
    accounts_and_roles = dict(
        (key, role_set_to_list(value)) for (key, value)
        in accounts_and_roles_with_sets.items()
    )
    return accounts_and_roles


@route('/account/<account>/<role>')
@with_exception_handling
@get_proxy_return_json()
def get_credentials_and_console(proxy, account, role):
    """ Return credentials and console url

    Return a dict of credentials (access_key, secret_key and session token)
    and ConsoleURL for the specified role in the specified account
    """
    callback_url = request.query.callbackurl or ""
    credentials = proxy.get_aws_credentials(account, role)
    credentials_dict = build_credentials_dict(credentials)
    credentials_dict['ConsoleUrl'] = proxy.get_console_url(credentials,
                                                           callback_url)
    return credentials_dict


@route('/account/<account>/<role>/credentials')
@with_exception_handling
@get_proxy_return_json()
def get_credentials(proxy, account, role):
    """Return credentials

    Return a dict of credentials (AccessKeyId, SecretAccessKey, Token)
    for the specified role in the specified account.
    """
    credentials = proxy.get_aws_credentials(account, role)
    return build_credentials_dict(credentials)


@route('/account/<account>/<role>/consoleurl')
@with_exception_handling
def get_console(account, role):
    """Return ConsoleURL

    Return string of the console URL for the specified role and account
    """
    proxy = initialize_federation_proxy()
    callback_url = request.query.callbackurl or ""
    credentials = proxy.get_aws_credentials(account, role)
    console_url = proxy.get_console_url(credentials, callback_url)
    response.content_type = 'text/plain; charset=utf-8'
    return str(console_url)


def get_account_and_role(proxy):
    accounts_and_roles = proxy.get_account_and_role_dict()
    if len(accounts_and_roles) != 1:
        raise ConfigurationError("Did not get exactly one account: %s" % (
            accounts_and_roles))

    roles = list(accounts_and_roles.values())[0]
    if len(roles) != 1:
        raise ConfigurationError("Did not get exactly one role: %s" % (
            accounts_and_roles))

    account = list(accounts_and_roles.keys())[0]
    role = list(roles)[0][0]
    return account, role


@route('/meta-data/iam/security-credentials/')
@with_exception_handling
def get_ims_role():
    proxy = initialize_federation_proxy()
    _, role = get_account_and_role(proxy)
    response.content_type = 'text/plain'
    return role


@route('/meta-data/iam/security-credentials/<role>')
@with_exception_handling
@get_proxy_return_json()
def get_ims_credentials(proxy, role):
    account, _ = get_account_and_role(proxy)
    try:
        credentials = proxy.get_aws_credentials(account, role)
    except PermissionError as exc:
        abort(404, exc)
    return build_credentials_dict(credentials)


def get_webapp():
    """Give back the bottle default_app, for direct use in wsgi scripts"""
    return default_app()
