import argparse

from toolbox import Toolbox

def main():
    """
    Entry point for the toolbox application.

    This function parses command-line arguments and initializes the Toolbox
    with the provided configuration and verbosity settings. It then runs the
    specified command with any additional arguments.

    Command-line arguments:
    - -c, --config <file>: Path to the config.yml file (optional).
    - -i, --input <file>: YAML input for the module (optional).
    - -o, --output <file>: Path to store module output (optional, default is "-").
    - -v, --verbose: Enable verbose mode (optional, default is False).
    - command: Mode or module name to run.
    - arguments: Additional arguments for the selected mode/module.

    Returns:
    None
    """


    # First get generic paramters
    parser = argparse.ArgumentParser(prog="toolbox", add_help=True)
    parser.add_argument("-c", "--config", metavar="<file>", help="Path to config.yml", required=False)
    parser.add_argument("-i", "--input", metavar="<file>", help="YAML-Input for module", required=False)
    parser.add_argument(
        "-o", "--output", metavar="<file>", help="Path to store module output", required=False, default="-"
    )
    parser.add_argument("-v", "--verbose", help="Verbose Mode", required=False, action="store_true", default=False)

    parser.add_argument("command", help="Mode or module name")
    parser.add_argument("arguments", nargs=argparse.REMAINDER, help="Additional arguments for the selected mode/module")
    args = parser.parse_args()

    # then run the toolbox

    tb = Toolbox(args.config, args.verbose)
    tb.run(args.command, args.arguments, args.input, args.output)

if __name__ == "__main__":
    main()
