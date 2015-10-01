from __future__ import print_function, absolute_import, unicode_literals, division

import collections
from mock import patch

from provider_by_groups_tests import ProviderByGroupsTests
from aws_federation_proxy.provider.grp_provider import Provider


class GrpProviderTests(ProviderByGroupsTests):
    def setUp(self):
        super(GrpProviderTests, self).setUp()
        self.testclass = Provider

    @patch("aws_federation_proxy.provider.grp_provider.grp.getgrall")
    def check_group_list_with_set_users(self, given_user_name, system_user_name, mock_getgrall):
        fake_struct_group = collections.namedtuple(
            "struct_group",
            ["gr_name", "gr_passwd", "gr_gid", "gr_mem"])
        fake_getgrall_result = fake_struct_group(
            "group_name", "group_password", 42, [system_user_name, "someone_else"])
        mock_getgrall.return_value = [fake_getgrall_result]

        provider = self.testclass(given_user_name, self.config)
        received_groups = provider.get_group_list()

        self.assertGreater(len(received_groups), 0)
        self.assertEqual(received_groups, ["group_name"])

    def test_get_group_list_must_parse_grp_getgrall_return_value_with_uppercase_user_name(self):
        self.check_group_list_with_set_users("SOME_USER_NAME", "some_user_name")

    def test_get_group_list_must_parse_grp_getgrall_return_value_with_both_users_lowercase(self):
        self.check_group_list_with_set_users("some_user_name", "some_user_name")

    def test_get_group_list_must_parse_grp_getgrall_return_value_with_both_users_uppercase(self):
        self.check_group_list_with_set_users("SOME_USER_NAME", "SOME_USER_NAME")

    def test_get_group_list_must_parse_grp_getgrall_return_value_with_uppercase_system_user(self):
        self.check_group_list_with_set_users("some_user_name", "SOME_USER_NAME")
