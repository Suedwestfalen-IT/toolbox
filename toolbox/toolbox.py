import argparse
import importlib
import importlib.util
import logging
import os

import sys
import inspect
from typing import Type, Optional, Union

import yaml

from toolbox.base import BaseToolboxModule

class Toolbox:

    """
    Transform your one-off scripts into powerful, reusable YAML workflows—effortlessly
    export, import, and analyze your data for seamless, ad-hoc solutions.
    """

    def __init__(self, config:Optional[Union[str, dict]] = None, verbose=False):
        """
        Initializes the Toolbox instance.

        Args:
            config (str | None | dict): Configuration for the toolbox. It can be a string, None, or a dictionary.
            verbose (bool, optional): If True, sets the logger to DEBUG level. Defaults to False.

        Sets up a logger for the toolbox instance with the specified verbosity level.
        """

        config_template = {
            'web': {
                'groups': {}
            }
        }
        self.config = config_template

        # Load configuration
        if config is None:
            config = os.path.expanduser("~/.config/toolbox.yaml")

        if isinstance(config, str):
            if not os.path.exists(config):
                raise FileNotFoundError(f"Configuration file {config} does not exist.")
            with open(config, "r", encoding="utf-8") as fh:
                if loaded_config := yaml.safe_load(fh):
                    self.config.update(loaded_config)

        elif isinstance(config, dict):
            self.config.update(config)
        else:
            raise ValueError("Invalid config type. Must be None, str, or dict.")

        # Setup Logger
        self.logger = logging.getLogger("toolbox")

        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)

        self.logger.addHandler(handler)

        # # Load Search Paths
        search_paths = self.config.get("toolbox", {}).get("module_search_paths", [])
        if not search_paths:
            search_paths = self.config.get("toolbox", {}).get("modul_search_paths", [])
        # search_paths.append(os.getcwd())
        for base_path in search_paths:
            self.logger.debug(f"add search path: {base_path}")
            sys.path.insert(0, base_path)

        self.logger.info("Toolbox initialized")

    def load_module(self, module_name: str) -> Type[BaseToolboxModule]|None:
        """
        Loads a module by its fully qualified name.

        Args:
            module_name (str): The fully qualified name of the module to be loaded.

        Returns:
            Type[BaseToolboxModule]: The class object of the loaded module.
        """

        package_name, module = module_name.split(".", 1)
        prefix = "toolbox"

        if package_name != "builtin":
            prefix = "toolbox_modules"
            importlib.import_module(f"{prefix}.{package_name}")

        try:
            full_module_name = f"{prefix}.{package_name}.{module}"
            self.logger.debug(f"loading {full_module_name}")
            module = importlib.import_module(full_module_name)
        except ImportError as e:
            self.logger.error(f"Error loading module {module_name}: {e}")
            return None

        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseToolboxModule) and obj != BaseToolboxModule:
                return obj

        self.logger.error(f"No ToolboxModule class found in module {module_name}")
        return None

    def init_module(self, module_class: Type[BaseToolboxModule], arguments: list | dict) -> BaseToolboxModule:
        """ Initalizes a Module with specified args, for reusability of the toolbox instance """

        command = module_class.__module__.removeprefix("toolbox.").removeprefix("toolbox_modules.")
        if isinstance(arguments, list):
            argparser = argparse.ArgumentParser(prog=command, description=module_class.HELP)
            module_class.update_parser(argparser)
            args = argparser.parse_args(arguments)
            parsed_args = module_class.Arguments.parse_obj(vars(args))

        elif isinstance(arguments, dict):
            parsed_args = module_class.Arguments.parse_obj(arguments)
        else:
            raise ValueError("Invalid arguments type. Must be list or dict.")

        self.logger.debug(f"Arguments: {parsed_args}")

        # Initialize module
        module = module_class(args=parsed_args, config=self.config, logger=self.logger.getChild(command))

        return module

    def list_modules(self, package_name: str): # pylint: disable=too-many-locals,too-many-branches
        """ Get all Toolbox Modules from given package retruns a generator with strings """
        prefix = "toolbox"

        if package_name != "builtin":
            prefix = "toolbox_modules"

        full_package_name = f"{prefix}.{package_name}"
        if package_name == "toolbox_modules":
            full_package_name = package_name

        try:
            package = importlib.import_module(full_package_name)
        except Exception as e: # pylint: disable=broad-exception-caught
            self.logger.error(f"Fehler beim Import von {full_package_name}: {e}")
            return

        if not hasattr(package, '__path__'):
            self.logger.warning(f"{full_package_name} besitzt kein __path__-Attribut und kann daher nicht rekursiv durchsucht werden.")
            return

        # Iteriere über alle Pfade des Pakets (funktioniert auch bei Namespace-Paketen)
        for package_path in package.__path__: # pylint: disable=too-many-nested-blocks
            for root, _, files in os.walk(package_path):
                for file in files:
                    if file.endswith('.py') and file != '__init__.py':
                        # Erstelle den Modulnamen basierend auf dem relativen Pfad
                        rel_dir = os.path.relpath(root, package_path)
                        module_name = os.path.splitext(file)[0]
                        if rel_dir == '.':
                            full_module_name = f"{package.__name__}.{module_name}"
                        else:
                            full_module_name = f"{package.__name__}.{rel_dir.replace(os.sep, '.')}.{module_name}"
                        try:
                            mod = importlib.import_module(full_module_name)
                        except Exception as e: # pylint: disable=broad-exception-caught
                            self.logger.error(f"Fehler beim Import des Moduls {full_module_name}: {e}")
                            continue

                        # Prüfe, ob im Modul eine Klasse namens ToolboxModule existiert
                        for member_name, _ in inspect.getmembers(mod, inspect.isclass):
                            if member_name == "ToolboxModule":
                                full_module_name = full_module_name.removeprefix("toolbox_modules.")
                                full_module_name = full_module_name.removeprefix("toolbox.")
                                self.logger.info(f"{full_module_name}")
                                yield full_module_name

    def run(self, command: str, arguments: list | dict, input: Optional[str] = None, output: Optional[str] = None): # pylint: disable=redefined-builtin
        """
        Executes a command with the specified arguments.

        Args:
            command (str): The CLI command to be executed.
            arguments (list | dict): A list or dictionary of arguments to be passed to the command.
            input (str, optional): The input to be provided to the command. Can be None, '-' for stdin, or a path to a YAML file. Defaults to None.
            output (str, optional): The output to be captured from the command. Can be None, '-' for stdout or a path to a YAML file. Defaults to None.

        Returns:
            dict: A dictionary containing the module's output.
        """

        if len(command.split('.')) == 1:
            return list(self.list_modules(command))

        # Handle remaining arguments
        module_class = self.load_module(command)
        if module_class is None:
            return {} # Todo: raise exception or something

        module = self.init_module(module_class, arguments)

        # Get Input
        if input is not None:
            if input == '-':
                input_data = yaml.safe_load(sys.stdin.read())
            else:
                with open(input, "r", encoding="utf-8") as fh:
                    input_data = yaml.safe_load(fh)
        else:
            input_data = None

        # Process
        output_data = {command: module.run(input_data)}

        # Send Output
        output_yaml = yaml.dump(output_data, allow_unicode=True, default_flow_style=False)

        if output is not None:
            if output == '-':
                print(output_yaml)
            else:
                with open(output, 'w', encoding="utf-8") as file:
                    file.write(output_yaml)

        return output_data
