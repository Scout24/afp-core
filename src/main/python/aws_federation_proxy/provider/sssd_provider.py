#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pysss

from aws_federation_proxy.provider import ProviderByGroups


class Provider(ProviderByGroups):
    """Uses the pysss module to retrieve group information from SSSD"""

    def get_group_list(self):
        return pysss.getgrouplist(self.user)
