from pybuilder.core import use_plugin, init

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
use_plugin("python.pylint")
use_plugin("python.coverage")
use_plugin("python.distutils")
use_plugin("copy_resources")
use_plugin("filter_resources")

name = 'afp-core'
summary = 'API and backend for temporary authentication to aws services'
description = """API and backend for temporary authentication to aws services.
Based on different providers the included backend uses the assumeRole call
to retrieve temporary credentials. This could be used for human and/or
machine authentication to services from aws.
"""
license = 'GNU GPL v3'

default_task = ["clean", "analyze", "publish"]


@init
def set_properties(project):
    project.build_depends_on("mock")
    project.build_depends_on("moto")
    project.build_depends_on("PyYAML")
    project.build_depends_on("unittest2")
    project.build_depends_on("webtest")

    project.depends_on("requests")
    project.depends_on("simplejson")
    project.depends_on("six")
    project.depends_on("yamlreader")
    project.depends_on("bottle")
    project.depends_on("boto>=2.38.0")

    project.set_property("verbose", True)
    project.set_property('flake8_include_test_sources', True)
    project.set_property('flake8_break_build', True)

    project.set_property('copy_resources_target', '$dir_dist')
    project.install_file('/var/www/afp-core/', 'wsgi/api.wsgi')
    project.get_property('copy_resources_glob').extend(['wsgi/*'])


@init(environments='teamcity')
def set_properties_for_teamcity_builds(project):
    import os
    project.set_property('teamcity_output', True)
    project.version = '%s-%s' % (project.version,
                                 os.environ.get('BUILD_NUMBER', 0))
    project.default_task = ['clean', 'install_build_dependencies', 'publish']
    project.set_property('install_dependencies_index_url',
                         os.environ.get('PYPIPROXY_URL'))
    project.rpm_release = os.environ.get('RPM_RELEASE', 0)
    project.set_property('copy_resources_target', '$dir_dist')
    project.get_property('copy_resources_glob').extend(['setup.cfg'])
    project.get_property('filter_resources_glob').extend(['**/setup.cfg'])
