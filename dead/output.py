from pathlib import Path
from typing import Sequence

from diopter.compiler import CompilationOutput, CompilationOutputKind

from dead.differential_testing import DifferentialTestingCase


def write_case_to_directory(
    case: DifferentialTestingCase, output_directory: Path
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    code_file = (output_directory / "code").with_suffix(
        case.program.language.to_suffix()
    )
    with open(str(code_file), "w") as f:
        print(case.program.code, file=f)

    with open(output_directory / "setting1", "w") as f:
        print(
            " ".join(
                case.setting1.get_compilation_cmd(
                    (case.program, Path(code_file.name)),
                    CompilationOutput(Path("dummy1.s"), CompilationOutputKind.Assembly),
                )
            ),
            file=f,
        )

    with open(output_directory / "setting2", "w") as f:
        print(
            " ".join(
                case.setting2.get_compilation_cmd(
                    (case.program, Path(code_file.name)),
                    CompilationOutput(Path("dummy2.s"), CompilationOutputKind.Assembly),
                )
            ),
            file=f,
        )
    with open(output_directory / "markers_only_eliminated_by_setting1", "w") as f:
        print(
            "\n".join(
                map(lambda m: m.to_macro(), case.markers_only_eliminated_by_setting1)
            ),
            file=f,
        )

    with open(output_directory / "markers_only_eliminated_by_setting2", "w") as f:
        print(
            "\n".join(
                map(lambda m: m.to_macro(), case.markers_only_eliminated_by_setting2)
            ),
            file=f,
        )


def write_cases_to_directory(
    cases: Sequence[DifferentialTestingCase], output_directory: Path
) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    output_sub_dir_n = 0
    for case in cases:
        while (output_directory / str(output_sub_dir_n)).exists():
            output_sub_dir_n += 1
        write_case_to_directory(case, output_directory / str(output_sub_dir_n))
