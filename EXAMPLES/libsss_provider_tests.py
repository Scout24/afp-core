#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pwd
import grp
import unittest2
from aws_federation_proxy.provider.sssd_provider import Provider


class LibsssProviderIntegrationTest(unittest2.TestCase):
    def test_get_group_list(self):
        user = pwd.getpwall()[0].pw_name
        primary_group = grp.getgrgid(pwd.getpwall()[0].pw_gid).gr_name
        config = {
            "regex": "(?P<account>.*)-(?P<role>.*)"
        }

        provider = Provider(user, config)
        received_groups = provider.get_group_list()
        self.assertIn(primary_group, received_groups)


if __name__ == "__main__":
    unittest2.main()
