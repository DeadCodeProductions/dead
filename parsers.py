import argparse
from typing import Any, Sequence


def config_parser(
    expected_entries: Sequence[tuple[Any, ...]]
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    for _, path, desc in expected_entries:
        parser.add_argument("--" + ".".join(path), help=desc)
    parser.add_argument("--config", type=str, help="Path to config.json")

    parser.add_argument(
        "-ll",
        "--log-level",
        type=str,
        choices=("debug", "info", "warning", "error", "critical"),
        help="Log level",
    )

    parser.add_argument(
        "--cores", help="Amount of build cores to use. Defaults to all.", type=int
    )

    return parser


def builder_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "-c", "--compiler", help="Which compiler project to use", nargs=1, type=str
    )

    parser.add_argument(
        "-r",
        "--revision",
        help="Which revision of the compiler project to use. Use 'trunk' to use the latest commit",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "--build-releases", help="Build release versions", action="store_true"
    )

    parser.add_argument(
        "--add-patches",
        help="Which patches to apply in addition to the ones found in patchDB",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "-f",
        "--force",
        help="Force build even if patch combo is known to be bad",
        action="store_true",
    )
    return parser


def patcher_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    mut_excl_group = parser.add_mutually_exclusive_group(required=True)

    # ====================
    mut_excl_group.add_argument(
        "--find-range",
        help="Try to find the range where a patch is required",
        action="store_true",
    )

    parser.add_argument(
        "-c",
        "--compiler",
        help="Which compiler project to use",
        nargs=1,
        type=str,
        required=True,
    )

    parser.add_argument(
        "-pr",
        "--patchable-revision",
        help="Which revision is patchable with the commit specified in --patches",
        type=str,
    )

    parser.add_argument(
        "--patches",
        nargs="*",
        help="Which patch(es) to apply.",
        type=str,
    )
    # ====================
    mut_excl_group.add_argument(
        "--find-introducer",
        help="Try to find the introducer commit of a build failure.",
        action="store_true",
    )

    parser.add_argument(
        "-br", "--broken-revision", help="Which revision is borken", type=str
    )
    # ====================

    return parser


def generator_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "-a", "--amount", help="Amount of cases to generate.", type=int, default=0
    )

    parser.add_argument(
        "--interesting",
        help="If the generated case should be an interesting one.",
        action=argparse.BooleanOptionalAction,
        default=True,
    )

    parser.add_argument(
        "-t",
        "--targets",
        help="Project name and revision of compiler to use.",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "-tdol",
        "--targets-default-opt-levels",
        help="Default optimization levels for the target to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "-ac",
        "--additional-compilers",
        help="Additional compiler to compare the target against.",
        nargs="*",
        type=str,
    )

    parser.add_argument(
        "-acdol",
        "--additional-compilers-default-opt-levels",
        help="Default optimization levels for the additional compilers to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument("-s", "--scenario", help="Which scenario to work on.", type=str)

    parser.add_argument(
        "-p",
        "--parallel",
        help="Run the search in parallel for --parallel processes. Works only in combination with --interesting.",
        type=int,
    )

    parser.add_argument(
        "-d", "--output-directory", help="Where the cases should be saved to.", type=str
    )

    return parser


def checker_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    group = parser.add_mutually_exclusive_group()

    parser.add_argument(
        "-f", "--file", help="Which file to work on.", type=str, required=True
    )

    parser.add_argument("-m", "--marker", help="Marker to check for.", type=str)

    group.add_argument(
        "-s",
        "--scenario",
        help="Which scenario to use as testing replacement.",
        type=str,
    )

    group.add_argument(
        "-is",
        "--interesting-settings",
        help="Which interesting settings to use.",
        type=str,
    )

    parser.add_argument(
        "-bad",
        "--bad-settings",
        help="Settings which are supposed to *not* eliminate the marker",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "-bsdol",
        "--bad-settings-default-opt-levels",
        help="Default optimization levels for the bad-settings to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "-good",
        "--good-settings",
        help="Settings which are supposed to eliminate the marker",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "-gsdol",
        "--good-settings-default-opt-levels",
        help="Default optimization levels for the good-settings to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "-cr",
        "--check-reduced",
        help="Instead of checking the original file, check the latest reduced code.",
        action="store_true",
    )

    parser.add_argument(
        "--check-pp",
        help="Run the preprocessed version through the checker.",
        action="store_true",
    )

    parser.add_argument(
        "--dont-preprocess",
        help="Force no preprocessing",
        action="store_true",
    )

    return parser


def reducer_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-f", "--file", help="Which file to work on.", type=str)

    parser.add_argument(
        "-g",
        "--generate",
        help="Whether or not to generate and reduce cases",
        action="store_true",
    )

    parser.add_argument(
        "--work-through",
        help="Look at all cases found in directory specified in --output-directory and reduce them when they are not.",
        action="store_true",
    )

    parser.add_argument("-s", "--scenario", help="Which scenario to work on.", type=str)

    parser.add_argument(
        "-a", "--amount", help="How many cases to find and reduce.", type=int, default=0
    )

    parser.add_argument(
        "-d", "--output-directory", help="Where the cases should be saved to.", type=str
    )

    parser.add_argument(
        "-t",
        "--targets",
        help="Project name and revision of compiler to use.",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "-tdol",
        "--targets-default-opt-levels",
        help="Default optimization levels for the target to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "-ac",
        "--additional-compilers",
        help="Additional compiler to compare the target against.",
        nargs="*",
        type=str,
    )

    parser.add_argument(
        "-acdol",
        "--additional-compilers-default-opt-levels",
        help="Default optimization levels for the additional compilers to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "--force",
        help="Force another reduction even if one already exists.",
        action="store_true",
    )

    parser.add_argument(
        "-rr",
        "--re-reduce",
        help="Re-reduce the last reduce code",
        action="store_true",
    )

    return parser


def bisector_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-f", "--file", help="Which file to work on.", type=str)

    parser.add_argument(
        "-d", "--output-directory", help="Where the cases should be saved to.", type=str
    )

    parser.add_argument(
        "-a", "--amount", help="How many cases to find and reduce.", type=int, default=0
    )

    parser.add_argument(
        "-g",
        "--generate",
        help="Whether or not to generate, reduce and bisect cases",
        action="store_true",
    )

    parser.add_argument("-s", "--scenario", help="Which scenario to work on.", type=str)

    parser.add_argument(
        "-t",
        "--targets",
        help="Project name and revision of compiler to use.",
        nargs="+",
        type=str,
    )

    parser.add_argument(
        "-tdol",
        "--targets-default-opt-levels",
        help="Default optimization levels for the target to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "-ac",
        "--additional-compilers",
        help="Additional compiler to compare the target against.",
        nargs="*",
        type=str,
    )

    parser.add_argument(
        "-acdol",
        "--additional-compilers-default-opt-levels",
        help="Default optimization levels for the additional compilers to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    parser.add_argument(
        "--work-through",
        help="Look at all cases found in directory specified in --output-directory and bisect them when they are not.",
        action="store_true",
    )

    parser.add_argument(
        "--force",
        help="Force another bisection even if they already exist",
        action="store_true",
    )

    parser.add_argument(
        "--reducer",
        help="If the generated case should be reduced or not.",
        action=argparse.BooleanOptionalAction,
        default=True,
    )

    return parser


def debugtool_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-f", "--file", help="Which file to work on.", type=str)

    parser.add_argument(
        "-crb",
        "--clean-reduced-bisections",
        help="Delete all files related to reduction and bisection",
        action="store_true",
    )

    parser.add_argument(
        "--reduced",
        help="Work on reduced files. (where applicable)",
        action="store_true",
    )

    parser.add_argument(
        "--preprocessed",
        help="Work on preprocessed files. (where applicable)",
        action="store_true",
    )

    parser.add_argument(
        "--asm",
        help="Get assembly for a case asmgood.s and asmbad.s",
        action="store_true",
    )

    parser.add_argument(
        "--static",
        help="Get code where functions and global variables are static in static.c",
        action="store_true",
    )

    # TODO: help information for --viz
    parser.add_argument("--viz", help="", action="store_true")

    parser.add_argument("--preprocess-code", help="", action="store_true")

    parser.add_argument(
        "-di", "--diagnose", help="Run general tests.", action="store_true"
    )

    parser.add_argument(
        "--empty-marker-code",
        help="Get empty marker body code in empty_body.c",
        action="store_true",
    )

    return parser


def main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)

    subparser = parser.add_subparsers(title="sub", dest="sub")
    run_parser = subparser.add_parser("run", help="Let DEAD search for cases.")

    run_parser.add_argument(
        "-d", "--output-directory", help="Where the cases should be saved to.", type=str
    )

    run_parser.add_argument(
        "-a", "--amount", help="How many cases to find and reduce.", type=int, default=0
    )

    run_parser.add_argument(
        "-s", "--scenario", help="Which scenario to work on.", type=str
    )
    run_parser.add_argument(
        "-t",
        "--targets",
        help="Project name and revision of compiler to use.",
        nargs="+",
        type=str,
    )

    run_parser.add_argument(
        "-tdol",
        "--targets-default-opt-levels",
        help="Default optimization levels for the target to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    run_parser.add_argument(
        "-ac",
        "--additional-compilers",
        help="Additional compiler to compare the target against.",
        nargs="*",
        type=str,
    )

    run_parser.add_argument(
        "-acdol",
        "--additional-compilers-default-opt-levels",
        help="Default optimization levels for the additional compilers to be checked against.",
        nargs="+",
        default=[],
        type=str,
    )

    run_parser.add_argument(
        "--reducer",
        help="If the generated case should be reduced or not.",
        action=argparse.BooleanOptionalAction,
        default=False,
    )

    run_parser.add_argument(
        "--bisector",
        help="If the generated case should be bisected or not.",
        action=argparse.BooleanOptionalAction,
        default=True,
    )

    run_parser.add_argument(
        "-pg",
        "--parallel-generation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run the case generation part in parallel. This will disable timing for the generation part.",
    )

    run_parser.add_argument(
        "--update-trunk-after-X-hours",
        help="Enable automatic updating target compilers which are at the current trunk after X hours of running.",
        metavar="X",
        type=int,
    )

    absorb_parser = subparser.add_parser(
        "absorb", help="Read cases outside of the database into the database."
    )

    absorb_parser.add_argument(
        "absorb_object",
        metavar="DIR|FILE",
        help="Directory or file to read .tar cases from into the database.",
    )

    report_parser = subparser.add_parser("report", help="Generate a report for a case.")

    report_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Generate a bug report for the given id.",
    )

    report_parser.add_argument(
        "--pull",
        help="Pull the repo to check against upsteam.",
        action=argparse.BooleanOptionalAction,
        default=True,
    )

    tofile_parser = subparser.add_parser(
        "tofile",
        help="Save a case from the database into a file. This is a LOSSY operation.",
    )

    tofile_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Case to get a .tar from ",
    )

    rereduce_parser = subparser.add_parser(
        "rereduce",
        help="Reduce code from outside the database w.r.t. a specified case.",
    )

    rereduce_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Case to work with.",
    )

    rereduce_parser.add_argument(
        "code_path",
        metavar="CODE_PATH",
        type=str,
        help="Path to code to rereduce",
    )

    diagnose_parser = subparser.add_parser(
        "diagnose", help="Run tests on a specified case and print a summary."
    )

    diagnose_parser.add_argument(
        "-ci",
        "--case-id",
        metavar="CASE_ID",
        type=int,
        help="Case to work with.",
    )

    diagnose_parser.add_argument(
        "--file",
        metavar="PATH",
        type=str,
        help="Path to case to work with",
    )

    checkreduced_parser = subparser.add_parser(
        "checkreduced",
        help="Check if code outside of the database passes the checks of a specified case.",
    )

    checkreduced_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Case to work with.",
    )

    checkreduced_parser.add_argument(
        "code_path",
        metavar="CODE_PATH",
        type=str,
        help="Path to code to checkreduced",
    )

    cache_parser = subparser.add_parser("cache", help="Perform actions on the cache.")

    cache_parser.add_argument(
        "what",
        choices=("clean", "stats"),
        type=str,
        help="What you want to do with the cache. Clean will search and remove all unfinished cache entries. `stats` will print some statistics about the cache.",
    )

    asm_parser = subparser.add_parser(
        "asm",
        help="Save assembly outputs (-S) for the good and bad settings for each code found in a case.",
    )
    asm_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Case to work with.",
    )

    set_parser = subparser.add_parser("set", help="Set values of a case.")
    get_parser = subparser.add_parser(
        "get", help="Print values of a case to the command line."
    )

    get_parser.add_argument(
        "what",
        choices=("link", "fixed", "mcode", "rcode", "ocode", "bisection"),
        type=str,
        help="What you want to get. `ocode` is the original code. `rcode` is the reduced code. `mcode` is the massaged code. fixed is the commit the commit the case was `fixed` with and `link` the link to the bug report.",
    )

    get_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Case from which to get what you chose",
    )

    set_parser.add_argument(
        "what",
        choices=("link", "fixed", "mcode", "rcode", "ocode", "bisection"),
        type=str,
        help="What you want to set. `ocode` is the original code. `rcode` is the reduced code. `mcode` is the massaged code. `fixed` is the commit the commit the case was fixed` with and `link` the link to the bug report. `ocode`, `rcode` and `mcode` expect files, `link`, `fixed` and `bisection` strings.",
    )

    set_parser.add_argument(
        "case_id",
        metavar="CASE_ID",
        type=int,
        help="Case to set the value of",
    )

    set_parser.add_argument(
        "var",
        metavar="VAR",
        type=str,
        help="What to set the chosen value to. Expected input may change based on what you are setting.",
    )

    build_parser = subparser.add_parser(
        "build", help="Build a specific compiler version."
    )

    build_parser.add_argument(
        "project",
        choices=("gcc", "llvm", "clang"),
        type=str,
        help="Which compiler to build",
    )
    build_parser.add_argument(
        "rev", nargs="+", type=str, help="Which revision(s)/commit(s) to build"
    )
    build_parser.add_argument(
        "--force",
        action=argparse.BooleanOptionalAction,
        help="Whether or not to force another build.",
    )

    build_parser.add_argument(
        "--add-patches",
        help="Which patches to apply in addition to the ones found in patchDB",
        nargs="+",
        type=str,
    )

    reduce_parser = subparser.add_parser(
        "reduce", help="Reduce the initially found code of a case."
    )

    reduce_parser.add_argument(
        "case_id", nargs="+", type=int, help="Which case to reduce"
    )
    reduce_parser.add_argument(
        "--force",
        action=argparse.BooleanOptionalAction,
        help="Whether or not to force another reduction. This will override the old reduced code.",
    )

    bisect_parser = subparser.add_parser(
        "bisect", help="Find the bisection commit for a specified case."
    )

    bisect_parser.add_argument(
        "case_id", nargs="+", type=int, help="Which case to bisect"
    )
    bisect_parser.add_argument(
        "--force",
        action=argparse.BooleanOptionalAction,
        help="Whether or not to force another bisection. This will override the old bisection.",
    )

    edit_parser = subparser.add_parser("edit", help="Open DEADs config in $EDITOR.")

    unreported_parser = subparser.add_parser(
        "unreported", help="List cases which have not been reported or fixed."
    )

    unreported_parser.add_argument(
        "--id-only",
        action="store_true",
        help="Print only the case ids. Useful for scripting.",
    )

    unrep_mut_ex_red = unreported_parser.add_mutually_exclusive_group()
    unrep_mut_ex_red.add_argument(
        "--not-reduced",
        action="store_true",
        help="If the listed cases should NOT be reduced",
    )
    unrep_mut_ex_red.add_argument(
        "--reduced", action="store_true", help="If the listed cases should be reduced"
    )

    unrep_mut_ex = unreported_parser.add_mutually_exclusive_group()
    # I'd call the options --gcc, --clang etc. but
    # running ./main.py unreported --gcc will complain about ambiguity
    # wrt to --gcc.repo etc. from the config.
    # However when running ./main.py unreported --gcc.repo it is an unknown option
    # as these flags are only parsed directly after ./main.py.
    unrep_mut_ex.add_argument(
        "--gcc-only", action="store_true", help="Print only GCC related bisections."
    )
    unrep_mut_ex.add_argument(
        "--llvm-only",
        action="store_true",
        help="Print only LLVM related bisections. Same as --clang-only.",
    )
    unrep_mut_ex.add_argument(
        "--clang-only",
        action="store_true",
        help="Print only clang related bisections. Same as --llvm-only.",
    )

    unreported_parser.add_argument(
        "--OX-only",
        type=str,
        metavar="OPT_LEVEL",
        help="Print only bisections with OPT_LEVEL as bad setting.",
    )

    unreported_parser.add_argument(
        "--good-version",
        type=str,
        metavar="REV",
        help="Print only bisections which have REV as a good compiler matching the opt level of the bad compiler.",
    )

    reported_parser = subparser.add_parser(
        "reported", help="List cases which have been reported."
    )

    reported_parser.add_argument(
        "--id-only",
        action="store_true",
        help="Print only the case ids. Useful for scripting.",
    )

    rep_mut_ex = reported_parser.add_mutually_exclusive_group()
    rep_mut_ex.add_argument(
        "--gcc-only", action="store_true", help="Print only GCC related bisections."
    )
    rep_mut_ex.add_argument(
        "--llvm-only",
        action="store_true",
        help="Print only LLVM related bisections. Same as --clang-only.",
    )
    rep_mut_ex.add_argument(
        "--clang-only",
        action="store_true",
        help="Print only clang related bisections. Same as --llvm-only.",
    )

    reported_parser.add_argument(
        "--good-settings",
        action="store_true",
        help="Print the good settings of the cases.",
    )

    findby_parser = subparser.add_parser(
        "findby", help="Find case IDs given only a part of a case."
    )
    findby_parser.add_argument(
        "what",
        type=str,
        choices=("link", "case", "code", "fixed"),
    )

    findby_parser.add_argument(
        "var",
        type=str,
        metavar="VAR",
        help="Is a string, when choosing link or fixed, is a path when choosing case or code.",
    )

    init_parser = subparser.add_parser("init", help="Initialize DEAD.")

    return parser
