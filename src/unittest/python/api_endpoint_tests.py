#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division

import datetime
import os
import tempfile
import shutil
import yaml
import logging
import aws_federation_proxy.wsgi_api as wsgi_api
from aws_federation_proxy.util import setup_logging

from moto import mock_sts
from six.moves.urllib.parse import quote_plus
from webtest import TestApp
from unittest2 import TestCase
from mock import patch, Mock
from aws_federation_proxy import AWSError, PermissionError

# Else we run into problems with mocking
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['no_proxy'] = ''

SESSION_TOKEN = (
    u"BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+"
    u"FvwqnKwRcOIfrRh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniC"
    u"EXAMPLE/IvU1dYUg2RVAJBanLiHb4IgRmpRV3zrkuWJOgQs8"
    u"IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/AXlzBBko7b15fjr"
    u"Bs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE"
)
CREDENTIALS = {
    'Code': 'Success',
    'Type': "AWS-HMAC",
    'AccessKeyId': u'AKIAIOSFODNN7EXAMPLE',
    'SecretAccessKey': u'aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
    'Token': SESSION_TOKEN
}


class BaseEndpointTest(TestCase):
    def setUp(self):
        self.user = 'testuser'
        self.config_path = tempfile.mkdtemp(prefix='afp-config-')
        self.account_config_path = tempfile.mkdtemp(
            prefix='afp-account-config-')
        self.logger = logging.getLogger('AWSFederationProxy')
        self.log_file = tempfile.NamedTemporaryFile(prefix='afp-test-')

        self.basicconfig = {
            'api': {
                'user_identification': {
                    'environment_field': 'REMOTE_USER'
                }
            },
            'aws': {
                'access_key': 'accesskey',
                'secret_key': 'secretkey'
            },
            'logging_handler': {
                'module': 'logging',
                'class': 'FileHandler',
                'args': [self.log_file.name],
                'kwargs': {}
            },
        }
        self.environment = dict(
            REMOTE_USER=self.user,
            CONFIG_PATH=self.config_path,
            ACCOUNT_CONFIG_PATH=self.account_config_path
        )
        self.providerconfig = {
            'provider': {
                'module': 'aws_federation_proxy.provider.base_provider',
                'class': 'GroupTestProvider',
                'regex': '(?P<account>.*)-(?P<role>.*)'
            }
        }
        self.accountconfig = {
            'testaccount': {
                'id': '123456789'
            },
            'nonaccessibleaccount': {
                'id': '987654321'
            },
            'the_only_account': {
                'id': '424242'
            }
        }

        self._create_app()

    def _create_app(self):
        self.writeyaml(
            self.basicconfig,
            os.path.join(self.config_path, "basic.yaml")
        )
        self.writeyaml(
            self.providerconfig,
            os.path.join(self.config_path, "provider.yaml")
        )
        self.writeyaml(
            self.accountconfig,
            os.path.join(self.account_config_path, "accounts.yaml")
        )
        self.app = TestApp(wsgi_api.get_webapp(), extra_environ=self.environment)

    @staticmethod
    def writeyaml(data, yamlfile):
        with open(yamlfile, "w") as target:
            target.write(yaml.dump(data))

    def tearDown(self):
        shutil.rmtree(self.config_path)
        shutil.rmtree(self.account_config_path)
        os.unlink(self.log_file.name)
        if self.logger.handlers:
            self.logger.removeHandler(self.logger.handlers[0])


class AWSEndpointTest(BaseEndpointTest):
    @mock_sts
    def test_get_my_role(self):
        self.providerconfig['provider']['class'] = "SingleAccountSingleRoleProvider"
        self._create_app()

        result = self.app.get('/meta-data/iam/security-credentials/')
        self.assertEqual(result.status_int, 200)
        self.assertEqual(result.body, "the_only_role".encode())

    def test_get_my_role_must_fail_if_multiple_roles_from_provider(self):
        result = self.app.get('/meta-data/iam/security-credentials/', expect_errors=True)
        self.assertNotEqual(result.status_int, 200)

    def test_get_my_role_must_fail_if_no_roles_from_provider(self):
        self.providerconfig['provider']['class'] = "NoAccountNoRoleProvider"
        self._create_app()

        result = self.app.get('/meta-data/iam/security-credentials/', expect_errors=True)
        self.assertEqual(result.status_int, 404)

    @patch("aws_federation_proxy.AWSFederationProxy.get_aws_credentials")
    def test_get_my_role_must_return_empty_success_if_role_not_exists_in_aws(self, mock_get_aws_credentials):
        self.providerconfig['provider']['class'] = "SingleAccountSingleRoleProvider"
        self._create_app()

        mock_get_aws_credentials.side_effect = PermissionError("Foo")
        result = self.app.get('/meta-data/iam/security-credentials/')
        self.assertEqual(result.status_int, 200)
        self.assertEqual(result.body, b"")

    @mock_sts
    def test_get_credentials(self):
        self.providerconfig['provider']['class'] = "SingleAccountSingleRoleProvider"
        self._create_app()

        result = self.app.get('/meta-data/iam/security-credentials/the_only_role')
        self.assertEqual(result.status_int, 200)
        result_dict = dict(result.json)
        del(result_dict['Expiration'])

        last_updated = result_dict.pop('LastUpdated')
        last_updated = datetime.datetime.strptime(last_updated, "%Y-%m-%dT%H:%M:%SZ")
        time_delta = datetime.datetime.utcnow() - last_updated
        self.assertLess(time_delta, datetime.timedelta(seconds=3))

        self.assertEqual(result_dict, CREDENTIALS)

        logged_data = str(self.log_file.read())
        self.assertIn('access to account', logged_data)
        self.assertIn('the_only_account', logged_data)
        self.assertIn('the_only_role', logged_data)
        self.assertIn(self.user, logged_data)

    @mock_sts
    def test_get_credentials_must_fail_for_forbidden_role(self):
        result = self.app.get('/meta-data/iam/security-credentials/forbidden_role', expect_errors=True)
        self.assertEqual(result.status_int, 404)

    def test_get_credentials_must_fail_if_multiple_roles_from_provider(self):
        result = self.app.get('/meta-data/iam/security-credentials/testrole', expect_errors=True)
        self.assertNotEqual(result.status_int, 200)


class AFPEndpointTest(BaseEndpointTest):
    def test_status_good_case(self):
        result = self.app.get('/status')
        expected_json = {"status": "200", "message": "OK"}
        self.assertEqual(result.json, expected_json)

    def test_status_broken_providerconfig_must_be_reported(self):
        self.providerconfig = {
            'provider': {
                'module': 'a-module-that-does-not-exist',
                'class': 'a-class-that-does-not-exist',
                'regex': '(?P<account>.*)-(?P<role>.*)'
            }
        }
        self._create_app()
        result = self.app.get('/status', expect_errors=True)
        self.assertEqual(result.status_int, 404)

    def test_account_broken_providerconfig_must_be_reported(self):
        self.providerconfig = {
            'provider': {
                'module': 'a-module-that-does-not-exist',
                'class': 'a-class-that-does-not-exist',
                'regex': '(?P<account>.*)-(?P<role>.*)'
            }
        }
        self._create_app()
        result = self.app.get('/account', expect_errors=True)
        self.assertEqual(result.status_int, 404)
        self.assertIn('X-Username', result.headers)

    def test_status_broken_basicconfig_must_be_reported(self):
        self.basicconfig['logging_handler']['module'] = "a-module-that-does-not-exist"
        self._create_app()
        result = self.app.get('/status', expect_errors=True)
        self.assertEqual(result.status_int, 404)

    def test_account_broken_basicconfig_must_be_reported(self):
        self.basicconfig['logging_handler']['module'] = "a-module-that-does-not-exist"
        self._create_app()
        result = self.app.get('/account', expect_errors=True)
        self.assertEqual(result.status_int, 404)
        self.assertIn('X-Username', result.headers)

    def test_setup_logging_sets_log_level(self):
        self.basicconfig['log_level'] = 'debug'
        setup_logging(self.basicconfig, logger_name='foobar')
        logger = logging.getLogger('foobar')
        self.assertEqual(logger.getEffectiveLevel(), logging.DEBUG)

    def test_get_list_roles_and_accounts(self):
        result = self.app.get('/account')
        accounts_and_roles = {
            "testaccount": ["testrole"],
            "testaccount1": ["testrole2"]
        }
        self.assertEqual(result.status_int, 200)
        self.assertTrue(result.json == accounts_and_roles)
        self.assertEqual(self.user, result.headers['X-Username'])

    @mock_sts
    def test_get_credentials(self):
        result = self.app.get('/account/testaccount/testrole/credentials')
        self.assertEqual(result.status_int, 200)
        result_dict = dict(result.json)
        del(result_dict['Expiration'])
        del(result_dict['LastUpdated'])
        self.assertEqual(result_dict, CREDENTIALS)
        logged_data = str(self.log_file.read())
        self.assertIn('access to account', logged_data)
        self.assertIn('testaccount', logged_data)
        self.assertIn('testrole', logged_data)
        self.assertIn(self.user, logged_data)
        self.assertEqual(self.user, result.headers['X-Username'])

    @mock_sts
    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_get_console_url(self, mock_get):
        token = "abcdefg123"
        callbackurl = ""
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=200,
                                     reason="Ok")
        url_template = ("https://signin.aws.amazon.com/federation?"
                        "Action=login&"
                        "Issuer={callbackurl}&"
                        "Destination=https%3A%2F%2Fconsole.aws.amazon.com%2F&"
                        "SigninToken={token}")
        expected_url = url_template.format(callbackurl=quote_plus(callbackurl),
                                           token=token).encode()

        result = self.app.get('/account/testaccount/testrole/consoleurl')
        self.assertEqual(result.status_int, 200)
        self.assertEqual(result.body, expected_url)

        # Check if the Callback URL is set
        callbackurl = "https://www.foobar.invalid"
        expected_url = url_template.format(callbackurl=quote_plus(callbackurl),
                                           token=token).encode()
        result = self.app.get('/account/testaccount/testrole/consoleurl',
                              {'callbackurl': callbackurl})
        self.assertEqual(result.status_int, 200)
        self.assertEqual(result.body, expected_url)

    @mock_sts
    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_get_credentials_and_consoleurl(self, mock_get):
        token = "abcdefg123"
        callbackurl = ""
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=200,
                                     reason="Ok")
        url_template = (u"https://signin.aws.amazon.com/federation?"
                        u"Action=login&"
                        u"Issuer={callbackurl}&"
                        u"Destination=https%3A%2F%2Fconsole.aws.amazon.com%2F&"
                        u"SigninToken={token}")
        expected_url = url_template.format(callbackurl=callbackurl,
                                           token=token)
        expected_credentials = dict(CREDENTIALS)
        expected_credentials['ConsoleUrl'] = expected_url
        result = self.app.get('/account/testaccount/testrole')
        result_dict = dict(result.json)
        del(result_dict['Expiration'])
        del(result_dict['LastUpdated'])
        self.assertEqual(result.status_int, 200)
        self.assertEqual(result_dict, expected_credentials)
        self.assertEqual(self.user, result.headers['X-Username'])

    @mock_sts
    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_404_on_unconfigured_account(self, mock_get):
        token = "abcdefg123"
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=200,
                                     reason="Ok")

        result = self.app.get('/account/testaccount1/testrole2',
                              expect_errors=True)
        self.assertEqual(result.status_int, 404)
        result.mustcontain('Configuration')
        self.assertEqual(self.user, result.headers['X-Username'])

        result = self.app.get('/account/testaccount1/testrole2/credentials',
                              expect_errors=True)
        self.assertEqual(result.status_int, 404)
        result.mustcontain('Configuration')
        self.assertEqual(self.user, result.headers['X-Username'])

        result = self.app.get('/account/testaccount1/testrole2/consoleurl',
                              expect_errors=True)
        self.assertEqual(result.status_int, 404)
        result.mustcontain('Configuration')
        self.assertEqual(self.user, result.headers['X-Username'])

    @mock_sts
    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_403_on_illegal_role(self, mock_get):
        token = "abcdefg123"
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=200,
                                     reason="Ok")
        result = self.app.get('/account/testaccount/illegalrole',
                              expect_errors=True)
        self.assertEqual(result.status_int, 403)
        self.assertEqual(self.user, result.headers['X-Username'])

        result.mustcontain("may not access")
        result = self.app.get('/account/testaccount/illegalrole/credentials',
                              expect_errors=True)
        self.assertEqual(result.status_int, 403)
        result.mustcontain("may not access")
        self.assertEqual(self.user, result.headers['X-Username'])

        result = self.app.get('/account/testaccount/illegalrole/consoleurl',
                              expect_errors=True)
        self.assertEqual(result.status_int, 403)
        result.mustcontain("may not access")
        self.assertEqual(self.user, result.headers['X-Username'])

        logged_data = str(self.log_file.read())
        self.assertIn('may not access role', logged_data)
        self.assertIn('testaccount', logged_data)
        self.assertIn('illegalrole', logged_data)
        self.assertIn(self.user, logged_data)

    @mock_sts
    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_403_on_illegal_account(self, mock_get):
        token = "abcdefg123"
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=200,
                                     reason="Ok")
        result = self.app.get('/account/testaccount1/testrole',
                              expect_errors=True)
        self.assertEqual(result.status_int, 403)
        result.mustcontain("may not access")
        self.assertEqual(self.user, result.headers['X-Username'])

        result = self.app.get('/account/testaccount1/testrole/credentials',
                              expect_errors=True)
        self.assertEqual(result.status_int, 403)
        result.mustcontain("may not access")
        self.assertEqual(self.user, result.headers['X-Username'])

        result = self.app.get('/account/testaccount1/testrole/consoleurl',
                              expect_errors=True)
        self.assertEqual(result.status_int, 403)
        result.mustcontain("may not access")
        self.assertEqual(self.user, result.headers['X-Username'])

        logged_data = str(self.log_file.read())
        self.assertIn('may not access role', logged_data)
        self.assertIn('testaccount1', logged_data)
        self.assertIn('testrole', logged_data)
        self.assertIn(self.user, logged_data)

    @patch("aws_federation_proxy.aws_federation_proxy.AWSFederationProxy.get_aws_credentials")
    def test_502_on_aws_failure(self, mock_get_aws_credentials):
        mock_get_aws_credentials.side_effect = AWSError("aws is down")
        result = self.app.get('/account/testaccount/testrole',
                              expect_errors=True)
        self.assertEqual(result.status_int, 502)
        result.mustcontain("aws is down")
        self.assertEqual(self.user, result.headers['X-Username'])
