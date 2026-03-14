# Ansible role: `a9f.zabbix.run`

The `a9f.zabbix.run` Ansible role (part if the `a9f.zabbix` Ansible collection).



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

- name: "Initialize the a9f.zabbix.run role"
  hosts: localhost
  gather_facts: false
  tasks:

    - name: "Trigger invocation of the a9f.zabbix.run role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.run"
      vars:
        run_zabbix_autoupgrade: true
```

Uninstall:

```yaml
---

- name: "Initialize the a9f.zabbix.run role"
  hosts: localhost
  gather_facts: false
  tasks:

    - name: "Trigger invocation of the a9f.zabbix.run role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.run"
      vars:
        run_zabbix_state: "absent"
```



## Supported tags<a id="tags"></a>

It might be useful and faster to only call parts of the role by using tags:

- `run_zabbix_setup`: Manage basic resources, such as packages or service users.
- `run_zabbix_config`: Manage settings, such as adapting or creating configuration files.
- `run_zabbix_service`: Manage services and daemons, such as running states and service boot configurations.

There are also tags usually not meant to be called directly but listed for the sake of completeness** and edge cases:

- `run_zabbix_always`, `always`: Tasks needed by the role itself for internal role setup and the Ansible environment.



## Dependencies<a id="dependencies"></a>

See `dependencies` in [`meta/main.yml`](./meta/main.yml).



## Compatibility<a id="compatibility"></a>

See `min_ansible_version` in [`meta/main.yml`](./meta/main.yml) and `__run_zabbix_supported_platforms` in [`vars/main.yml`](./vars/main.yml).



## External requirements<a id="requirements"></a>

There are no special requirements not covered by Ansible itself.
