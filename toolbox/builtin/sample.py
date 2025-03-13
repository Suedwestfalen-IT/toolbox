from typing import Any, Optional
from toolbox.base import BaseToolboxModule


class ToolboxModule(BaseToolboxModule):
    """
    ToolboxModule is a sample module that extends BaseToolboxModule.

    Attributes:
        HELP (str): A description of the module.

    Classes:
        Arguments (ConfigModel): A nested class that defines the arguments for the module.
            test (str): A positional test argument.
            other (str): An optional argument with short and long flags.

    Methods:
        run(run_data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
            Executes the module with the provided run data and returns a dictionary containing the test argument.
    """

    HELP: str = "This is a sample module"
    OUTPUT_HTML_JINJA2: Optional[str] = None

    def flat_output(self, output_data: dict[str, Any]) -> str:
        return """
        Flat Output for CSV or generic HTML
        Must be implemented in the subclass.
        """

    class Arguments(BaseToolboxModule.Arguments):
        test: str = BaseToolboxModule.Arguments.add_argument(help="This is a positional test argument")
        other: Optional[str] = BaseToolboxModule.Arguments.add_argument('-a','--other', help="This is other argument")

    def run(self, run_data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        return {
            "test": self.args.test,
            "other": self.args.other
        }
