#!/usr/bin/python
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: Andreas Wolf
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: host
short_description: Manage Zabbix hosts via the HTTP JSON-RPC API
version_added: "1.0.0"
description:
  - Creates, updates (idempotently), or removes Zabbix host objects using the
    Zabbix HTTP JSON-RPC API.
  - All HTTP requests are made from the host on which the task runs. For
    controller-side execution, use C(delegate_to: localhost) or run the task
    in a play that targets C(localhost).
  - When O(state=present) the module only reports C(changed) when the host
    configuration actually differs from the desired state.
  - When O(state=absent) the module is idempotent; it is a no-op if the host
    does not exist.
options:
  state:
    description:
      - Whether the host should be V(present) or V(absent).
    type: str
    choices: [present, absent]
    default: present
  name:
    description:
      - Technical host name (the C(host) field in the Zabbix API).
      - Must be unique within the Zabbix instance.
    type: str
    required: true
  visible_name:
    description:
      - Human-readable display name (the C(name) field in the Zabbix API).
      - When omitted (V(null)) the field is left untouched on update and
        defaults to the technical name on create.
    type: str
    default: null
  description:
    description:
      - Free-text description of the host.
      - When omitted (V(null)) the field is left untouched on update.
    type: str
    default: null
  status:
    description:
      - Whether monitoring is V(enabled) or V(disabled) for this host.
    type: str
    choices: [enabled, disabled]
    default: enabled
  host_groups:
    description:
      - List of host group names the host should belong to.
      - Required when O(state=present).
      - All existing group memberships are replaced with this list.
    type: list
    elements: str
    default: null
  templates:
    description:
      - List of template names to link directly to the host.
      - An empty list unlinks all templates.
      - All existing direct template links are replaced with this list.
    type: list
    elements: str
    default: []
  interfaces:
    description:
      - List of host interfaces.
      - When omitted (V(null)) existing interfaces are not modified.
      - An empty list removes all interfaces.
      - Each interface dict must include C(type) (V(agent), V(snmp), V(ipmi),
        or V(jmx)), C(useip) (bool), and C(port). Either C(ip) or C(dns) is
        required depending on C(useip). C(main) defaults to V(true).
    type: list
    elements: dict
    default: null
  tags:
    description:
      - List of host tags as dicts with C(tag) and C(value) keys.
      - An empty list removes all tags.
      - All existing tags are replaced with this list.
    type: list
    elements: dict
    default: []
  macros:
    description:
      - List of host macros as dicts with C(macro) and C(value) keys.
      - Macro names are case-insensitive; Zabbix stores them uppercase.
      - An empty list removes all macros.
      - All existing macros are replaced with this list.
    type: list
    elements: dict
    default: []
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
- name: Ensure a host exists with an agent interface
  a9f.zabbix.host:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_token: "{{ zabbix_api_token }}"
    name: "web01.example.com"
    visible_name: "Web Server 01"
    host_groups:
      - "Linux servers"
    templates:
      - "Linux by Zabbix agent"
    interfaces:
      - type: agent
        useip: true
        ip: "192.0.2.10"
        dns: ""
        port: "10050"
        main: true
    state: present
  delegate_to: localhost

- name: Disable monitoring for a host
  a9f.zabbix.host:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_token: "{{ zabbix_api_token }}"
    name: "web01.example.com"
    host_groups:
      - "Linux servers"
    status: disabled
    state: present
  delegate_to: localhost

- name: Remove a host
  a9f.zabbix.host:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_token: "{{ zabbix_api_token }}"
    name: "web01.example.com"
    state: absent
  delegate_to: localhost

- name: Use user/password authentication instead of a token
  a9f.zabbix.host:
    api_url: "https://zabbix.example.com/zabbix/api_jsonrpc.php"
    api_user: "Admin"
    api_password: "{{ zabbix_password }}"
    name: "web01.example.com"
    host_groups:
      - "Linux servers"
    state: present
  delegate_to: localhost
'''

RETURN = r'''
hostid:
  description: ID of the host that was created or updated.
  type: str
  returned: when state=present
  sample: "10084"
hostids:
  description: List of host IDs that were deleted.
  type: list
  elements: str
  returned: when state=absent and the host was found and deleted
  sample: ["10084"]
'''

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import fetch_url


_INTERFACE_TYPE_MAP = {
    'agent': 1,
    'snmp': 2,
    'ipmi': 3,
    'jmx': 4,
}


# ---------------------------------------------------------------------------
# Helpers copied verbatim from template.py
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Name resolution
# ---------------------------------------------------------------------------

def _resolve_group_names(module, url, names):
    """Return {name: groupid} for each name in *names*.

    Fails the module if any name is not found in Zabbix.
    """
    result = _api_request(module, url, 'hostgroup.get', {
        'filter': {'name': names},
        'output': ['groupid', 'name'],
    })
    found = {g['name']: g['groupid'] for g in result.get('result', [])}
    missing = [n for n in names if n not in found]
    if missing:
        module.fail_json(
            msg='The following host groups were not found in Zabbix: %s' % ', '.join(missing)
        )
    return found


def _resolve_template_names(module, url, names):
    """Return {name: templateid} for each name in *names*.

    Fails the module if any name is not found in Zabbix.
    """
    result = _api_request(module, url, 'template.get', {
        'filter': {'host': names},
        'output': ['templateid', 'host'],
    })
    found = {t['host']: t['templateid'] for t in result.get('result', [])}
    missing = [n for n in names if n not in found]
    if missing:
        module.fail_json(
            msg='The following templates were not found in Zabbix: %s' % ', '.join(missing)
        )
    return found


# ---------------------------------------------------------------------------
# Host lookup
# ---------------------------------------------------------------------------

def _get_host(module, url, name):
    """Return the first host dict matching *name*, or None."""
    result = _api_request(module, url, 'host.get', {
        'filter': {'host': [name]},
        'output': 'extend',
        'selectGroups': ['groupid'],
        'selectParentTemplates': ['templateid', 'host'],
        'selectInterfaces': 'extend',
        'selectTags': 'extend',
        'selectMacros': 'extend',
    })
    hosts = result.get('result', [])
    return hosts[0] if hosts else None


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def _normalize_tags(tags):
    """Return a sorted list of (tag, value) tuples."""
    return sorted((t.get('tag', ''), t.get('value', '')) for t in tags)


def _normalize_macros(macros):
    """Return a sorted list of (MACRO, value) tuples (Zabbix stores uppercase)."""
    return sorted((m.get('macro', '').upper(), m.get('value', '')) for m in macros)


def _normalize_interfaces(interfaces_raw):
    """Normalise a list of interface dicts to consistent Python types.

    Converts:
    - type: string name → int via _INTERFACE_TYPE_MAP
    - useip: bool/int/str → int (1 or 0)
    - main: bool/int/str/omitted → int (1 or 0), default 1
    - port: kept as str
    - ip/dns: default to '' when absent
    """
    result = []
    for iface in interfaces_raw:
        raw_type = iface.get('type')
        if isinstance(raw_type, str):
            type_int = _INTERFACE_TYPE_MAP.get(raw_type.lower())
        else:
            type_int = int(raw_type)

        raw_useip = iface.get('useip', 0)
        useip_int = 1 if raw_useip in (True, 1, '1') else 0

        raw_main = iface.get('main', True)
        main_int = 1 if raw_main in (True, 1, '1') else 0

        result.append({
            'type': type_int,
            'useip': useip_int,
            'main': main_int,
            'ip': str(iface.get('ip', '')),
            'dns': str(iface.get('dns', '')),
            'port': str(iface.get('port', '')),
        })
    return result


def _validate_interfaces(module):
    """Fail early if any interface has an unknown type string."""
    for iface in module.params['interfaces']:
        raw_type = iface.get('type')
        if isinstance(raw_type, str) and raw_type.lower() not in _INTERFACE_TYPE_MAP:
            module.fail_json(
                msg="Invalid interface type '%s'. Must be one of: %s."
                    % (raw_type, ', '.join(sorted(_INTERFACE_TYPE_MAP)))
            )


# ---------------------------------------------------------------------------
# Interface diffing
# ---------------------------------------------------------------------------

def _iface_match_key(iface):
    """Return the tuple used to match desired vs current interfaces."""
    return (
        int(iface['type']),
        int(iface['useip']),
        str(iface.get('ip', '')),
        str(iface.get('dns', '')),
        str(iface['port']),
    )


def _diff_interfaces(desired_normalized, current_from_api):
    """Compute (to_create, to_update, to_delete) sets/lists.

    - to_create: desired entries with no matching current entry
    - to_update: matched entries where 'main' differs (includes interfaceid)
    - to_delete: interfaceid strings for current entries with no desired match
    """
    # Build a lookup from match-key → current interface dict
    current_by_key = {}
    for iface in current_from_api:
        key = (
            int(iface['type']),
            int(iface['useip']),
            str(iface.get('ip', '')),
            str(iface.get('dns', '')),
            str(iface['port']),
        )
        current_by_key[key] = iface

    to_create = []
    to_update = []
    matched_keys = set()

    for desired in desired_normalized:
        key = _iface_match_key(desired)
        if key in current_by_key:
            matched_keys.add(key)
            current = current_by_key[key]
            if int(current.get('main', 0)) != desired['main']:
                entry = dict(desired)
                entry['interfaceid'] = current['interfaceid']
                to_update.append(entry)
        else:
            to_create.append(desired)

    to_delete = [
        iface['interfaceid']
        for key, iface in current_by_key.items()
        if key not in matched_keys
    ]

    return to_create, to_update, to_delete


def _apply_interface_diff(module, url, hostid, desired, current):
    """Apply interface create/update/delete. Returns True if anything changed."""
    desired_normalized = _normalize_interfaces(desired)
    to_create, to_update, to_delete = _diff_interfaces(desired_normalized, current)

    changed = False

    # Create first — avoids "no main interface" constraint violations when
    # the new main replaces the old one.
    if to_create:
        for iface in to_create:
            params = dict(iface)
            params['hostid'] = hostid
            _api_request(module, url, 'hostinterface.create', params)
        changed = True

    if to_update:
        for iface in to_update:
            _api_request(module, url, 'hostinterface.update', iface)
        changed = True

    if to_delete:
        _api_request(module, url, 'hostinterface.delete', to_delete)
        changed = True

    return changed


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

def _ensure_present(module, url):
    """Ensure the host exists and matches desired state. Returns (changed, result)."""
    p = module.params
    name = p['name']
    visible_name = p['visible_name']
    description = p['description']
    status_str = p['status']
    desired_status = 0 if status_str == 'enabled' else 1
    host_groups = p['host_groups']
    templates = p['templates']
    tags = p['tags']
    macros = p['macros']
    interfaces = p['interfaces']

    # Resolve group names → IDs
    group_map = _resolve_group_names(module, url, host_groups)
    desired_groupids = set(group_map.values())

    # Resolve template names → IDs (skip API call when list is empty)
    desired_templateids = set()
    if templates:
        template_map = _resolve_template_names(module, url, templates)
        desired_templateids = set(template_map.values())

    host = _get_host(module, url, name)

    if host is None:
        # Host does not exist — create it
        create_params = {
            'host': name,
            'groups': [{'groupid': gid} for gid in desired_groupids],
            'templates': [{'templateid': tid} for tid in desired_templateids],
            'tags': tags,
            'macros': macros,
            'status': desired_status,
        }
        if visible_name is not None:
            create_params['name'] = visible_name
        if description is not None:
            create_params['description'] = description
        if interfaces is not None:
            create_params['interfaces'] = _normalize_interfaces(interfaces)

        result = _api_request(module, url, 'host.create', create_params)
        hostid = result['result']['hostids'][0]
        return True, {'hostid': hostid}

    # Host exists — compare fields
    hostid = host['hostid']
    update_params = {'hostid': hostid}
    changed = False

    if int(host.get('status', 0)) != desired_status:
        update_params['status'] = desired_status
        changed = True

    if visible_name is not None and host.get('name') != visible_name:
        update_params['name'] = visible_name
        changed = True

    if description is not None and host.get('description', '') != description:
        update_params['description'] = description
        changed = True

    current_groupids = {g['groupid'] for g in host.get('groups', [])}
    if current_groupids != desired_groupids:
        update_params['groups'] = [{'groupid': gid} for gid in desired_groupids]
        changed = True

    current_templateids = {t['templateid'] for t in host.get('parentTemplates', [])}
    if current_templateids != desired_templateids:
        update_params['templates'] = [{'templateid': tid} for tid in desired_templateids]
        changed = True

    if _normalize_tags(host.get('tags', [])) != _normalize_tags(tags):
        update_params['tags'] = tags
        changed = True

    if _normalize_macros(host.get('macros', [])) != _normalize_macros(macros):
        update_params['macros'] = macros
        changed = True

    if changed:
        _api_request(module, url, 'host.update', update_params)

    if interfaces is not None:
        iface_changed = _apply_interface_diff(module, url, hostid, interfaces, host.get('interfaces', []))
        changed = changed or iface_changed

    return changed, {'hostid': hostid}


def _ensure_absent(module, url):
    """Remove the host if it exists. Returns (changed, result)."""
    host = _get_host(module, url, module.params['name'])
    if host is None:
        return False, {}

    hostid = host['hostid']
    _api_request(module, url, 'host.delete', [hostid])
    return True, {'hostids': [hostid]}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type='str', default='present', choices=['present', 'absent']),
            name=dict(type='str', required=True),
            visible_name=dict(type='str', default=None),
            description=dict(type='str', default=None),
            status=dict(type='str', default='enabled', choices=['enabled', 'disabled']),
            host_groups=dict(type='list', elements='str', default=None),
            templates=dict(type='list', elements='str', default=[]),
            interfaces=dict(type='list', elements='dict', default=None),
            tags=dict(type='list', elements='dict', default=[]),
            macros=dict(type='list', elements='dict', default=[]),
            api_url=dict(type='str', required=True),
            api_token=dict(type='str', no_log=True, default=''),
            api_user=dict(type='str', default=''),
            api_password=dict(type='str', no_log=True, default=''),
            validate_certs=dict(type='bool', default=True),
        ),
        required_if=[
            ['state', 'present', ['host_groups']],
        ],
        supports_check_mode=False,
    )

    url = module.params['api_url']
    name = module.params['name']
    state = module.params['state']

    # Validation guards (in order, before any network call)
    if not url:
        module.fail_json(
            msg="api_url must be set to the full URL of the Zabbix JSON-RPC API endpoint "
                "(e.g. 'https://zabbix.example.com/zabbix/api_jsonrpc.php')."
        )

    if not name:
        module.fail_json(msg="'name' must be a non-empty string.")

    if not module.params['api_token'] and not (module.params['api_user'] and module.params['api_password']):
        module.fail_json(
            msg='No authentication configured. Set api_token (preferred) or both api_user and api_password.'
        )

    if state == 'present' and module.params['host_groups'] is not None and not module.params['host_groups']:
        module.fail_json(msg="host_groups must contain at least one group name when state=present.")

    if module.params['interfaces'] is not None:
        _validate_interfaces(module)

    module.params['_auth_headers'] = _build_auth_headers(module)

    if state == 'present':
        changed, result = _ensure_present(module, url)
    else:
        changed, result = _ensure_absent(module, url)

    module.exit_json(changed=changed, **result)


if __name__ == '__main__':
    main()
