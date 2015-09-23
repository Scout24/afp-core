import collections
from mock import patch

from provider_by_groups_tests import ProviderByGroupsTests
from aws_federation_proxy.provider.grp_provider import Provider


class GrpProviderTests(ProviderByGroupsTests):
    def setUp(self):
        super(GrpProviderTests, self).setUp()
        self.testclass = Provider

    @patch("aws_federation_proxy.provider.grp_provider.grp.getgrall")
    def test_get_group_list_must_parse_grp_getgrall_return_value(self, mock_getgrall):
        user_name = "some_user_name"
        fake_struct_group = collections.namedtuple(
            "struct_group",
            ["gr_name", "gr_passwd", "gr_gid", "gr_mem"])
        fake_getgrall_result = fake_struct_group(
            "group_name", "group_password", 42, [user_name, "someone_else"])
        mock_getgrall.return_value = [fake_getgrall_result]

        provider = self.testclass(user_name, self.config)
        received_groups = provider.get_group_list()

        self.assertGreater(len(received_groups), 0)
        self.assertEqual(received_groups, ["group_name"])
