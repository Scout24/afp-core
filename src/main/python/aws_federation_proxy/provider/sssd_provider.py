#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aws_federation_proxy.provider import ProviderByGroups

import pysss


class Provider(ProviderByGroups):
    """Uses the pysss module to retrieve group information from SSSD"""

    def get_group_list(self):
        return pysss.getgrouplist(self.user)
