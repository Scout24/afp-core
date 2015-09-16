API [API]
=========
Configuration
-------------
Requires two environment variables set:

* ``CONFIG_PATH``: Path of the directory with the configuration of the API and
the AWS Federation Proxy. Additionally to the AFP configuration the API itself
needs the following setting:

  .. code-block:: yaml

    'api': {
      'user_identification': {
        'environment_field': 'REMOTE_USER'
      }
    },
    'logging_handlers': [
        {
            'module': 'logging',
            'class': 'SysLogHander',
            'args': [],
            'kwargs': {}
        }
    ]

The environment_field specifies which field from the WSGI environment identifies
the user, i.e. it is considered to be the user name.

For logging, a single logger object is used. But the logging_handlers setting
allows you to add handlers to that logger, so you can send log messages to
destinations of your choice.

* ``ACCOUNT_CONFIG_PATH``: Path of the directory with the configuration of all
Accounts.

**For details in configuration, please see the AFP Section.**

You use the example to set the Environment in the context of an apache web
server:

.. code-block::
    <Location /path/to/afp_human>
        SetEnv CONFIG_PATH "/path/to/config_human"
        SetEnv ACCOUNT_CONFIG_PATH "/path/to/account_configuration"
        AuthType Basic
        AuthName "auth_name"
        Require group group_name
        AuthPAM_Enabled On/Off
    </Location>

    <Location /path/to/afp_machine>
        SetEnv CONFIG_PATH "/path/to/config_machine"
        SetEnv ACCOUNT_CONFIG_PATH "/path/to/account_configuration"
    </Location>

    WSGIScriptAlias /path/to/afp_human "/var/www/aws-federation-proxy/api.wsgi"
    WSGIScriptAlias /path/to/afp_machine "/var/www/aws-federation-proxy/api.wsgi"

``/account``
------------
Return a set of all accounts and roles for the current user

**Returns:**

.. code-block:: json

  {
    "accountname1": ["rolename1", "rolename2", ...],
    ...
  }


``/account/<account>/<role>[?callbackurl=<CallbackURL>]``
-----------------------------
Return a dict of credentials (access_key, secret_key and session token) and
console URL for the specified role in the specified account

If callbackurl the User of the console will be redirected to this URL after the
credentials expire.

**Returns:**

.. code-block:: json

  {
    "credentials": {
      "access_key": "AKIAIOSFODNN7EXAMPLE",
      "secret_key": "aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY",
      "session_token": "BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+..."
    },
    "console_url": "https://signin.aws.amazon.com/federation?Action=login&..."
  }

``/account/<account>/<role>/credentials``
-----------------------------------------
Return a dict of credentials (access_key, secret_key and session token)

**Returns:**

.. code-block:: json

  {
    "credentials": {
      "access_key": "AKIAIOSFODNN7EXAMPLE",
      "secret_key": "aJalrXUtnFEMI/K7MDENG/bPxRfiCYzEXAMPLEKEY",
      "session_token": "BQoEXAMPLEH4aoAH0gNCAPyJxz4BlCFFxWNE1OPTgk5TthT+..."
    }
  }


``/account/<account>/<role>/consoleurl[?callbackurl=<CallbackURL>]``
----------------------------------------
Return string of the console URL for the specified role in the specified
account.

If callbackurl the User of the console will be redirected to this URL after the
credentials expire.

**Returns:**

.. code-block::

  https://signin.aws.amazon.com/federation?Action=login&...


``/status``
-----------
Return a dict of monitoring information (status, message)

**Returns:**

.. code-block:: json

  {
    "status": "200",
    "message": "OK"
  }
