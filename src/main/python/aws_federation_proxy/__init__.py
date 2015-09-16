#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Only imports/exports"""

from aws_federation_proxy import (
    AWSFederationProxy,
    ConfigurationError,
    AWSError,
    PermissionError
)
__all__ = ['AWSFederationProxy',
           'ConfigurationError',
           'AWSError',
           'PermissionError']
