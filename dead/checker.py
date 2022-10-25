from dead_instrumenter.instrumenter import InstrumentedProgram
from callchain_checker.callchain_checker import callchain_exists
from diopter.compiler import CompilationSetting


def find_interesting_markers(
    program: InstrumentedProgram,
    bad_setting: CompilationSetting,
    good_setting: CompilationSetting,
) -> list[str]:
    """Find interesting markers in program.

    A marker is interesting if:
    1) It is not eliminated by bad_setting.
    2) It is eliminated by the good setting.
    3) There is a callchain from main to the marker

    Args:
        self:
        program (InstrumentedProgram): the program to check
        bad_setting (CompilationSetting): The compilation setting that misses the markers
        good_setting (CompilationSetting): The compilation setting that can eliminate the markers

    Returns:
        list[str]:
            list of interesting markers

    Raises:
        diopter.compiler.CompilerError:
            The compilation required to find alive markers might fail
    """

    return [
        marker
        for marker in set(program.find_alive_markers(bad_setting))
        - set(program.find_alive_markers(good_setting))
        if callchain_exists(program, "main", marker)
    ]
