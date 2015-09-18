#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pwd
import unittest2
from aws_federation_proxy.provider.grp_provider import Provider


class GrpProviderIntegrationTest(unittest2.TestCase):
    def test_get_group_list(self):
        my_user_name = pwd.getpwuid(os.getuid()).pw_name
        config = {
            "regex": "(?P<account>.*)(?P<role>.*)"
        }

        provider = Provider(my_user_name, config)
        received_groups = provider.get_group_list()

        # Assume that the user running this test has more than just a
        # primary groups, otherwise the test fails.
        self.assertGreater(len(received_groups), 0)


if __name__ == "__main__":
    unittest2.main()
