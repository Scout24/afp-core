#!/bin/bash
# Setup script for Ubuntu/Debian or Red Hat/Clones
# Run this program to get an initial setup that allows you to run unit tests.

# Add required packages as space seperated list:
DEBIAN_PACKAGES="python-sss"
REDHAT_PACKAGES=""

# Add additional virtualenv options:
VIRTUALENV_OPTIONS="--system-site-packages"

if type apt-get &>/dev/null ; then
    dpkg -s $DEBIAN_PACKAGES python-virtualenv &>/dev/null || \
        sudo apt-get install $DEBIAN_PACKAGES python-virtualenv
else
    rpm -q $REDHAT_PACKAGES python-virtualenv &>/dev/null || \
        sudo yum install $REDHAT_PACKAGES python-virtualenv
fi

virtualenv $VIRTUALENV_OPTIONS venv

# Enter the virtual environment before "pip install ...", so that things get
# installed in venv, not in the main system.
source venv/bin/activate
pip install --pre yamlreader
pip install pybuilder
pyb install_dependencies
