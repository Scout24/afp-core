import logging

from unittest2 import TestCase
from aws_federation_proxy.provider.base_provider import BaseProvider


class BaseProviderTest(TestCase):
    def setUp(self):
        self.testclass = BaseProvider
        self.config = {}
        self.mini_config = {}

    def test_base_provider_can_be_instantiated_with_basic_config(self):
        provider = self.testclass('testuser', self.mini_config)
        self.assertEqual(provider.user, 'testuser')
        self.assertTrue(isinstance(provider.logger, object))

    def test_base_provider_can_be_instantiated_with_logger(self):
        logger = logging.getLogger()

        provider = self.testclass('testuser', self.config, logger=logger)
        self.assertIs(provider.logger, logger)
