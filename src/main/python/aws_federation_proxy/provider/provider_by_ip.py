#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

from socket import gethostbyaddr

from aws_federation_proxy import PermissionError
from aws_federation_proxy.provider import BaseProvider


class ProviderByIP(BaseProvider):
    """Uses IP address/FQDN as username, returning exactly one role

    The account name must be configured, only the role name is determined by
    the IP/FQDN.
    """

    def get_accounts_and_roles(self):
        """Return a dict with one account and one aws role"""
        self.role_prefix = self.config.get('role_prefix', "")
        try:
            self.client_fqdn = gethostbyaddr(self.user)[0]
        except Exception as exc:
            # The exception message of gethostbyaddr() is quite useless since
            # it does not include the address that was looked up.
            message = "Lookup for '{0}' failed: {1}".format(self.user, exc)
            raise Exception(message)
        self.check_host_allowed()
        self._get_role_name()
        reason = "Machine {0} (FQDN {1}) matched the role {2}".format(
            self.user, self.client_fqdn, self.role_name)
        return {self.config["account_name"]: set([(self.role_name, reason)])}

    def check_host_allowed(self):
        self.client_host, self.client_domain = self.client_fqdn.split(".", 1)
        allowed_domains = self.config['allowed_domains']
        if self.client_domain not in allowed_domains:
            raise PermissionError("Client IP {0} (FQDN {1}) is not permitted".format(
                self.user, self.client_fqdn))

    def _get_role_name(self):
        """Translate self.user / self.client_fqdn into self.role_name"""
        raise NotImplementedError  # pragma: no cover


class Provider(ProviderByIP):
    """Apply Immobilienscout24 host name pattern, returning exactly one role"""

    def _get_role_name(self):
        """Determined the aws role name to a given ip address"""
        loctyp = self._normalize_loctyp()
        self.role_name = self.role_prefix + loctyp

    def check_host_allowed(self):
        super(Provider, self).check_host_allowed()
        if len(self.client_host) != 8:
            raise PermissionError(
                "Client {0} has an invalid name".format(self.client_fqdn))

    def _normalize_loctyp(self):
        """Return the normalized (ber/ham -> pro) loctyp of self.client_host"""
        if self.client_host.startswith(("ber", "ham")):
            return "pro" + self.client_host[3:6]
        else:
            return self.client_host[:6]
