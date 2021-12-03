import argparse
import os
from typing import Any, Sequence


def config_parser(expected_entries: Sequence[tuple[Any, ...]]):
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


def builder_parser():
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


def patcher_parser():
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
        help="Which revision is patchable with the commit specified in --patch",
        type=str,
    )

    parser.add_argument(
        "--patch",
        help="Which revision is patchable with the commit specified in --patch",
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


def generator_parser():
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


def checker_parser():
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


def reducer_parser():
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


def bisector_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument("-f", "--file", help="Which file to work on.", type=str)

    parser.add_argument(
        "-d", "--output-directory", help="Where the cases should be saved to.", type=str
    )

    parser.add_argument(
        "-a", "--amount", help="How many cases to find and reduce.", type=str, default=0
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


def debugtool_parser():
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
