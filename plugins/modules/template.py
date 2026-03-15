#!/usr/bin/python
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Andreas Wolf
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: template
short_description: Manage Zabbix templates via the HTTP JSON-RPC API
version_added: "1.0.0"
description:
  - Imports or removes Zabbix templates using the Zabbix HTTP JSON-RPC API.
  - All HTTP requests are made from the host on which the task runs. For
    controller-side execution, use C(delegate_to: localhost) or run the task
    in a play that targets C(localhost).
  - When O(state=present), the module always reports C(changed) because the
    Zabbix C(configuration.import) API provides no delta information.
  - When O(state=absent), the module is idempotent; it is a no-op if the
    template does not exist.
options:
  state:
    description:
      - Whether the template should be V(present) (imported) or V(absent)
        (removed).
    type: str
    choices: [present, absent]
    default: present
  src:
    description:
      - Path to a YAML file containing the template in Zabbix export format.
      - Mutually exclusive with O(template).
      - Required when O(state=present) and O(template) is not set.
    type: path
  template:
    description:
      - Inline template content as a dict in Zabbix export format (the
        structure produced by Zabbix's Export feature).
      - Mutually exclusive with O(src).
      - Required when O(state=present) and O(src) is not set.
    type: dict
  name:
    description:
      - Name of the template in Zabbix (the C(host) identifier used by the
        API).
      - Required when O(state=absent).
    type: str
  api_url:
    description:
      - Full URL to the Zabbix JSON-RPC API endpoint.
      - "Example: C(https://zabbix.example.com/zabbix/api_jsonrpc.php)"
    type: str
    required: true
  api_token:
    description:
      - Bearer token for API authentication (preferred; requires Zabbix
        >= 6.4).
      - When set, O(api_user) and O(api_password) are ignored.
    type: str
    no_log: true
    default: ""
  api_user:
    description:
      - Zabbix username for session-based authentication.
      - Used as a fallback when O(api_token) is not set.
    type: str
    default: ""
  api_password:
    description:
      - Zabbix password for session-based authentication.
      - Used together with O(api_user).
    type: str
    no_log: true
    default: ""
  validate_certs:
    description:
      - Whether to validate TLS certificates when making API requests.
      - Set to V(false) only in development or test environments with
        self-signed certificates.
    type: bool
    default: true
author:
  - Andreas Wolf (@andreaswolf)
'''

EXAMPLES = r'''
- name: Import a Zabbix template from a YAML file on the controller
  a9f.zabbix.template:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_token: "{{ zabbix_api_token }}"
    src: "{{ playbook_dir }}/files/my_template.yml"
    state: present
  delegate_to: localhost

- name: Import a Zabbix template defined inline
  a9f.zabbix.template:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_token: "{{ zabbix_api_token }}"
    template:
      zabbix_export:
        version: "7.4"
        templates:
          - template: "My Template"
            name: "My Template"
    state: present
  delegate_to: localhost

- name: Remove a Zabbix template
  a9f.zabbix.template:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_token: "{{ zabbix_api_token }}"
    name: "My Template"
    state: absent
  delegate_to: localhost

- name: Use user/password authentication instead of a token
  a9f.zabbix.template:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_user: "Admin"
    api_password: "{{ zabbix_password }}"
    src: "{{ playbook_dir }}/files/my_template.yml"
    state: present
  delegate_to: localhost

- name: Use module_defaults to share API connection parameters
  hosts: localhost
  module_defaults:
    a9f.zabbix.template:
      api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
      api_token: "{{ zabbix_api_token }}"
  tasks:
    - name: Manage Zabbix templates
      a9f.zabbix.template:
        src: "{{ item }}"
        state: present
      loop: "{{ query('fileglob', 'files/templates/*.yml') }}"
'''

RETURN = r'''
templateids:
  description: List of template IDs deleted by the operation.
  type: list
  elements: str
  returned: when state=absent and the template was found and deleted
  sample: ["10001"]
'''

import json
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url


# Import rules for configuration.import: create and update on import,
# but do not delete items absent from the imported YAML.
_IMPORT_RULES = {
    'templates':          {'createMissing': True, 'updateExisting': True,                       },
    'templateDashboards': {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    'templateLinkage':    {'createMissing': True,                         'deleteMissing': False},
    'items':              {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    'discoveryRules':     {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    'triggers':           {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    'graphs':             {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    'httptests':          {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
    'valueMaps':          {'createMissing': True, 'updateExisting': True, 'deleteMissing': False},
}


def _api_request(module, url, method, params):
    """POST a JSON-RPC request and return the parsed response dict.

    Calls module.fail_json on HTTP errors, non-200 responses, JSON parse
    failures, or when the response contains an 'error' key.
    """
    body = json.dumps({
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': 1,
    })
    headers = module.params['_auth_headers']

    response, info = fetch_url(
        module,
        url,
        data=body,
        method='POST',
        headers=headers,
        unredirected_headers=['Authorization'],
    )

    if info['status'] != 200:
        module.fail_json(
            msg='Zabbix API request failed: HTTP %s — %s' % (info['status'], info.get('msg', ''))
        )

    try:
        result = json.loads(response.read())
    except (ValueError, AttributeError) as exc:
        module.fail_json(msg='Failed to parse Zabbix API response as JSON: %s' % str(exc))

    if 'error' in result:
        err = result['error']
        module.fail_json(
            msg='Zabbix API %s failed: %s' % (
                method,
                err.get('data', err.get('message', str(err))),
            )
        )

    return result


def _build_auth_headers(module):
    """Resolve credentials and return HTTP headers with an Authorization value.

    Uses a bearer token directly when api_token is set. Otherwise performs a
    user.login call and uses the returned session token as a bearer token
    (Zabbix 6.4+ style).
    """
    if module.params['api_token']:
        return {
            'Content-Type': 'application/json-rpc',
            'Authorization': 'Bearer ' + module.params['api_token'],
        }

    # Fall back to user.login
    body = json.dumps({
        'jsonrpc': '2.0',
        'method': 'user.login',
        'params': {
            'username': module.params['api_user'],
            'password': module.params['api_password'],
        },
        'id': 1,
    })

    response, info = fetch_url(
        module,
        module.params['api_url'],
        data=body,
        method='POST',
        headers={'Content-Type': 'application/json'},
    )

    if info['status'] != 200:
        module.fail_json(msg='Zabbix user.login request failed: HTTP %s' % info['status'])

    try:
        result = json.loads(response.read())
    except (ValueError, AttributeError) as exc:
        module.fail_json(msg='Failed to parse user.login response as JSON: %s' % str(exc))

    if 'error' in result:
        err = result['error']
        module.fail_json(
            msg='Zabbix user.login failed: %s' % err.get('data', err.get('message', str(err)))
        )

    return {
        'Content-Type': 'application/json-rpc',
        'Authorization': 'Bearer ' + result['result'],
    }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type='str', default='present', choices=['present', 'absent']),
            src=dict(type='path'),
            template=dict(type='dict'),
            name=dict(type='str'),
            api_url=dict(type='str', required=True),
            api_token=dict(type='str', no_log=True, default=''),
            api_user=dict(type='str', default=''),
            api_password=dict(type='str', no_log=True, default=''),
            validate_certs=dict(type='bool', default=True),
        ),
        mutually_exclusive=[
            ['src', 'template'],
        ],
        required_if=[
            ['state', 'absent', ['name']],
        ],
        supports_check_mode=False,
    )

    state = module.params['state']
    url = module.params['api_url']

    if not url:
        module.fail_json(
            msg="api_url must be set to the full URL of the Zabbix JSON-RPC API endpoint "
                "(e.g. 'https://zabbix.example.com/zabbix/api_jsonrpc.php')."
        )

    if not module.params['api_token'] and not (module.params['api_user'] and module.params['api_password']):
        module.fail_json(
            msg='No authentication configured. Set api_token (preferred) or both api_user and api_password.'
        )

    if state == 'present' and not module.params['src'] and not module.params['template']:
        module.fail_json(msg="One of 'src' or 'template' is required when state=present.")

    # Stash headers in params so _api_request can pick them up without
    # threading them through every call.
    module.params['_auth_headers'] = _build_auth_headers(module)

    if state == 'present':
        if module.params['src']:
            try:
                with open(module.params['src'], 'r') as fh:
                    template_yaml = fh.read()
            except IOError as exc:
                module.fail_json(
                    msg='Failed to read template file %s: %s' % (module.params['src'], str(exc))
                )
        else:
            template_yaml = yaml.dump(
                module.params['template'],
                default_flow_style=False,
                indent=2,
                allow_unicode=True,
            )

        _api_request(module, url, 'configuration.import', {
            'format': 'yaml',
            'rules': _IMPORT_RULES,
            'source': template_yaml,
        })

        module.exit_json(changed=True)

    else:  # state == 'absent'
        result = _api_request(module, url, 'template.get', {
            'filter': {'host': [module.params['name']]},
            'output': ['templateid'],
        })

        found = result.get('result', [])
        if not found:
            module.exit_json(
                changed=False,
                msg="Template '%s' not found in Zabbix — nothing to delete." % module.params['name'],
            )

        templateids = [t['templateid'] for t in found]
        _api_request(module, url, 'template.delete', templateids)

        module.exit_json(changed=True, templateids=templateids)


if __name__ == '__main__':
    main()
