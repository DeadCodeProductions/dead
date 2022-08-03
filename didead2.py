#!/usr/bin/env python3

import pickle
import logging
import copy
import tempfile
from typing import Optional
from concurrent.futures import ProcessPoolExecutor, as_completed, Future, wait
from pathlib import Path

import ccbuilder
from dead_instrumenter.instrumenter import instrument_program
from diopter.compiler import CompilationSetting, CompilerExe, OptLevel, ClangTool
from diopter.generator import CSmithGenerator
from diopter.reducer import Reducer
from diopter.reduction_checks import make_interestingness_check
from diopter.bisector import Bisector

from dead.checker import Checker, find_alive_markers

from tqdm import tqdm  # type: ignore


class DeadGenerator(CSmithGenerator):
    def generate_code(self) -> str:
        csmith_code = super().generate_code()
        with tempfile.NamedTemporaryFile(suffix=".c") as tfile:
            with open(tfile.name, "w") as f:
                f.write(csmith_code)
            instrument_program(Path(tfile.name), flags=["-I/usr/include/csmith-2.3.0/"])
            with open(tfile.name, "r") as f:
                return f.read()


def create_compilation_settings(
    bldr: ccbuilder.Builder,
    project: ccbuilder.CompilerProject,
    revs: list[ccbuilder.Revision],
    opt_levels: list[OptLevel],
    flags: list[str],
    include_paths: list[str],
    system_include_paths: list[str],
    repo: ccbuilder.Repo
    # DiopterContext should have a dict[CompilerProject,Repo]
) -> list[CompilationSetting]:

    res: list[CompilationSetting] = []
    for rev in revs:
        commit = repo.rev_to_commit(rev)
        for opt in opt_levels:
            res.append(
                CompilationSetting(
                    compiler=CompilerExe(
                        project, bldr.build(project, rev, True), commit
                    ),
                    opt_level=opt,
                    include_paths=copy.deepcopy(include_paths),
                    system_include_paths=copy.deepcopy(system_include_paths),
                    flags=copy.deepcopy(flags),
                )
            )
    return res


def check_interestingness(
    checker: Checker,
    candidate: str,
    target: CompilationSetting,
    attackers: list[CompilationSetting],
) -> Optional[tuple[str, list[tuple[str, list[CompilationSetting]]]]]:
    markers = checker.interesting_markers(candidate, target, attackers)
    if not markers:
        return None
    return candidate, markers


def reduction_check(
    code: str,
    clang: str,
    gcc: str,
    ccc: str,
    marker: str,
    bad_setting: str,
    good_setting: str,
) -> bool:
    checker = Checker(
        CompilerExe.from_str(clang),
        CompilerExe.from_str(gcc),
        ClangTool.from_str(ccc),
        "ccomp",
    )
    return checker.is_interesting_marker(
        code,
        marker,
        CompilationSetting.from_str(bad_setting),
        [CompilationSetting.from_str(good_setting)],
    )


def bisection_test(
    new_commit: ccbuilder.Commit,
    codemarkersetting: tuple[str, str, CompilationSetting],
    bldr: ccbuilder.Builder,
) -> Optional[bool]:
    try:
        code, marker, setting = codemarkersetting
        setting = copy.deepcopy(setting)
        cproject = setting.compiler.project
        setting.compiler = CompilerExe(
            cproject, bldr.build(cproject, new_commit, True), new_commit
        )
        return marker in find_alive_markers(code, setting, "DCEMarker")

    except Exception as e:
        logging.warning(f"Test failed with: '{e}'. Continuing...")
        return None


if __name__ == "__main__":
    # num_lvl = getattr(logging, "DEBUG")
    # logging.basicConfig(level=num_lvl)

    # All the default paths and standard objects, e.g., the repos,
    # should be part of DiopterContext

    llvm_repo = ccbuilder.get_repo(
        ccbuilder.CompilerProject.LLVM,
        Path("/home/theo/.cache/ccbuilder-repos/llvm-project/"),
    )

    gcc_repo = ccbuilder.get_repo(
        ccbuilder.CompilerProject.GCC,
        Path("/home/theo/.cache/ccbuilder-repos/gcc/"),
    )
    bldr = ccbuilder.Builder(Path("/zdata/compiler_cache"), gcc_repo, llvm_repo)

    attackers = create_compilation_settings(
        bldr,
        project=ccbuilder.CompilerProject.LLVM,
        revs=ccbuilder.MajorCompilerReleases[ccbuilder.CompilerProject.LLVM][:4],
        opt_levels=[OptLevel.O3, OptLevel.O2],
        flags=[],
        include_paths=[],
        system_include_paths=["/usr/include/csmith-2.3.0/"],
        repo=llvm_repo,
    )

    target = create_compilation_settings(
        bldr,
        project=ccbuilder.CompilerProject.LLVM,
        revs=["trunk"],
        opt_levels=[OptLevel.O3],
        flags=[],
        include_paths=[],
        system_include_paths=["/usr/include/csmith-2.3.0/"],
        repo=llvm_repo,
    )[0]

    generator = DeadGenerator()

    llvm = CompilerExe(ccbuilder.CompilerProject.LLVM, Path("clang"), "system")
    gcc = CompilerExe(ccbuilder.CompilerProject.GCC, Path("gcc"), "system")
    ccc = ClangTool.init_with_paths_from_llvm(
        Path("/home/theo/dead/callchain_checker/build/bin/ccc"), llvm
    )
    checker = Checker(
        llvm,
        gcc,
        ccc,
        "ccomp",
    )

    interesting_candidate_futures = []
    interesting_candidates = []
    with ProcessPoolExecutor() as p:
        n = 1000
        for candidate in tqdm(
            generator.generate_code_parallel(n, p),
            desc="Generating candidates",
            total=n,
            dynamic_ncols=True,
        ):
            interesting_candidate_futures.append(
                p.submit(
                    check_interestingness,
                    checker,
                    candidate,
                    target,
                    attackers,
                )
            )

        print("Filtering interesting candidates")
        for fut in tqdm(
            as_completed(interesting_candidate_futures),
            desc="Filtering candidates",
            total=n,
            dynamic_ncols=True,
        ):
            r = fut.result()
            if not r:
                continue
            interesting_candidates.append(r)

        print(f"Found {len(interesting_candidates)} interesting candidates")

    print("Bisecting")
    bsctr = Bisector(bldr)

    for code, markersettings in interesting_candidates:
        print(
            bsctr.bisect(
                (code, markersettings[0][0], target),
                bisection_test,
                target.compiler.revision,
                markersettings[0][1][0].compiler.revision,
                ccbuilder.CompilerProject.LLVM,
                llvm_repo,
            )
        )

    print("Reducing")
    for code, markersettings in interesting_candidates:
        check = make_interestingness_check(
            reduction_check,
            {
                "clang": str(llvm),
                "gcc": str(gcc),
                "ccc": str(ccc),
                "marker": markersettings[0][0],
                "bad_setting": str(target),
                "good_setting": str(markersettings[0][1][0]),
            },
        )
        Reducer().reduce(code, check)
