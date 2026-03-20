# Ansible role: `a9f.zabbix.server`

The `a9f.zabbix.server` Ansible role (part of the `a9f.zabbix` Ansible collection) installs and manages the Zabbix server daemon on supported Linux platforms. This role handles OS repository setup, package installation (MySQL or PostgreSQL variant), configuration file deployment, and service lifecycle. Database provisioning and the web frontend are out of scope.



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

Installation with MySQL backend:

```yaml
---

- name: "Manage Zabbix server"
  hosts: all
  gather_facts: false
  tasks:

    - name: "Invoke the a9f.zabbix.server role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.server"
      vars:
        server_zabbix_db_type: "mysql"
        server_zabbix_db_password: "secret"
```

Installation with PostgreSQL backend:

```yaml
---

- name: "Manage Zabbix server"
  hosts: all
  gather_facts: false
  tasks:

    - name: "Invoke the a9f.zabbix.server role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.server"
      vars:
        server_zabbix_db_type: "pgsql"
        server_zabbix_db_password: "secret"
```

Uninstall:

```yaml
---

- name: "Remove Zabbix server"
  hosts: all
  gather_facts: false
  tasks:

    - name: "Invoke the a9f.zabbix.server role"
      ansible.builtin.include_role:
        name: "a9f.zabbix.server"
      vars:
        server_zabbix_state: "absent"
```



## Supported tags<a id="tags"></a>

It might be useful and faster to only call parts of the role by using tags:

- `server_zabbix_setup`: Manage basic resources, such as packages or service users.
- `server_zabbix_config`: Manage settings, such as adapting or creating configuration files.
- `server_zabbix_service`: Manage services and daemons, such as running states and service boot configurations.

There are also tags usually not meant to be called directly but listed for the sake of completeness and edge cases:

- `server_zabbix_always`, `always`: Tasks needed by the role itself for internal role setup and the Ansible environment.



## Dependencies<a id="dependencies"></a>

See `dependencies` in [`meta/main.yml`](./meta/main.yml).



## Compatibility<a id="compatibility"></a>

See `min_ansible_version` in [`meta/main.yml`](./meta/main.yml) and `__server_zabbix_supported_platforms` in [`vars/main.yml`](./vars/main.yml).



## External requirements<a id="requirements"></a>

There are no special requirements not covered by Ansible itself.
