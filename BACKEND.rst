============================
AWS Federation Proxy Backend
============================

Configuration
=============

The ``AWSFederationProxy`` needs two configurations:

Application Configuration
-------------------------

* ``aws``: (optional, if not set boto is used)

  - ``access_key``: The access key you get from AWS
  - ``secret_key``: The secret key you get from AWS

* ``provider``:

    - ``SimpleTestProvider``:

        + This provider does not need a provider configuration

    - ``ProviderByGroups``:

        + ``module``: Defines the provider module how you would import
          it in scripts (e.g.: ``aws_federation_proxy.provider.grp_provider``)
        + ``class``: Class to be used inside the provider module
          (optional, default `Provider` is used)
        + ``regex``: Only needed for ``ProviderByGroups`` (``grp_provider`` for example).
          In this Regex named groups are used to seperate *account* and *role* names.
          e.g.: ``foo-(?P<account>.*)-(?P<role>.*)``
          (**The whole groupname is matched by this regex!**)

    - ``ProviderByIP``:

        + ``module``: Defines the provider module how you would import it in scripts
          (e.g.: ``aws_federation_proxy.provider.provider_by_ip``)
        + ``allowed_domains``: Only hosts from this domains are permitted
        + ``account_name``: AWS Account with AWS Roles
        + ``role_prefix``: Prefix to prepend to the role


Accounts Configuration
----------------------

Here you need to map account aliases to account ids. Example:
.. code-block:: yaml

      account-name:
        id: 3141592654

AWS Configuration
-----------------

General
~~~~~~~

Because everything is based on the assume role process you need a user
in your central aws account, which has the following permissions:

.. code-block:: json

      "Action": [
        "iam:ListRoles",
        "Iam:GetRole"
      ],
      "Resource": [
        "*"
      ]
      "Effect": "Allow",
      "Action": [
        "sts:AssumeRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/*"
      ]

Resources
~~~~~~~~~

At first you have to define roles, which have the permission set you need.
A role can be located on another aws account or on your main account,
depending what you want to achieve. Here are two examples:

# The **ProviderByGroups** is a good choice, if you want to authorize
  humans. Create role(s) in another aws account, set your needed
  permissions and define the **Trusted Entities**, which have to point to
  your federation user:

  ::

      arn:aws:iam::123456789:user/federation-user

# The **ProviderByIP** is good for machine authentication. In this
  scenario you have to define your wished roles inside your main
  account. This roles should have no permissions at all. Why?
  Resources in other accounts can then be configured to grant
  access to this role then. But don't forget to define the
  **Trusted Entities** for this roles as described in point 1.

Usage
=====

AWSFederationProxy module
-------------------------

Initialize
~~~~~~~~~~

.. code-block:: python

      from aws_federation_proxy import AWSFederationProxy

      user = 'Testuser'
      application_configuration = {
          'module': 'aws_federation_proxy.provider.sssd_provider',
          'regex': '(?P<account>.*)-(?P<role>.*)'
      }
      account_configuration = {
          'ap-test1': {
              'id': 123456789
          },
          'ap-test2': {
              'id': 3141592654
          }
      }
      aws_proxy = AWSFederationProxy(user=user,
                                     config=application_configuration,
                                     account_config=account_configuration)

Get Groups
~~~~~~~~~~

.. code-block:: python

      aws_proxy.get_account_and_role_dict()

Get Credentials
~~~~~~~~~~~~~~~

.. code-block:: python

      account_alias = 'ap-test1'
      role = 'rp-role1'
      credentials = aws_proxy.get_aws_credentials(account_alias, role)

Get Signin URL
~~~~~~~~~~~~~~

.. code-block:: python

      # AWS will redirect to the callback URL if the credentials are timed out
      callback_url = "http://example.invalid"
      aws_proxy.get_console_url(credentials, callback_url)
