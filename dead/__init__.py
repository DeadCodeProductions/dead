import argparse
from multiprocessing import cpu_count
from pathlib import Path

from diopter.compiler import CComp, CompilerExe, parse_compilation_setting_from_string

from dead.config import dump_config, interactive_init
from dead.differential_testing import DifferentialTestingMode, generate_and_test
from dead.output import write_cases_to_directory
from dead.reduction import reduce_case


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


def __arg_to_testing_mode(arg: str) -> DifferentialTestingMode:
    match arg:
        case "unidirectional":
            return DifferentialTestingMode.Unidirectional
        case "bidirectional":
            return DifferentialTestingMode.Bidirectional
        case _:
            print("Wrong testing mode")
            exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        "find missed optimizations across the two compilation commands"
    )

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
    parser.add_argument(
        "compilation_command1",
        type=str,
        help="The first compilation command used for differential testing,"
        " e.g., 'gcc -O3'",
    )
    parser.add_argument(
        "compilation_command2",
        type=str,
        help="The second compilation command used for differential testing,"
        " e.g., 'clang -O2 -march=native'",
    )

    parser.add_argument(
        "--testing_mode",
        default="bidirectional",
        choices=["unidirectional", "bidirectional"],
        help="Defines how to test between the two commands: in the unidirectional "
        "mode a case is interesting if the second command misses a marker that the "
        "first command eliminated, in the bidirectional mode (default) a case is "
        "interesting as long as at least one command misses a marker",
    )

    parser.add_argument(
        "--reduce",
        action=argparse.BooleanOptionalAction,
        help="Also reduce the discovered cases",
    )
    parser.add_argument(
        "--jobs",
        "-j",
        help="Number of parallel jobs. Defaults to all.",
        type=int,
        default=cpu_count(),
    )
    parser.add_argument(
        "--number-candidates",
        "-n",
        help="How many candidates to generate and test. Defaults to 128.",
        type=int,
        default=128,
    )
    parser.add_argument(
        "output_directory", help="Where to store the generated cases.", type=Path
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

    setting1, _, _ = parse_compilation_setting_from_string(args.compilation_command1)
    setting2, _, _ = parse_compilation_setting_from_string(args.compilation_command2)

    cases = generate_and_test(
        setting1,
        setting2,
        __arg_to_testing_mode(args.testing_mode),
        args.number_candidates,
        args.jobs,
    )
    reductions = {}
    if args.reduce:
        for case in cases:
            # XXX: how to a select marker?
            target_marker = (
                case.markers_only_eliminated_by_setting1
                + case.markers_only_eliminated_by_setting2
            )[0]
            reduction = reduce_case(case, target_marker, args.jobs)
            assert reduction
            reductions[case] = reduction

    write_cases_to_directory(cases, reductions, args.output_directory)
