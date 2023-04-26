#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# This file is part of solidity.
#
# solidity is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# solidity is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with solidity.  If not, see <http://www.gnu.org/licenses/>
#
# (c) 2023 solidity contributors.
# ------------------------------------------------------------------------------

from argparse import ArgumentParser, Namespace
import os
from pathlib import Path
import sys

# Our scripts/ is not a proper Python package so we need to modify PYTHONPATH to import from it
# pragma pylint: disable=import-error,wrong-import-position
SCRIPTS_DIR = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from common.shell_command import run_cmd

EXTERNAL_TESTS_DIR = Path(__file__).parent / "externalTests"


class ExternalTestNotFound(Exception):
    pass


def detect_external_tests() -> dict:
    # TODO: Remove `file_path.stem != "common"` when we complete the migration
    # of the external tests to python, since there will be no more
    # common.sh script in the externalTests folder.
    return {
        file_path.stem: file_path
        for file_path in Path(EXTERNAL_TESTS_DIR).iterdir()
        if file_path.is_file() and file_path.suffix == ".sh" and file_path.stem != "common"
    }


def display_available_external_tests(_) -> int:
    print("Available external tests:")
    print(*detect_external_tests().keys())
    return os.EX_OK


def run_test_script(solc_binary_type: str, solc_binary_path: Path, tests: dict) -> int:
    for test_name, test_script_path in tests.items():
        print(f"Running {test_name} external test...")
        ret = run_cmd(f"{test_script_path} {solc_binary_type} {solc_binary_path}")
        if ret != os.EX_OK:
            return ret
    return os.EX_OK


def run_external_tests(args: dict) -> int:
    solc_binary_type = args.get("solc_binary_type")
    solc_binary_path = args.get("solc_binary_path")

    all_test_scripts = detect_external_tests()
    if args.get("run_all"):
        return run_test_script(solc_binary_type, solc_binary_path, all_test_scripts)
    else:
        selected_tests = args.get("selected_tests")
        if selected_tests:
            diff_set = set(selected_tests) - set(all_test_scripts.keys())
            if diff_set:
                raise ExternalTestNotFound(
                    f"External test(s): {' '.join(diff_set)} not found"
                )
            return run_test_script(
                solc_binary_type,
                solc_binary_path,
                {k: all_test_scripts[k] for k in selected_tests},
            )
    raise ExternalTestNotFound(
        "External test was not selected. Please use --run or --run-all option"
    )


def parse_commandline() -> Namespace:
    script_description = "Script to run external Solidity tests."

    parser = ArgumentParser(description=script_description)
    subparser = parser.add_subparsers()
    list_command = subparser.add_parser(
        "list",
        help="List all available external tests.",
    )
    list_command.set_defaults(cmd=display_available_external_tests)

    run_command = subparser.add_parser(
        "test",
        help="Run external tests.",
    )
    run_command.set_defaults(cmd=run_external_tests)

    run_command.add_argument(
        "--solc-binary-type",
        dest="solc_binary_type",
        type=str,
        required=True,
        choices=["native", "solcjs"],
        help="Type of the solidity compiler binary to be used.",
    )
    run_command.add_argument(
        "--solc-binary-path",
        dest="solc_binary_path",
        type=Path,
        required=True,
        help="Path to the solidity compiler binary.",
    )

    running_mode = run_command.add_mutually_exclusive_group()
    running_mode.add_argument(
        "--run",
        metavar="TEST_NAME",
        dest="selected_tests",
        nargs="+",
        default=[],
        help="Run one or more given external tests.",
    )
    running_mode.add_argument(
        "--run-all",
        dest="run_all",
        default=False,
        action="store_true",
        help="Run all available external tests.",
    )

    return parser.parse_args()


def main():
    try:
        args = parse_commandline()
        args.cmd(vars(args))
    except ExternalTestNotFound as exception:
        print(f"Error: {exception}", file=sys.stderr)
        return os.EX_NOINPUT
    except RuntimeError as exception:
        print(f"Error: {exception}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
