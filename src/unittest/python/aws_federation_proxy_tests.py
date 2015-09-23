from __future__ import print_function, absolute_import, division

import logging
import json
from unittest2 import TestCase
from moto import mock_sts
from mock import patch, Mock
from six.moves.urllib.parse import quote_plus, unquote_plus
from aws_federation_proxy import AWSFederationProxy
from aws_federation_proxy.aws_federation_proxy import log_function_call
from aws_federation_proxy_mocks import MockAWSFederationProxyForInitTest


class CredentialDict(dict):
    def to_dict(self):
        return self


class LogFunctionCallTest(TestCase):
    def setUp(self):
        self.testobject = Mock()
        self.testobject.logger = Mock()
        self.testobject.logger.debug = Mock()
        foobar = Mock()
        foobar.__name__ = "foobar"
        self.testobject.foobar = log_function_call(foobar)
        self.testobject.original_foobar = foobar

    def test_must_pass_parameters(self):
        self.testobject.foobar(self.testobject, 42, foo=23)
        self.testobject.original_foobar.assert_called_with(
            self.testobject,
            42,
            foo=23)

    def test_must_pass_exception(self):
        class MyOwnException(Exception):
            pass
        self.testobject.original_foobar.side_effect = MyOwnException
        self.assertRaises(
            MyOwnException,
            self.testobject.foobar,
            self.testobject)

    def test_must_pass_return_values(self):
        self.testobject.original_foobar.return_value = 42
        self.assertEqual(
            self.testobject.foobar(self.testobject),
            self.testobject.original_foobar.return_value)

    def test_must_log(self):
        self.testobject.foobar(self.testobject)
        self.assertGreaterEqual(self.testobject.logger.debug.call_count, 1)

    def test_must_log_on_Exception(self):
        self.testobject.original_foobar.side_effect = Exception
        self.assertRaises(Exception, self.testobject.foobar, self.testobject)
        self.assertGreaterEqual(self.testobject.logger.debug.call_count, 1)


class TestAWSFederationProxyInit(TestCase):
    def test_applies_defaults(self):
        user = "testuser"
        proxy = MockAWSFederationProxyForInitTest(
            user,
            config={},
            account_config={})
        self.assertEqual(None, proxy.application_config['aws']['access_key'])
        self.assertEqual(None, proxy.application_config['aws']['secret_key'])
        self.assertEqual(
            "Provider",
            proxy.application_config['provider']['class'])
        self.assertTrue(isinstance(proxy.logger, object))

    def test_merges_config(self):
        config = {
            'aws': {
                'access_key': "foobar"
            },
            'provider': {
                'module': 'aws_federation_proxy.provider.sssd_provider',
            }
        }
        expected_config = {
            'aws': {
                'access_key': "foobar",
                'secret_key': None
            },
            'provider': {
                'module': 'aws_federation_proxy.provider.sssd_provider',
                'class': 'Provider'
            }
        }
        user = "testuser"
        proxy = MockAWSFederationProxyForInitTest(
            user,
            config=config,
            account_config={})
        self.assertEqual(proxy.application_config, expected_config)


class TestSetupProvider(TestCase):
    def test_report_name_if_module_cannot_imported(self):
        provider = "some-module-that-does-not-exist"
        config = {
            'provider': {
                'module': provider
            }
        }

        self.assertRaisesRegexp(
            Exception, provider, AWSFederationProxy,
            user="testuser", config=config, account_config={})

    def test_report_name_if_class_cannot_imported(self):
        provider_class = 'not-existing-class'
        config = {
            'provider': {
                'module': 'aws_federation_proxy.provider.base_provider',
                'class': provider_class
            }
        }
        self.assertRaisesRegexp(
            Exception, provider_class, AWSFederationProxy,
            user="testuser", config=config, account_config={})

    def test_report_module_not_configured(self):
        expected_regex = "(No.*defined.*provider)|(provider.*not defined)"
        self.assertRaisesRegexp(Exception, expected_regex, AWSFederationProxy,
                                user="testuser", config={}, account_config={})

    def test_instantiate_provider_with_proper_parameters(self):
        user = "testuser"
        config = {
            'provider': {
                'module': 'aws_federation_proxy.provider.base_provider',
                'class': 'GroupTestProvider',
                'regex': '(?P<account>.*)-(?P<role>.*)'
            }
        }
        proxy = AWSFederationProxy(user=user, config=config, account_config={})
        provider = proxy.provider
        self.assertEqual(user, provider.user)
        self.assertEqual(proxy.application_config['provider'], provider.config)
        self.assertIs(proxy.logger, provider.logger)

    def test_throws_exception_with_proper_message_on_wrong_provider(self):
        user = "testuser"
        class_name = 'loads'
        config = {
            'provider': {
                'module': 'json',
                'class': class_name
            }
        }
        self.assertRaisesRegexp(
            Exception, "instantiate.*" + class_name,
            AWSFederationProxy, user=user, config=config, account_config={}
        )


class TestHandler(logging.Handler):
    """A handler that stores all messages in memory only"""
    def __init__(self):
        logging.Handler.__init__(self)
        self.logged_messages = ""

    def emit(self, record):
        self.logged_messages += self.format(record) + "\n"


class BaseAFPTest(object):
    def setUp(self):
        self.testuser = 'mmustermann'
        self.account_alias = 'aws-account-alias'
        self.role = 'role'

        self.account_config = {
            'aws-account-alias': {
                'id': '123456789'
            }
        }
        proxy_logger = logging.getLogger('proxy_logger')
        self.handler = TestHandler()
        proxy_logger.addHandler(self.handler)
        proxy_logger.setLevel(logging.INFO)
        self.proxy = AWSFederationProxy(
            user=self.testuser,
            config=self.config,
            account_config=self.account_config,
            logger=proxy_logger)

        self.test_access_key = "unencoded string;"
        self.test_secret_key = "another weird string"
        self.test_session_token = "string with special characters %&;?"
        self.credentials = CredentialDict({
            'access_key': self.test_access_key,
            'secret_key': self.test_secret_key,
            'session_token': self.test_session_token
        })

    def test_check_user_permissions_ok(self):
        self.proxy.check_user_permissions('testaccount', 'testrole')
        self.assertIn(self.testuser, self.handler.logged_messages)
        self.assertIn('testrole', self.handler.logged_messages)
        self.assertIn('testaccount', self.handler.logged_messages)

        self.proxy.check_user_permissions('testaccount1', 'testrole2')
        self.assertIn('testrole2', self.handler.logged_messages)
        self.assertIn('testaccount', self.handler.logged_messages)

    def test_check_user_permissions_wrong_account(self):
        self.assertRaisesRegexp(
            Exception, 'noaccount',
            self.proxy.check_user_permissions, 'noaccount', 'testrole')
        self.assertIn('noaccount', self.handler.logged_messages)
        self.assertIn('testrole', self.handler.logged_messages)
        self.assertIn(self.testuser, self.handler.logged_messages)

        self.handler.logged_messages = ""

        self.assertRaisesRegexp(
            Exception, '(noaccount|norole)',
            self.proxy.check_user_permissions, 'noaccount', 'norole')
        self.assertIn('noaccount', self.handler.logged_messages)
        self.assertIn('norole', self.handler.logged_messages)
        self.assertIn(self.testuser, self.handler.logged_messages)

    def test_check_user_permissions_wrong_role(self):
        self.assertRaisesRegexp(
            Exception, 'norole',
            self.proxy.check_user_permissions, 'testaccount', 'norole')
        self.assertRaisesRegexp(
            Exception, '(noaccount|norole)',
            self.proxy.check_user_permissions, 'noaccount', 'norole')

    @patch("aws_federation_proxy.aws_federation_proxy.STSConnection")
    @patch("aws_federation_proxy.AWSFederationProxy.check_user_permissions")
    def test_get_aws_credentials_uses_correct_arn(
            self, mock_check_user_permissions, mock_sts_connection):
        arn = "arn:aws:iam::{account_id}:role/{role}"
        arn = arn.format(
            account_id=self.account_config[self.account_alias]['id'],
            role=self.role)

        self.proxy.get_aws_credentials(self.account_alias, self.role)
        mock_sts_connection.return_value.assume_role.assert_called_with(
            role_arn=arn,
            role_session_name=self.testuser)

    @mock_sts
    @patch("aws_federation_proxy.AWSFederationProxy.check_user_permissions")
    def test_get_aws_credentials(self, mock_check_user_permissions):
        session_token = (
            'BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+FvwqnKwRcOIfr'
            'Rh3c/LTo6UDdyJwOOvEVPvLXCrrrUtdnniCEXAMPLE/IvU1dYUg2RVAJBan'
            'LiHb4IgRmpRV3zrkuWJOgQs8IZZaIv2BXIa2R4OlgkBN9bkUDNCJiBeb/'
            'AXlzBBko7b15fjrBs2+cTQtpZ3CYWFXG8C5zqx37wnOE49mRl/+OtkIKGO7fAE')
        expected_result = {
            'access_key': u'AKIAIOSFODNN7EXAMPLE',
            'secret_key': u'aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY',
            'session_token': session_token
        }

        result = self.proxy.get_aws_credentials('aws-account-alias', 'role')
        self.assertEqual(
            result.access_key,
            expected_result['access_key'],
            'Should be the same AWS access_key')
        self.assertEqual(
            result.secret_key,
            expected_result['secret_key'],
            'Should be the same AWS secret_key')
        self.assertEqual(
            result.session_token,
            expected_result['session_token'],
            'Should be the same AWS session_token')

        # Check that exception is raised if account is not configured
        self.assertRaisesRegexp(Exception, 'account-alias-not-configured',
                                self.proxy.get_aws_credentials,
                                'account-alias-not-configured', 'role')

        # Check that exception is raised if user has no permissions
        mock_check_user_permissions.side_effect = Exception
        self.assertRaises(
            Exception,
            self.proxy.get_aws_credentials,
            'aws-account-alias',
            'role')

    def test_encode_json_credentials_returned(self):
        expected_credential_dict = {
            'sessionId': self.test_access_key,
            'sessionKey': self.test_secret_key,
            'sessionToken': self.test_session_token
        }
        returned_credentialstring = self.proxy._generate_urlencoded_json_credentials(self.credentials)
        decoded_credentialstring = unquote_plus(
            returned_credentialstring)
        self.assertNotEqual(
            decoded_credentialstring,
            returned_credentialstring)
        credential_dict = json.loads(decoded_credentialstring)
        self.assertEqual(credential_dict, expected_credential_dict)

    def test_encode_json_credentials_throws_exception_on_missing_parameter(self):
        credential_dict = CredentialDict({
            'access_key': self.test_access_key,
            'secret_key': self.test_secret_key,
        })
        self.assertRaisesRegexp(
            Exception, 'session_token',
            self.proxy._generate_urlencoded_json_credentials, credential_dict
        )

    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_get_signin_token(self, mock_get):
        token = "abcdefg123"
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=200,
                                     reason="Ok")
        returned_token = self.proxy._get_signin_token(self.credentials)
        self.assertEqual(token, returned_token)

    @patch("aws_federation_proxy.aws_federation_proxy.requests.get")
    def test_get_signin_token_throws_exception_on_error(self, mock_get):
        token = "abcdefg123"
        reason = "Bad request"
        mock_get.return_value = Mock(text=u'{"SigninToken": "%s"}' % token,
                                     status_code=400,
                                     reason=reason)
        self.assertRaisesRegexp(Exception, reason,
                                self.proxy._get_signin_token, self.credentials)

    def test_construct_console_url(self):
        token = "abcdefg123"
        callback_url = 'http://callback_url'
        encoded_callback_url = quote_plus(callback_url)
        expected_return = (
            'https://signin.aws.amazon.com/federation?'
            'Action=login&Issuer={callback_url}&'
            'Destination=https%3A%2F%2Fconsole.aws.amazon.com%2F&'
            'SigninToken={token}')
        expected_return = expected_return.format(
            token=token,
            callback_url=encoded_callback_url)

        result_url = self.proxy._construct_console_url(token, callback_url)
        self.assertEqual(
            result_url,
            expected_return,
            "Should return correct signin URL, got {0}".format(result_url))

    def test_get_console_url(self):
        token = "abcdefg123"
        callback_url = 'http://callback_url'
        encoded_callback_url = quote_plus(callback_url)
        self.proxy._get_signin_token = Mock(return_value=token)

        console_url = self.proxy.get_console_url(
            self.credentials,
            callback_url)

        expected_console_url = (
            'https://signin.aws.amazon.com/federation?'
            'Action=login&Issuer={callback_url}&'
            'Destination=https%3A%2F%2Fconsole.aws.amazon.com%2F&'
            'SigninToken={token}')
        expected_console_url = expected_console_url.format(
            token=token, callback_url=encoded_callback_url)
        self.assertEqual(console_url, expected_console_url)


class AFPGroupTest(BaseAFPTest, TestCase):
    config = {
        'provider': {
            'module': 'aws_federation_proxy.provider.base_provider',
            'class': 'GroupTestProvider',
            'regex': '(?P<account>.*)-(?P<role>.*)'
        }
    }


class AFPSimpleTest(BaseAFPTest, TestCase):
    config = {
        'provider': {
            'module': 'aws_federation_proxy.provider.base_provider',
            'class': 'SimpleTestProvider',
        }
    }
