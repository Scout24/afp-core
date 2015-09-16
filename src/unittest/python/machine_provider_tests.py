#!/usr/bin/env python
# -*- coding: utf-8 -*-

from mock import patch
from base_provider_tests import BaseProviderTest
from aws_federation_proxy.provider.provider_by_ip import Provider

ACCOUNT_NAME = "testaccount"


class MachineProviderTests(BaseProviderTest):
    def setUp(self):
        super(MachineProviderTests, self).setUp()
        self.config['account_name'] = ACCOUNT_NAME
        self.testclass = Provider

    def test_normalize_loctyp_return_given_loctyp_because_loctyp_is_not_ham_ber_dev_or_tuv(self):
        provider = self.testclass("awsxyz", self.config)
        provider.client_host = "awsxyz"
        self.assertEqual("awsxyz", provider._normalize_loctyp())

    def test_normalize_loctyp_should_match_ber_to_pro_if_ber_is_given(self):
        provider = self.testclass("berxxx", self.config)
        provider.client_host = "berxxx"
        self.assertEqual("proxxx", provider._normalize_loctyp())

    def test_normalize_loctyp_should_match_ham_to_pro_if_ham_is_given(self):
        provider = self.testclass("hamber", self.config)
        provider.client_host = "hamber"
        self.assertEqual("prober", provider._normalize_loctyp())

    def test_normalize_loctyp_should_match_dev_to_dev_if_dev_is_given(self):
        provider = self.testclass("devzzz", self.config)
        provider.client_host = "devzzz"
        self.assertEqual("devzzz", provider._normalize_loctyp())

    def test_normalize_loctyp_should_match_tuv_to_tuv_if_tuv_is_given(self):
        provider = self.testclass("tuvooo", self.config)
        provider.client_host = "tuvooo"
        self.assertEqual("tuvooo", provider._normalize_loctyp())

    @patch("aws_federation_proxy.provider.provider_by_ip.gethostbyaddr")
    def test_allowed_domains_work(self, mock_gethostbyaddr):
        mock_gethostbyaddr.return_value = ["tuvfoo42.valid"]
        self.config['allowed_domains'] = ["something.else", "valid"]
        provider = self.testclass("tuvfoo42.valid", self.config)
        return_value = provider.get_accounts_and_roles()
        self.assertIn(ACCOUNT_NAME, return_value)
        self.assertEqual(len(return_value), 1)

        roles = return_value[ACCOUNT_NAME]
        self.assertEqual(len(roles), 1)

        role, reason = roles.pop()
        self.assertEqual(role, "tuvfoo")
        self.assertGreater(len(reason), 0)

    @patch("aws_federation_proxy.provider.provider_by_ip.gethostbyaddr")
    def test_forbidden_domains_raise_exception(self, mock_gethostbyaddr):
        mock_gethostbyaddr.return_value = ["tuvfoo42.invalid"]
        self.config['allowed_domains'] = ["valid"]
        provider = self.testclass("tuvfoo42.invalid", self.config)
        self.assertRaises(Exception, provider.get_accounts_and_roles)

    @patch("aws_federation_proxy.provider.provider_by_ip.gethostbyaddr")
    def test_invalid_names_raise_exception(self, mock_gethostbyaddr):
        # host name is one character too short
        mock_gethostbyaddr.return_value = ["tuvfoo4.valid"]
        self.config['allowed_domains'] = ["something.else", "valid"]
        provider = self.testclass("tuvfoo42.valid", self.config)
        self.assertRaises(Exception, provider.get_accounts_and_roles)
