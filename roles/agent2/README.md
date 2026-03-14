# Ansible role: `a9f.zabbix.agent2`

The `a9f.zabbix.agent2` Ansible role (part of the `a9f.zabbix` Ansible collection) installs and configures Zabbix agent 2 on supported Linux platforms.



## Table of contents<a id="toc"></a>

- [Role variables](#variables)
- [Example playbooks, using this role](#examples)
- [Supported tags](#tags)
- [Dependencies](#dependencies)
- [Compatibility](#compatibility)
- [External requirements](#requirements)



## Role variables<a id="variables"></a>

See [`defaults/main.yml`](./defaults/main.yml) for all available role parameters and their description. [`vars/main.yml`](./vars/main.yml) contains internal variables you should not override (but their description might be interesting).

Additionally, there are variables read from other roles and/or the global scope (for example, host or group vars) as follows:

- None right now.



## Example playbooks, using this role<a id="examples"></a>

Installation with automatic upgrade:

```yaml
---

- name: "Manage Zabbix agent 2"
  hosts: all
  gather_facts: false
  tasks:

    - name: "Invoke the a9f.zabbix.agent2 role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.agent2"
      vars:
        agent2_zabbix_server: "zabbix.example.com"
        agent2_zabbix_autoupgrade: true
```

Uninstall:

```yaml
---

- name: "Remove Zabbix agent 2"
  hosts: all
  gather_facts: false
  tasks:

    - name: "Invoke the a9f.zabbix.agent2 role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.agent2"
      vars:
        agent2_zabbix_state: "absent"
```



## Supported tags<a id="tags"></a>

It might be useful and faster to only call parts of the role by using tags:

- `agent2_zabbix_setup`: Manage basic resources, such as packages or service users.
- `agent2_zabbix_config`: Manage settings, such as adapting or creating configuration files.
- `agent2_zabbix_service`: Manage services and daemons, such as running states and service boot configurations.

There are also tags usually not meant to be called directly but listed for the sake of completeness and edge cases:

- `agent2_zabbix_always`, `always`: Tasks needed by the role itself for internal role setup and the Ansible environment.



## Dependencies<a id="dependencies"></a>

See `dependencies` in [`meta/main.yml`](./meta/main.yml).



## Compatibility<a id="compatibility"></a>

See `min_ansible_version` in [`meta/main.yml`](./meta/main.yml) and `__agent2_zabbix_supported_platforms` in [`vars/main.yml`](./vars/main.yml).



## External requirements<a id="requirements"></a>

There are no special requirements not covered by Ansible itself.
