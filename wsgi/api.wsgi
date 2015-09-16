#!/usr/bin/env python
# -*- coding: utf-8 -*-

import aws_federation_proxy.wsgi_api as wsgi_api
application = wsgi_api.get_webapp()
