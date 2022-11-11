# type:ignore

from pathlib import Path

from diopter.compiler import CompilerExe, CComp, CompilationSetting, OptLevel
from diopter.reducer import Reducer
from diopter.bisector import Bisector

from ccbuilder import (
    get_repo,
    CompilerProject,
    DEFAULT_REPOS_DIR,
    DEFAULT_PATCH_DIR,
    DEFAULT_PREFIX_PARENT_PATH,
    PatchDB,
    Builder,
)

from dead.utils import DeadConfig, Scenario
from dead.generator import generate_regression_cases


def run_as_module() -> None:
    system_llvm = CompilerExe.get_system_clang()
    system_gcc = CompilerExe.get_system_gcc()
    gcc_repo = get_repo(CompilerProject.GCC, DEFAULT_REPOS_DIR / "gcc")
    llvm_repo = get_repo(CompilerProject.LLVM, DEFAULT_REPOS_DIR / "llvm-project")
    DeadConfig.init(
        system_llvm,
        llvm_repo,
        system_gcc,
        gcc_repo,
        CComp.get_system_ccomp(),
        "/usr/include/csmith-2.3.0",
    )

    patchdb = PatchDB(Path(DEFAULT_PATCH_DIR) / "patchdb.json")
    bldr = Builder(
        cache_prefix=Path(DEFAULT_PREFIX_PARENT_PATH),
        gcc_repo=gcc_repo,
        llvm_repo=llvm_repo,
        patchdb=patchdb,
        jobs=8,
        logdir=Path("~/dead/logdir"),
    )
    rdcr = Reducer()
    bsctr = Bisector(DEFAULT_PREFIX_PARENT_PATH)

    llvm14 = CompilerExe(
        CompilerProject.LLVM,
        bldr.build(CompilerProject.LLVM, "llvmorg-14.0.6", get_executable=True),
        "llvmorg-14.0.6",
    )
    llvm15 = CompilerExe(
        CompilerProject.LLVM,
        bldr.build(CompilerProject.LLVM, "llvmorg-15.0.2", get_executable=True),
        "llvmorg-15.0.2",
    )
    scenario = Scenario(
        [
            CompilationSetting(compiler=llvm15, opt_level=OptLevel.O3),
            CompilationSetting(compiler=llvm15, opt_level=OptLevel.O2),
            CompilationSetting(compiler=llvm15, opt_level=OptLevel.O1),
        ],
        [
            CompilationSetting(compiler=llvm14, opt_level=OptLevel.O3),
            CompilationSetting(compiler=llvm14, opt_level=OptLevel.O2),
            CompilationSetting(compiler=llvm14, opt_level=OptLevel.O1),
        ],
    )
    print(generator.generate_regression_cases(scenario))
