from copy import copy
from pathlib import Path

from diopter.compiler import CComp, CompilerExe
from pytest import raises

from dead.config import DeadConfig, MissingEntryError, __parse_config_from_dict


def get_dummy_compiler_exe() -> CompilerExe:
    return CompilerExe.from_path(Path("gcc"))


def get_dummy_compiler_ccomp() -> CComp:
    return CComp(exe=Path("cat"))


def test_DeadConfig_json_roundtrip() -> None:
    orig = DeadConfig(
        clang=get_dummy_compiler_exe(),
        gcc=get_dummy_compiler_exe(),
        ccomp=get_dummy_compiler_ccomp(),
        csmith=Path("ls"),
        csmith_include_path=Path("asdfasdf"),
        creduce=Path("wc"),
    )
    roundtrip = __parse_config_from_dict(orig.to_jsonable_dict())
    print(orig)
    print(roundtrip)
    assert orig == roundtrip

    # Also test with None attributes
    orig = DeadConfig(
        clang=get_dummy_compiler_exe(),
        gcc=get_dummy_compiler_exe(),
        ccomp=None,
        csmith=Path("ls"),
        csmith_include_path=Path("asdfasdf"),
        creduce=Path("wc"),
    )
    roundtrip = __parse_config_from_dict(orig.to_jsonable_dict())
    assert orig == roundtrip


def test_missing_entries() -> None:
    dict_config = DeadConfig(
        clang=get_dummy_compiler_exe(),
        gcc=get_dummy_compiler_exe(),
        ccomp=get_dummy_compiler_ccomp(),
        csmith=Path("ls"),
        csmith_include_path=Path("asdfasdf"),
        creduce=Path("wc"),
    ).to_jsonable_dict()
    for entry in dict_config.keys():
        dict_with_missing = copy(dict_config)
        del dict_with_missing[entry]
        with raises(MissingEntryError):
            __parse_config_from_dict(dict_with_missing)
