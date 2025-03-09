import argparse
import importlib
import logging
import os
# import pkgutil
import sys
import inspect
from typing import Type

import yaml

from toolbox.base import BaseToolboxModule




class Toolbox:

    """
    Transform your one-off scripts into powerful, reusable YAML workflows—effortlessly
    export, import, and analyze your data for seamless, ad-hoc solutions.
    """

    def __init__(self, config:str|None|dict, verbose=False):
        """
        Initializes the Toolbox instance.

        Args:
            config (str | None | dict): Configuration for the toolbox. It can be a string, None, or a dictionary.
            verbose (bool, optional): If True, sets the logger to DEBUG level. Defaults to False.

        Sets up a logger for the toolbox instance with the specified verbosity level.
        """

        # Load configuration
        if config is None:
            config_path = os.path.expanduser("~/.config/toolbox.yaml")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as fh:
                    self.config = yaml.safe_load(fh)
            else:
                self.config = {}
        elif isinstance(config, str):
            if not os.path.exists(config):
                raise FileNotFoundError(f"Configuration file {config} does not exist.")
            with open(config, "r", encoding="utf-8") as fh:
                self.config = yaml.safe_load(fh)
        elif isinstance(config, dict):
            self.config = config
        else:
            raise ValueError("Invalid config type. Must be None, str, or dict.")



        # Setup Logger
        self.logger = logging.getLogger("toolbox")
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        self.logger.debug("Toolbox initialized")

    def load_module(self, module_name: str) -> Type[BaseToolboxModule]|None:
        """
        Loads a module by its fully qualified name.

        Args:
            module_name (str): The fully qualified name of the module to be loaded.

        Returns:
            Type[BaseToolboxModule]: The class object of the loaded module.
        """

        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            self.logger.error(f"Error loading module {module_name}: {e}")
            return None

        for _, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BaseToolboxModule) and obj != BaseToolboxModule:
                return obj

        self.logger.error(f"No ToolboxModule class found in module {module_name}")
        return None

    def run(self, command: str, arguments: list | dict, input: str | None = None, output: str | None = None): # pylint: disable=redefined-builtin
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

        # Handle remaining arguments
        module_class = self.load_module(command)
        if module_class is None:
            return {} # Todo: raise exception or something

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
        module = module_class(args=parsed_args, config=self.config, logger=self.logger.getChild(command.removeprefix("toolbox.")))

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

        return output_yaml



    # def find_toolbox_modules(self, package: ModuleType|str) -> Dict[str, Type[BaseToolboxModule]]:
    #     if isinstance(package, str):
    #         package = importlib.import_module(package)

    #     """Rekursiv alle Module und Subpackages durchsuchen und
    #     ein Dictionary mit vollqualifizierten Modulnamen und deren
    #     ToolboxModule-Klasse zurückgeben, falls vorhanden.
    #     """
    #     found = {}
    #     for _, name, ispkg in pkgutil.iter_modules(package.__path__):
    #         full_name = f"{package.__name__}.{name}"
    #         try:
    #             module = importlib.import_module(full_name)
    #         except ImportError as e:
    #             print(f"ImportError in {full_name}: {e}", file=sys.stderr)
    #             continue

    #         print(f"Checking {full_name}...")

    #         # Direkt prüfen, ob das Modul die Klasse ToolboxModule enthält.
    #         if hasattr(module, "ToolboxModule"):
    #             candidate = getattr(module, "ToolboxModule")
    #             if inspect.isclass(candidate):
    #                 found[full_name] = candidate

    #         # Falls es sich um ein Package handelt, rekursiv weitersuchen.
    #         if ispkg:
    #             found.update(self.find_toolbox_modules(module))
    #     return found
