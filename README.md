# Toolbox

The Toolbox is a collection of scripts designed to automate one-off data tasks such as exporting, importing, and analyzing data. In scenarios where you need to perform ad-hoc operations, this toolbox ensures you always get a standardized YAML output that can be easily manipulated, imported, or modified in other modules.

## Purpose and Motivation

Many workflows involve repetitive, manual data handling tasks that are both time-consuming and prone to errors. The Toolbox aims to streamline these processes by:

- **Reusability:** Every execution produces a consistent YAML output that can be reused across various applications.
- **Modularity:** The standardized YAML format facilitates seamless integration into different workflows.
- **Efficiency:** Automating one-off tasks minimizes manual effort and reduces the chance of errors, delivering quick and reliable results.

## Main Features

- **Data Export and Import:** Extract data from various sources and convert it into a unified YAML format.
- **Ad-hoc Analysis:** Run spontaneous analyses with outputs delivered directly in YAML.
- **Standardized Outputs:** Each script run produces a YAML file that serves as a solid foundation for further processing or integration.

## Installation

```bash
pip install toolbox
```

Or, if you are installing from source:

```bash
git clone <repository-url>
cd toolbox
pip install .
```

## Usage

### 1. CLI

Run a specific module directly from the command line by specifying its fully qualified module name along with the required parameters.

Example:

```bash
toolbox toolbox.builtin.vmware.get_vms -l WIN
python -m toolbox toolbox.builtin.vmware.get_vms -l WIN
```

In this example, the module `toolbox.builtin.vmware.get_vms` is invoked with the parameter `limit` set to `WIN`.

### 2. Python

You can also run the toolbox modules directly within your Python scripts. This allows you to programmatically execute a module and process its output.

Example:

```python
import toolbox
tb = Toolbox(config={
  'vmware': {
    'host': 'vcenter.local',
    'user': 'username',
    'password': 'password'
  }
})
result = tb.run('toolbox.builtin.vmware.get_vms', args={
    'limit': 'WIN'
})
print(result)
```

This example shows how to call the module `toolbox.builtin.vmware.get_vms` with the parameter `limit` provided.

### 3. Ansible

The toolbox can also be used as an Ansible module, enabling you to integrate its functionality into your playbooks.

Example Ansible task:

```yaml
- name: Get VMs
  toolbox:
    module: toolbox.builtin.vmware.get_vms
    limit: WIN
  register: win_vms
```

In this task, the module `toolbox.builtin.vmware.get_vms` is executed with the parameter `limit` set to `WIN`, and the output is stored in the variable `win_vms`.

## Contributing

Contributions to improve the Toolbox are welcome. If you have suggestions, improvements, or bug fixes, please submit a pull request or open an issue in the repository.

## License

This project is licensed under the [MIT License](LICENSE).
