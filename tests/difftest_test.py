from pathlib import Path

from diopter.compiler import (
    CompilationSetting,
    CompilerExe,
    Language,
    OptLevel,
    SourceProgram,
)

from dead.differential_testing import differential_test


def test_basic_differential_test() -> None:
    # Known case where gcc cannot infer that a branch is dead
    gcc = CompilationSetting(
        compiler=CompilerExe.from_path(Path("gcc")), opt_level=OptLevel.O3
    )
    clang = CompilationSetting(
        compiler=CompilerExe.from_path(Path("clang")), opt_level=OptLevel.O3
    )

    program = SourceProgram(
        code="static int a = 0; int main () { if (a) { a = 1; } return 0; }",
        language=Language.C,
    )

    case = differential_test(program, gcc, clang)

    assert case
    assert set(case.markers_only_eliminated_by_setting2) > set(
        case.markers_only_eliminated_by_setting1
    )
