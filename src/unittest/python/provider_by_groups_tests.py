from base_provider_tests import BaseProviderTest

from mock import Mock
from aws_federation_proxy.provider.base_provider import ProviderByGroups


class ProviderByGroupsTests(BaseProviderTest):
    def setUp(self):
        super(ProviderByGroupsTests, self).setUp()
        self.testclass = ProviderByGroups
        regex = '(?P<account>.*)-(?P<role>.*)'
        self.config['regex'] = regex
        self.reason_template = (
            'user is in group "%%s" which matches regexp "^%s$"' % regex)
        self.mini_config['regex'] = self.config['regex']

    def test_prepend_caret_to_regex(self):
        provider = self.testclass('testuser', self.config)
        self.assertTrue(provider.regex.startswith('^'))

    def test_append_dollar_to_regex(self):
        provider = self.testclass('testuser', self.config)
        self.assertTrue(provider.regex.endswith('$'))

    def test_dont_prepend_caret_to_regex_if_exists(self):
        self.config['regex'] = '^(?P<account>.*)-(?P<role>.*)'
        provider = self.testclass('testuser', self.config)
        self.assertFalse(provider.regex.startswith('^^'))

    def test_dont_append_dollar_to_regex_if_exists(self):
        self.config['regex'] = '(?P<account>.*)-(?P<role>.*)$'
        provider = self.testclass('testuser', self.config)
        self.assertFalse(provider.regex.endswith('$$'))

    def test_get_accounts_and_roles_with_matching_single_group(self):
        provider = self.testclass('testuser', self.config)
        group = "account-role"
        expected_reason = self.reason_template % group
        expected_accounts = {
            'account': set([('role', expected_reason)])
        }
        mock_get_group_list = Mock()
        mock_get_group_list.return_value = (group,)
        provider.get_group_list = mock_get_group_list

        returned_accounts = provider.get_accounts_and_roles()
        self.assertEqual(returned_accounts, expected_accounts)

    def test_get_accounts_and_roles_with_nonmatching_single_group(self):
        provider = self.testclass('testuser', self.config)
        mock_get_group_list = Mock()
        mock_get_group_list.return_value = ("foobar",)
        provider.get_group_list = mock_get_group_list

        expected_accounts = {}
        returned_accounts = provider.get_accounts_and_roles()
        self.assertEqual(returned_accounts, expected_accounts)

    def test_get_accounts_and_roles_with_multiple_groups_matching_multiple_accounts(self):
        provider = self.testclass('testuser', self.config)
        expected_accounts = {
            'account1': set([('role', self.reason_template % "account1-role")]),
            'account2': set([('role', self.reason_template % "account2-role")])
        }
        mock_get_group_list = Mock()
        mock_get_group_list.return_value = ["account1-role", "account2-role"]
        provider.get_group_list = mock_get_group_list

        returned_accounts = provider.get_accounts_and_roles()
        self.assertEqual(returned_accounts, expected_accounts)

    def test_get_accounts_and_roles_with_multiple_groups_matching_multiple_roles(self):
        provider = self.testclass('testuser', self.config)
        group1 = "account-role1"
        group2 = "account-role2"
        expected_accounts = {
            'account': set([
                ('role1', self.reason_template % group1),
                ('role2', self.reason_template % group2)])
        }
        mock_get_group_list = Mock()
        mock_get_group_list.return_value = [group1, group2]
        provider.get_group_list = mock_get_group_list

        returned_accounts = provider.get_accounts_and_roles()
        self.assertEqual(returned_accounts, expected_accounts)
