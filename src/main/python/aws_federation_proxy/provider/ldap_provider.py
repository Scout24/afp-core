#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ldap

from aws_federation_proxy.provider import ProviderByGroups


class Provider(ProviderByGroups):
    """Uses the ldap module to retrieve group information from LDAP"""

    def get_group_list(self):
        ldap_uri = self.config['ldap_uri']
        ldap_base_users = self.config['ldap_base_users']
        ldap_base_groups = self.config['ldap_base_groups']
        ldap_bind_dn = self.config['ldap_bind_dn']
        ldap_bind_password = self.config['ldap_bind_password']

        l = ldap.initialize(ldap_uri)

        self.logger.debug('User: "%s"', self.user.lower())
        search_filter = '(|(&(objectClass=user)' \
                        '(sAMAccountName=%s)))' \
                        % self.user.lower()

        self.logger.debug('User DN Search Filter: "%s"', search_filter)
        try:
            l.simple_bind_s(ldap_bind_dn, ldap_bind_password)

            # Find user's DN
            result = l.search_s(ldap_base_users, ldap.SCOPE_SUBTREE, search_filter, ['dn', ])
            dn, _ = result[0]
            self.logger.debug('User DN: "%s"', dn)

            search_filter = '(|(&(objectClass=group)' \
                            '(member:1.2.840.113556.1.4.1941:=%s)))' \
                            % dn
            self.logger.debug('Group Search Filter: "%s"', search_filter)

            result = l.search_s(ldap_base_groups, ldap.SCOPE_SUBTREE, search_filter, ['name', ])
            results = []
            for _, entry in result:
                if type(entry) is dict:
                    results.append(entry['name'][0])

            self.logger.debug('Groups: "%s"', results)
            return results
        except ldap.LDAPError, e:
            print e.message['info']
            if type(e.message) == dict and 'desc' in e.message:
                print e.message['desc']
            else:
                print e
        return False
