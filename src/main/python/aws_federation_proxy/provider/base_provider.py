#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

import re
import logging


class BaseProvider(object):
    """
    Uses the supplied mapping config to construct a dict of accessible aws
    account aliases and the associated aws roles for the given user
    """

    def __init__(self, user, config, logger=None):
        self.user = user
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    def get_accounts_and_roles(self):
        """Return a dict like {account1: set([(role1, reason), ...]), ...} for self.user

        The "reason" in the (role, reason) tuple explains in human-readable
        form why the user is allowed to assume this role, mainly for logging.
        """
        raise NotImplementedError


class ProviderByGroups(BaseProvider):
    """Uses a user's groups and a regex to determine the accounts/roles

    This class assumes that config['regex'] is a regular expression that will
    produce two matching-groups called 'account' and 'role' when applied to
    certain group names. For example, if your group names look like
            aws-myaccount-administrator
    a regular expression like
            aws-(?P<account>.*)-(?P<role>.*)
    will produce a matching-group "account" which matched "myaccount" and a
    matching group "role" which matched "administrator".

    Actually retrieving group information must be implemented by subclasses.
    """
    def __init__(self, user, config, logger=None, **kwargs):
        super(ProviderByGroups, self).__init__(
            user,
            config,
            logger=logger,
            **kwargs)
        regex = config['regex']
        if not regex.startswith('^'):
            regex = '^' + regex
        if not regex.endswith('$'):
            regex = regex + '$'
        self.regex = regex

    def get_group_list(self):
        """Return the groups for self.user"""
        raise NotImplementedError

    def get_accounts_and_roles(self):
        """
        Return a dict of sets of all related
        groups which are assigned to the user
        """
        groups = self.get_group_list()
        accounts_and_roles = {}
        for group in groups:
            match = re.search(self.regex, group)
            if match:
                account = match.group('account')
                role = match.group('role')
                reason = 'user is in group "%s" which matches regexp "%s"' % (
                    group, self.regex)
                self.logger.debug(
                    'User "%s" may access account "%s", role "%s" because %s.',
                    self.user, role, account, reason)
                if account in accounts_and_roles:
                    accounts_and_roles[account].add((role, reason))
                else:
                    accounts_and_roles[account] = set([(role, reason)])
            else:
                self.logger.debug('Group "%s" did not match regex "%s"',
                                  group, self.regex)
        return accounts_and_roles


class SimpleTestProvider(BaseProvider):
    """A sample Provider, for testing only"""
    def get_accounts_and_roles(self):
        reason = "Because I said so."
        return {
            'testaccount': set([('testrole', reason)]),
            'testaccount1': set([('testrole2', reason)])}


class SingleAccountSingleRoleProvider(BaseProvider):
    """A sample Provider, for testing only"""
    def get_accounts_and_roles(self):
        return {'the_only_account': set([('the_only_role', 'because I said so')])}


class NoAccountNoRoleProvider(BaseProvider):
    """A sample Provider, for testing only"""
    def get_accounts_and_roles(self):
        return {}


class GroupTestProvider(ProviderByGroups):
    """A sample Provider, for testing only

    When configured with
            'regex': '(?P<account>.*)-(?P<role>.*)'
    it produces the same accounts and roles as the SimpleTestProvider.
    """
    def get_group_list(self):
        return ["testaccount-testrole", "testaccount1-testrole2", "foobar"]
