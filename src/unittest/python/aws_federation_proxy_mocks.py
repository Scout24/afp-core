""" Mock classes for use in aws_federation_proxy_tests """

from aws_federation_proxy.aws_federation_proxy import AWSFederationProxy


class MockAWSFederationProxyForInitTest(AWSFederationProxy):
    def _setup_provider(self):
        pass
