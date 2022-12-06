import argparse
from pathlib import Path

from diopter.compiler import CComp, CompilerExe

from dead.config import DeadConfig, dump_config, interactive_init


def __arg_to_compiler_exe(arg: str | None) -> CompilerExe | None:
    if not arg:
        return None
    return CompilerExe.from_path(Path(arg))


def __arg_to_ccomp(arg: str | None) -> CComp | None:
    if not arg:
        return None
    return CComp(exe=Path(arg))


def __arg_to_path(arg: str | None) -> Path | None:
    if not arg:
        return None
    return Path(arg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clang",
        type=__arg_to_compiler_exe,
        help="clang binary used for sanitizing test cases."
        " (Temporarily overrides what is stored in the configuration.)",
    )
    parser.add_argument(
        "--gcc",
        type=__arg_to_compiler_exe,
        help="gcc binary used for sanitizing test cases."
        " (Temporarily overrides what is stored in the configuration.)",
    )
    parser.add_argument(
        "--ccomp",
        type=__arg_to_ccomp,
        help="compcert binary used for sanitizing test cases."
        " (Temporarily overrides what is stored in the configuration.)",
    )
    parser.add_argument(
        "--csmith",
        type=__arg_to_path,
        help="csmith binary used for generating test cases."
        " (Temporarily overrides what is stored in the configuration.)",
    )
    parser.add_argument(
        "--csmith-include-path",
        type=__arg_to_path,
        help="csmith include path."
        " (Temporarily overrides what is stored in the configuration.)",
    )
    parser.add_argument(
        "--creduce",
        type=__arg_to_path,
        help="creduce binary used for reducing test cases."
        " (Temporarily overrides what is stored in the configuration.)",
    )
    parser.add_argument(
        "--update-config",
        action=argparse.BooleanOptionalAction,
        help="Make the temporary configuration overrides permanent.",
    )
    return parser.parse_args()


def run_as_module() -> None:
    args = parse_args()
    interactive_init(
        clang=args.clang,
        gcc=args.gcc,
        ccomp=args.ccomp,
        csmith=args.csmith,
        csmith_include_path=args.csmith_include_path,
        creduce=args.creduce,
    )
    if args.update_config:
        dump_config()

    print(DeadConfig.get_config())
