#!/usr/bin/env python3

"""
A tool to help with debugging.
Grows with arising needs.
"""

import copy
import logging
import tempfile
from pathlib import Path
from typing import Optional

import bisector
import builder
import checker
import generator
import parsers
import patchdatabase
import preprocessing
import reducer
import repository
import utils


def _ok_fail(b: bool) -> str:
    if b:
        return "OK"
    else:
        return "FAIL"


def sanitize_values(
    config: utils.NestedNamespace, case: utils.Case, prefix: str, chkr: checker.Checker
) -> None:
    empty_body_code = chkr._emtpy_marker_code_str(case)
    with tempfile.NamedTemporaryFile(suffix=".c") as tf:
        with open(tf.name, "w") as f:
            f.write(empty_body_code)
            res_comp_warnings = checker.check_compiler_warnings(
                config.gcc.sane_version,
                config.llvm.sane_version,
                Path(tf.name),
                case.bad_setting.get_flag_str(),
                10,
            )
            print(
                ("{:.<" f"{width}}}").format(prefix + "Sanity: compiler warnings"),
                _ok_fail(res_comp_warnings),
            )
            res_use_ub_san = checker.use_ub_sanitizers(
                config.llvm.sane_version,
                Path(tf.name),
                case.bad_setting.get_flag_str(),
                10,
                10,
            )
            print(
                ("{:.<" f"{width}}}").format(prefix + "Sanity: undefined behaviour"),
                _ok_fail(res_use_ub_san),
            )
            res_ccomp = checker.verify_with_ccomp(
                config.ccomp,
                Path(tf.name),
                case.bad_setting.get_flag_str(),
                10,
            )
            print(
                ("{:.<" f"{width}}}").format(prefix + "Sanity: ccomp"),
                _ok_fail(res_ccomp),
            )


def viz(case: utils.Case) -> None:
    def _res(case: utils.Case, rev: str) -> str:
        lerev = repo.rev_to_commit(rev)
        case.bad_setting.rev = lerev
        if chkr.is_interesting(case, preprocess=False):
            return "bad"
        else:
            return "good"

    def _print_version(
        case: utils.Case, revs: list[str], rev_bis: Optional[str]
    ) -> bool:
        revs.reverse()
        bis_ancestor_found = False
        for i, rev in enumerate(revs):
            i += 1
            res = _res(case, rev)
            insert_bis = False
            if isinstance(rev_bis, str) and not bis_ancestor_found:
                if bis_ancestor_found := repo.is_ancestor(rev, rev_bis):
                    insert_bis = True

            spaces = (len(revs) - i) * " "
            if insert_bis:
                print(" |" + spaces + " " + f" {rev}: {res}")
                print(" |" + spaces + " / bisect: {rev_bis}")
                print(" |" + spaces + "/")
            else:
                print(" |" + spaces + f" {rev}: {res}")
                print(" |" + spaces + "/")

        rev_CA = repo.get_best_common_ancestor(rev_main, revs[0])
        res_CA = _res(cpy, rev_CA)
        print(f"CA_{revs[0].split('-')[-1]}: {res_CA}")
        print(" |")
        if isinstance(rev_bis, str) and not bis_ancestor_found:
            if bis_ancestor_found := repo.is_ancestor(rev_CA, rev_bis):
                print(f" | bisect: {rev_bis}")
                print(" |")
                return True
        return bis_ancestor_found

    if case.bisection:
        rev_bis: Optional[str] = case.bisection
        print(f"Bisection commit {rev_bis}")
    else:
        rev_bis = None

    repo = repository.Repo(
        case.bad_setting.compiler_config.repo,
        case.bad_setting.compiler_config.main_branch,
    )
    rev_main = repo.rev_to_commit(case.bad_setting.compiler_config.main_branch)
    # Test bad_setting
    cpy = copy.deepcopy(case)
    if cpy.reduced_code:
        cpy.code = cpy.reduced_code
    res_bs = "bad" if chkr.is_interesting(cpy, preprocess=False) else "good"
    # TODO: Fix this
    print("NOTE: This graphic assumes the 'Start' commit to be from somewhere in trunk")
    print(f"Start:{res_bs}")
    print(" |")

    if case.bad_setting.compiler_config.name == "clang":
        first_CA = repo.get_best_common_ancestor(rev_main, "llvmorg-13.0.0")
        if rev_bis and repo.is_ancestor(first_CA, rev_bis):
            print(f" | bisect: {rev_bis}")
            print(" |")
            rev_bis = None

        if _print_version(cpy, ["llvmorg-13.0.0"], rev_bis):
            rev_bis = None
        if _print_version(cpy, ["llvmorg-12.0.0", "llvmorg-12.0.1"], rev_bis):
            rev_bis = None
        if _print_version(
            cpy, ["llvmorg-11.0.0", "llvmorg-11.0.1", "llvmorg-11.1.0"], rev_bis
        ):
            rev_bis = None
        if _print_version(cpy, ["llvmorg-10.0.0", "llvmorg-10.0.1"], rev_bis):
            rev_bis = None
    else:
        first_CA = repo.get_best_common_ancestor(rev_main, "releases/gcc-11.2.0")
        if rev_bis and repo.is_ancestor(first_CA, rev_bis):
            print(f" | bisect: {rev_bis}")
            print(" |")
            rev_bis = None

        if _print_version(
            cpy,
            ["releases/gcc-11.1.0", "releases/gcc-11.2.0"],
            rev_bis,
        ):
            rev_bis = None

        if _print_version(
            cpy,
            ["releases/gcc-10.1.0", "releases/gcc-10.2.0", "releases/gcc-10.3.0"],
            rev_bis,
        ):
            rev_bis = None

        if _print_version(
            cpy,
            [
                "releases/gcc-9.1.0",
                "releases/gcc-9.2.0",
                "releases/gcc-9.3.0",
                "releases/gcc-9.4.0",
            ],
            rev_bis,
        ):
            rev_bis = None

        if _print_version(cpy, ["releases/gcc-8.4.0", "releases/gcc-8.5.0"], rev_bis):
            rev_bis = None


if __name__ == "__main__":
    config, args = utils.get_config_and_parser(parsers.debugtool_parser())

    patchdb = patchdatabase.PatchDB(config.patchdb)
    bldr = builder.Builder(config, patchdb, args.cores)
    chkr = checker.Checker(config, bldr)
    gnrtr = generator.CSmithCaseGenerator(config, patchdb)
    rdcr = reducer.Reducer(config, bldr)
    bsctr = bisector.Bisector(config, bldr, chkr)

    file = Path(args.file)

    case = utils.Case.from_file(config, file)

    if args.clean_reduced_bisections:
        case.reduced_code = None
        case.bisection = None
        case.to_file(file)
    elif args.asm:
        code = case.code
        if args.reduced and case.reduced_code:
            code = case.reduced_code
        else:
            print("Found no static code. Working with normal code...")

        with open("asmbad.s", "w") as f:
            f.write("//====== Bad ASM =====\n")
            f.write(f"// {case.marker}\n")
            f.write(f"// {case.bad_setting.rev}\n")
            f.write(builder.get_asm_str(code, case.bad_setting, bldr))
        with open("asmgood.s", "w") as f:
            f.write("//====== Good ASM =====\n")
            f.write(f"// {case.marker}\n")
            f.write(f"// {case.good_settings[0].rev}\n")
            f.write(builder.get_asm_str(code, case.good_settings[0], bldr))
        print("Created files asmgood.s and asmbad.s")
    elif args.static:
        code = case.code
        if args.reduced and case.reduced_code:
            code = case.reduced_code
        else:
            print("Found no static code. Working with normal code...")

        with open("static.c", "w") as f:
            f.write(code)
        flags = (
            " ".join(case.bad_setting.additional_flags)
            if case.bad_setting.additional_flags
            else None
        )
        include_paths = utils.find_include_paths(
            config.llvm.sane_version,
            "static.c",
            flags if flags else "",
        )
        checker.annotate_program_with_static(
            config.static_annotator, Path("static.c"), include_paths
        )
        print("Created static.c")
    elif args.viz:
        viz(case)

    elif args.preprocess_code:
        with open("code_pp.c", "w") as f:
            code_pp = preprocessing.preprocess_csmith_code(
                case.code, utils.get_marker_prefix(case.marker), case.bad_setting, bldr
            )
            if not code_pp:
                print("Could not preprocess code.")
                exit(1)

            f.write(code_pp)
        print("Written preprocessed code to code_pp.c")

    elif args.empty_marker_code:
        cpy = copy.deepcopy(case)
        if args.preprocessed:
            tmp = preprocessing.preprocess_csmith_code(
                case.code, utils.get_marker_prefix(case.marker), case.bad_setting, bldr
            )
            if tmp:
                cpy.code = tmp
            else:
                logging.warn("Could not preprocess code. Continuing anyways...")

        if args.reduced and cpy.reduced_code:
            cpy.code = cpy.reduced_code

        empty_marker_code = chkr._emtpy_marker_code_str(cpy)
        with open("empty_body.c", "w") as f:
            f.write(empty_marker_code)
        print("Written empty marker body code in empty_body.c")

    elif args.diagnose:
        repo = repository.Repo(
            case.bad_setting.compiler_config.repo,
            case.bad_setting.compiler_config.main_branch,
        )
        width = 50
        print(("{:=^" f"{width}}}").format(" Values "))
        # print(("{:.<"f"{width}}}").format(""), )
        print(("{:.<" f"{width}}}").format("Marker"), case.marker)
        print(("{:.<" f"{width}}}").format("Code lenght"), len(case.code))
        print(("{:.<" f"{width}}}").format("Bad Setting"), case.bad_setting)
        same_opt = [
            gs
            for gs in case.good_settings
            if gs.opt_level == case.bad_setting.opt_level
        ]
        print(
            ("{:.<" f"{width}}}").format("Newest Good Setting"),
            utils.get_latest_compiler_setting_from_list(repo, same_opt),
        )
        print(
            ("{:.<" f"{width}}}").format("Check marker"),
            _ok_fail(chkr.is_interesting_wrt_marker(case)),
        )
        print(
            ("{:.<" f"{width}}}").format("Check CCC"),
            _ok_fail(chkr.is_interesting_wrt_ccc(case)),
        )
        print(
            ("{:.<" f"{width}}}").format("Check static. annotated"),
            _ok_fail(chkr.is_interesting_with_static_globals(case)),
        )
        res_empty = chkr.is_interesting_with_empty_marker_bodies(case)
        print(("{:.<" f"{width}}}").format("Check empty bodies"), _ok_fail(res_empty))
        if not res_empty:
            sanitize_values(config, case, "", chkr)

        cpy = copy.deepcopy(case)
        tmp = preprocessing.preprocess_csmith_code(
            case.code, utils.get_marker_prefix(case.marker), case.bad_setting, bldr
        )
        if tmp:
            cpy.code = tmp
        print(
            ("{:.<" f"{width}}}").format("PP: Check marker"),
            _ok_fail(chkr.is_interesting_wrt_marker(cpy)),
        )
        print(
            ("{:.<" f"{width}}}").format("PP: Check CCC"),
            _ok_fail(chkr.is_interesting_wrt_ccc(cpy)),
        )
        print(
            ("{:.<" f"{width}}}").format("PP: Check static. annotated"),
            _ok_fail(chkr.is_interesting_with_static_globals(cpy)),
        )
        res_empty = chkr.is_interesting_with_empty_marker_bodies(cpy)
        print(
            ("{:.<" f"{width}}}").format("PP: Check empty bodies"), _ok_fail(res_empty)
        )
        if not res_empty:
            sanitize_values(config, cpy, "PP: ", chkr)

        if case.reduced_code:
            cpy = copy.deepcopy(case)
            cpy.code = case.reduced_code
            print(
                ("{:.<" f"{width}}}").format("Reduced: Check marker"),
                _ok_fail(chkr.is_interesting_wrt_marker(cpy)),
            )
            print(
                ("{:.<" f"{width}}}").format("Reduced: Check CCC"),
                _ok_fail(chkr.is_interesting_wrt_ccc(cpy)),
            )
            print(
                ("{:.<" f"{width}}}").format("Reduced: Check static. annotated"),
                _ok_fail(chkr.is_interesting_with_static_globals(cpy)),
            )
            res_empty = chkr.is_interesting_with_empty_marker_bodies(cpy)
            print(
                ("{:.<" f"{width}}}").format("Reduced: Check empty bodies"),
                _ok_fail(res_empty),
            )
            if not res_empty:
                sanitize_values(config, cpy, "Reduced: ", chkr)

        if case.bisection:
            print(("{:.<" f"{width}}}").format("Last Bisection"), case.bisection)
            prev_rev = repo.rev_to_commit(case.bisection + "~")
            print(("{:.<" f"{width}}}").format("Bisection prev commit"), prev_rev)
            cpy = copy.deepcopy(case)
            if cpy.reduced_code:
                cpy.code = cpy.reduced_code
            bis_res = chkr.is_interesting(cpy, preprocess=False)
            cpy.bad_setting.rev = prev_rev
            bis_prev_res = chkr.is_interesting(cpy, preprocess=False)
            print(
                ("{:.<" f"{width}}}").format("Bisection test"),
                _ok_fail(bis_res and not bis_prev_res),
            )
        if case.reduced_code:
            print(("{:=^" f"{width}}}").format(" Last Reduced Code "))
            print(case.reduced_code)
