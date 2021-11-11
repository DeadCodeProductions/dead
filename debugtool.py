#!/usr/bin/env python3

"""
A tool to help with debugging.
Grows with arising needs.
"""

import copy
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
        case.reduced_code = []
        case.bisections = []
        case.to_file(file)
    elif args.asm:
        code = case.code
        if args.reduced:
            code = case.reduced_code[0]

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
        if args.reduced:
            code = case.reduced_code[0]

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
            flags,
        )
        checker.annotate_program_with_static(
            config.static_annotator, "static.c", include_paths
        )
        print("Created static.c")
    elif args.viz:

        def _res(case, rev):
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
            search_bis = isinstance(rev_bis, str)
            bis_ancestor_found = False
            for i, rev in enumerate(revs):
                i += 1
                res = _res(case, rev)
                insert_bis = False
                if search_bis and not bis_ancestor_found:
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
            if search_bis and not bis_ancestor_found:
                if bis_ancestor_found := repo.is_ancestor(rev_CA, rev_bis):
                    print(f" | bisect: {rev_bis}")
                    print(" |")
                    return True
            return bis_ancestor_found

        if case.bisections:
            rev_bis = case.bisections[0]
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
        cpy.code = cpy.reduced_code[0]
        res_bs = "bad" if chkr.is_interesting(cpy, preprocess=False) else "good"
        # TODO: Fix this
        print(
            "NOTE: This graphic assumes the 'Start' commit to be from somewhere in trunk"
        )
        print(f"Start:{res_bs}")
        print(" |")

        if case.bad_setting.compiler_config.name == "clang":
            first_CA = repo.get_best_common_ancestor(rev_main, "llvmorg-13.0.0")
            if repo.is_ancestor(first_CA, rev_bis):
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
            first_CA = repo.get_best_common_ancestor(rev_main, "llvmorg-11.2.0")
            if repo.is_ancestor(first_CA, rev_bis):
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

            if _print_version(
                cpy, ["releases/gcc-8.4.0", "releases/gcc-8.5.0"], rev_bis
            ):
                rev_bis = None

    elif args.preprocess:
        with open("code_pp.c", "w") as f:
            code_pp = preprocessing.preprocess_csmith_code(
                case.code, utils.get_marker_prefix(case.marker), case.bad_setting, bldr
            )
            f.write(code_pp)
        print("Written preprocessed code to code_pp.c")
