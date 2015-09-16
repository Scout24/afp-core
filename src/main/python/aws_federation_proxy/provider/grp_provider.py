from aws_federation_proxy.provider import ProviderByGroups

import grp


class Provider(ProviderByGroups):
    """Uses the builtin grp module to retrieve group information"""

    def get_group_list(self):
        return [g.gr_name for g in grp.getgrall() if self.user in g.gr_mem]
