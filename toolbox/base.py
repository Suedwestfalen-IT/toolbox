import argparse
import logging
from logging import Logger
from typing import Any, List, Optional, Type, Dict
import abc


from pydantic import BaseModel, Field

class ConfigModel(BaseModel):
    """
    Pydantic model for configuration.
    """

    @staticmethod
    def add_argument( # pylint: disable=too-many-arguments
        *flags: str,
        action: Any = None,
        nargs: Any = None,
        const: Any = None,
        default: Any = None,
        choices: Any = None,
        help: Optional[str] = None, # pylint: disable=redefined-builtin # allows same call as the argparse function
        metavar: Optional[str] = None,
        dest: Optional[str] = None,
        deprecated: Any = None,
    ) -> Any:
        """
        Helper-Funktion für CLI-Argumente, die Parameter ähnlich wie ArgumentParser.add_argument()
        akzeptiert. Die Werte für 'required' und 'type' werden später aus dem Modell abgeleitet.
        """
        return Field(
            default,
            # alias=flags[0] if flags else None,
            description=help,
            flags=flags,       # Speichert alle Flags (z. B. "-c", "--config")
            action=action,
            nargs=nargs,
            const=const,
            choices=choices,
            metavar=metavar,
            dest=dest,
            deprecated=deprecated,
        )

class BaseToolboxModule(abc.ABC):
    """
    Abstract base class for all Toolbox Modules.
    """
    HELP: str = "You should implement this in your subclass"  # Description for parser

    OUTPUT_HTML_JINJA2: Optional[str] = None

    @staticmethod
    def flat_output(output_data: Dict[str, Any]) -> List[Dict[str, str]]: # pylint: disable=unused-argument
        """ Flat the output of the module """

        raise NotImplementedError("flat_output not implemented!")


    class Arguments(ConfigModel):
        """
        Pydantic model for CLI arguments.
        """

    @classmethod
    def update_parser(cls, parser: argparse.ArgumentParser) -> None:
        """
        Aktualisiert den übergebenen ArgumentParser anhand der inneren Arguments-Klasse,
        sofern diese vorhanden ist.
        """
        if hasattr(cls, "Arguments"):
            model: Type[BaseModel] = cls.Arguments  # Typischerweise ein Pydantic-Modell
            for field_name, model_field in model.__fields__.items():
                field_info = getattr(model_field, "field_info", model_field)
                extras = field_info.json_schema_extra

                # Verwende die in add_argument hinterlegten Flags; falls nicht vorhanden, generiere ein Long-Flag
                flags = extras.get("flags")
                positional = False
                if not flags:
                    positional = True
                    flags = [field_name]

                # Verwende den Default-Wert aus dem Modell
                default = model_field.default

                args_dict = {
                    "action": extras.get("action"),
                    "nargs": extras.get("nargs"),
                    "const": extras.get("const"),
                    "default": default,
                    # "type": model_field.annotation, # ToDo: Implement type conversion, pydantic stuff is Union
                    "choices": extras.get("choices"),
                    "required": model_field.is_required(),
                    "help": field_info.description,
                    "metavar": extras.get("metavar"),
                    "dest": extras.get("dest"),
                }

                if positional:
                    if "required" in args_dict:
                        del args_dict["required"]
                else:
                    if not args_dict['dest']:
                        args_dict['dest'] = field_name

                # Delete all None values
                args_dict = {k: v for k, v in args_dict.items() if v is not None}

                parser.add_argument(
                    *flags,
                    **args_dict,
                )

    def __init__(
        self,
        args: dict | ConfigModel | None = None,
        config: Optional[dict[str, Any]] = None,
        logger: Optional[Logger] = None,
    ):
        if args is None:
            self.args = self.__class__.Arguments()  # Default-Werte verwenden
        elif isinstance(args, dict):
            self.args = self.__class__.Arguments(**args)  # aus einem dict parsen
        elif isinstance(args, self.__class__.Arguments):
            self.args = args
        else:
            raise ValueError("Invalid Type for args")

        self.config: dict[str, Any] = config or {}
        self.logger: Logger = logger or logging.getLogger(self.__class__.__name__)

        self.logger.debug(f"Initializing {self.__class__.__name__} module")

    @abc.abstractmethod
    def run(self, run_data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """
        Execute the module's main functionality.
        Must be implemented in the subclass.
        """
