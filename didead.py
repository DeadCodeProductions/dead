#!/usr/bin/env python3

import logging
import multiprocessing
import os
import re
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace, TracebackType
from typing import Any, Iterable, Optional

import ccbuilder
import diopter
import sqlalchemy
from ccbuilder import (
    Builder,
    BuildException,
    Commit,
    CompilerProject,
    MajorCompilerReleases,
    Repo,
)
from dead_instrumenter.instrumenter import instrument_program
from diopter.database import (
    Base,
    Code,
    CompilerSetting,
    CompressedString,
    CompressedStringList,
    HashableStringList,
)
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    and_,
    event,
    exists,
    func,
    inspect,
    not_,
    or_,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    aliased,
    column_property,
    declarative_base,
    relationship,
)
from sqlalchemy.schema import FetchedValue


class CompileContext:
    def __init__(self, code: str):
        self.code = code
        self.fd_code: Optional[int] = None
        self.fd_asm: Optional[int] = None
        self.code_file: Optional[str] = None
        self.asm_file: Optional[str] = None

    def __enter__(self) -> tuple[str, str]:
        self.fd_code, self.code_file = tempfile.mkstemp(suffix=".c")
        self.fd_asm, self.asm_file = tempfile.mkstemp(suffix=".s")

        with open(self.code_file, "w") as f:
            f.write(self.code)

        return (self.code_file, self.asm_file)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ) -> None:
        if self.code_file and self.fd_code and self.asm_file and self.fd_asm:
            os.remove(self.code_file)
            os.close(self.fd_code)
            # In case of a CompileError,
            # the file itself might not exist.
            if Path(self.asm_file).exists():
                os.remove(self.asm_file)
            os.close(self.fd_asm)
        else:
            raise BuildException("Compier context exited but was not entered")


class DeadGenerator(diopter.generator.CSmithGenerator):
    def generate_case(self) -> str:
        csmith_code = super().generate_code()
        with tempfile.NamedTemporaryFile(suffix=".c") as tfile:
            with open(tfile.name, "w") as f:
                f.write(csmith_code)
            instrument_program(Path(tfile.name), flags=["-I/usr/include/csmith-2.3.0/"])
            with open(tfile.name, "r") as f:
                return f.read()


class Marker(Base):
    __tablename__ = "marker"

    id = Column(
        Integer(), sqlalchemy.Sequence("maker_seq"), unique=True, primary_key=True
    )  # duckdb
    # id = Column(Integer(), primary_key=True) # sqlite

    number: Mapped[int] = Column(Integer(), primary_key=True)

    setting_id = Column(
        Integer(),
        ForeignKey("compiler_setting.id"),
        primary_key=True,
        server_default=FetchedValue(),
    )
    setting: Mapped[CompilerSetting] = relationship(
        "CompilerSetting", foreign_keys=[setting_id], cascade="merge, save-update"
    )

    code_id = Column(String(40), ForeignKey("code.id"), primary_key=True)
    original: Mapped[Code] = relationship(
        "Code", foreign_keys=[code_id], cascade="merge, save-update"
    )

    # Result
    alive: Mapped[bool] = Column(Boolean(), nullable=False)

    def __repr__(self) -> str:
        return f"Marker({self.number}, {self.setting_id})"


case_target_marker_assoc_table = Table(
    "case_target_marker_assoc_table",
    Base.metadata,
    Column("case_id_tm", ForeignKey("cases.id")),
    Column("marker_id", ForeignKey("marker.id")),
)
case_attacker_marker_assoc_table = Table(
    "case_attacker_marker_assoc_table",
    Base.metadata,
    Column("case_id_am", ForeignKey("cases.id")),
    Column("marker_id", ForeignKey("marker.id")),
)
case_target_setting_assoc_table = Table(
    "case_target_setting_assoc_table",
    Base.metadata,
    Column("case_id_tset", ForeignKey("cases.id")),
    Column("setting_id", ForeignKey("compiler_setting.id")),
)
case_attacker_setting_assoc_table = Table(
    "case_attacker_setting_assoc_table",
    Base.metadata,
    Column("case_id_aset", ForeignKey("cases.id")),
    Column("setting_id", ForeignKey("compiler_setting.id")),
)


class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer(), sqlalchemy.Sequence("case_seq"), primary_key=True)
    # id = Column(Integer(), primary_key=True) # Sqlite

    code_id = Column(String(40), ForeignKey("code.id"), nullable=False)
    original: Mapped[Code] = relationship(
        "Code", foreign_keys=[code_id], cascade="merge, save-update"
    )

    reduced_id = Column(String(40), nullable=True)
    # reduced_id = Column(String(40), ForeignKey("code.id"), nullable=True)
    # reduced: Mapped[Optional[Code]] = relationship(
    #    "Code", foreign_keys=[reduced_id]
    #    , cascade="merge, save-update"
    # )

    bisection: Mapped[Optional[Commit]] = Column(String(40))

    # many-to-many -> direct signature approach
    target_settings: Mapped[list[CompilerSetting]] = relationship(
        "CompilerSetting",
        secondary=case_target_setting_assoc_table,
        cascade="merge, save-update",
    )
    attacker_settings: Mapped[list[CompilerSetting]] = relationship(
        "CompilerSetting",
        secondary=case_attacker_setting_assoc_table,
        cascade="merge, save-update",
    )

    # Expected interesting result
    target_marker: Mapped[list[Marker]] = relationship(
        "Marker", secondary=case_target_marker_assoc_table, cascade="merge, save-update"
    )
    attacker_marker: Mapped[list[Marker]] = relationship(
        "Marker",
        secondary=case_attacker_marker_assoc_table,
        cascade="merge, save-update",
    )


# ====================
def get_max_marker(code: str) -> int:
    p = re.compile(r"^void DCEMarker([0-9]+)_\(void\).*")
    mc = -1
    for l in code.split("\n"):
        if m := p.match(l):
            mc = max(int(m.group(1)), mc)
    return mc + 1


def get_asm_str(code: str, compiler_setting: CompilerSetting, bldr: Builder) -> str:
    # Get the assembly output of `code` compiled with `compiler_setting` as str

    project = ccbuilder.get_compiler_project(compiler_setting.compiler_name)
    compiler_exe = bldr.build(project, compiler_setting.rev, get_executable=True)

    with CompileContext(code) as context_res:
        code_file, asm_file = context_res

        cmd = (
            f"{compiler_exe} -S {code_file} -o{asm_file} "
            + compiler_setting.get_flag_string()
        )
        # print(cmd)
        try:
            diopter.utils.run_cmd(cmd)
        except subprocess.CalledProcessError:
            raise Exception()

        with open(asm_file, "r") as f:
            return f.read()


def find_alive_markers(
    code: str,
    compiler_setting: CompilerSetting,
    bldr: Builder,
) -> set[int]:
    """Return set of markers which are found in the assembly."""

    asm = get_asm_str(code, compiler_setting, bldr)

    return extract_markers_from_asm(asm)


def extract_markers_from_asm(asm: str) -> set[int]:
    # Extract alive markers
    alive_markers: set[int] = set()
    alive_regex = re.compile(f".*[call|jmp].*DCEMarker([0-9]+)_.*")
    for line in asm.split("\n"):
        line = line.strip()
        m = alive_regex.match(line)
        if m:
            alive_markers.add(int(m.group(1)))

    logging.debug(f"{alive_markers=}")
    return alive_markers


def basic_interestingness_test(
    targets: list[Marker], attacker: list[Marker]
) -> Optional[tuple[list[Marker], list[Marker]]]:

    target_alive: set[int] = {m.number for m in targets if m.alive}
    attacker_dead: set[int] = {m.number for m in attacker if not m.alive}
    interesting_marker_numbers = target_alive.intersection(attacker_dead)

    if interesting_marker_numbers:
        # Choose just one marker
        marker_number = interesting_marker_numbers.pop()

        # We don't sort by the alive status to get a "free" signature
        i_target_marker: list[Marker] = [
            t for t in targets if t.number == marker_number
        ]
        i_attacker_marker: list[Marker] = [
            a for a in attacker if a.number == marker_number
        ]

        return i_target_marker, i_attacker_marker
    return None


def run_test(code: Code, setting: CompilerSetting, bldr: Builder) -> list[Marker]:

    alive_markers = find_alive_markers(code.code, setting, bldr)
    amount_marker = get_max_marker(code.code)

    return [
        Marker(number=i, original=code, setting=setting, alive=(i in alive_markers))
        for i in range(amount_marker)
    ]


def interestingness_test(
    code: Code,
    targets: list[CompilerSetting],
    attacker: list[CompilerSetting],
    bldr: Builder,
) -> Optional[tuple[list[Marker], list[Marker]]]:

    target_markers: list[Marker] = []
    attacker_markers: list[Marker] = []
    for t in targets:
        target_markers.extend(run_test(code, t, bldr))
    for a in attacker:
        attacker_markers.extend(run_test(code, a, bldr))
    return basic_interestingness_test(target_markers, attacker_markers)


def interestingness_test_to_case(
    code: Code,
    targets: list[CompilerSetting],
    attacker: list[CompilerSetting],
    bldr: Builder,
) -> Optional[Case]:

    if res := interestingness_test(code, targets, attacker, bldr):
        i_target_marker, i_attacker_marker = res

        i_target_settings = [m.setting for m in i_target_marker]
        i_attacker_settings = [m.setting for m in i_attacker_marker]

        return Case(
            original=code,
            target_settings=i_target_settings,
            target_marker=i_target_marker,
            attacker_settings=i_attacker_settings,
            attacker_marker=i_attacker_marker,
        )

    return None


# =====================
def bisection_test(
    new_commit: Commit, interesting_markers: list[Marker], bldr: Builder
) -> Optional[bool]:
    try:
        for m in interesting_markers:
            cs = m.setting.copy_override(rev=new_commit)
            ms = [
                k
                for k in run_test(m.original, cs, bldr)
                if k.number == m.number and k.alive == m.alive
            ]
            if not ms:
                return False
        return True
    except Exception as e:
        logging.warning(f"Test failed with: '{e}'. Continuing...")
        return None


# =====================


def get_script_args(
    bisection_commit: Commit, pre_bisection_commit: Commit, cse: Case, bldr: Builder
):
    pairs: list[tuple[str, int, bool]] = []
    for m in cse.target_marker:
        okproject = ccbuilder.get_compiler_project(m.setting.compiler_name)
        exe_string = f"{bldr.build(okproject, m.setting.rev, get_executable=True)} -S {m.setting.get_flag_string()}"
        bis_exe_string = f"{bldr.build(okproject, bisection_commit, get_executable=True)} -S {m.setting.get_flag_string()}"

        pairs.append((exe_string, m.number, m.alive))
        pairs.append((bis_exe_string, m.number, m.alive))

    for m in cse.attacker_marker:
        okproject = ccbuilder.get_compiler_project(m.setting.compiler_name)
        exe_string = f"{bldr.build(okproject, m.setting.rev, get_executable=True)} -S {m.setting.get_flag_string()}"
        pre_bis_exe_string = f"{bldr.build(okproject, pre_bisection_commit, get_executable=True)} -S {m.setting.get_flag_string()}"

        pairs.append((exe_string, m.number, m.alive))
        pairs.append((pre_bis_exe_string, m.number, m.alive))
    return pairs


def reduction_test(code: str, pairs: list[tuple[str, int, bool]]) -> bool:
    with diopter.utils.TempDirEnv(change_dir=True):
        with open("code.c", "w") as f:
            f.write(code)
        for comp, number, exp_res in pairs:
            asm = diopter.utils.run_cmd(comp + " -o/dev/stdout code.c")

            alive_markers = extract_markers_from_asm(asm)

            if exp_res != (number in alive_markers):
                return False
        return True


# =====================


def gen_pipeline(_: int) -> None:
    iteration = 0
    while True:
        # print(f"{iteration=}")
        iteration += 1
        # code = Code.make(gen.generate_case())
        with open("knowncode.c", "r") as f:
            code = Code.make(f.read())
        if cse := interestingness_test_to_case(
            code, llvm_targets, llvm_attackers, bldr
        ):

            with Session(engine) as session:
                session.add(cse)
                session.commit()
                print(cse.id)
        else:
            logging.info("Failed interestingness test")


if __name__ == "__main__":
    num_lvl = getattr(logging, "INFO")
    logging.basicConfig(level=num_lvl)

    engine = sqlalchemy.create_engine(
        "duckdb:///cases.db", echo=True, future=True, poolclass=sqlalchemy.pool.NullPool
    )
    # Create all tables in the database
    # event.listen(Base.metadata, "after_create", diopter.database.Trigger)
    Base.metadata.create_all(engine)

    jobs = 128

    # Build all compilers
    llvm_repo = ccbuilder.get_repo(
        CompilerProject.LLVM, Path("/home/yann/code/llvm-project/")
    )
    gcc_repo = ccbuilder.get_repo(CompilerProject.GCC, Path("/home/yann/code/gcc/"))
    cached_prefix = Path("/zdata/compiler_cache/")
    patchdb = ccbuilder.PatchDB()
    bldr = ccbuilder.Builder(
        cached_prefix,
        gcc_repo=gcc_repo,
        llvm_repo=llvm_repo,
        jobs=jobs,
        patchdb=patchdb,
    )
    bsctr = diopter.bisector.Bisector(bldr)
    rdcr = diopter.reducer.Reducer()

    llvm_attackers = diopter.utils.create_compiler_settings(
        project=CompilerProject.LLVM,
        # revs=MajorCompilerReleases[CompilerProject.LLVM],
        revs=["16c3143105594e5e58690ab8285b62d409b8af9a"],
        opt_levels=["z"],
        additional_flags=[HashableStringList(["-I/usr/include/csmith-2.3.0/"])],
        repo=llvm_repo,
    )
    llvm_targets = diopter.utils.create_compiler_settings(
        project=CompilerProject.LLVM,
        revs=["2fde26dfcabe6a8270d54569b970767b4773bc66"],
        opt_levels=["z"],
        additional_flags=[HashableStringList(["-I/usr/include/csmith-2.3.0/"])],
        repo=llvm_repo,
    )

    gen = DeadGenerator()

    with Session(engine, expire_on_commit=False) as session:
        cse: Case
        scalars = [
            c for c in session.scalars(select(Case).where(Case.reduced_id.is_(None)))
        ]
        for cse in scalars:
            if cse.bisection:
                import pdb

                pdb.set_trace()
                with open("code.c", "w") as f:
                    f.write(cse.original.code)
                pre_bisection = llvm_repo.rev_to_commit(f"{cse.bisection}~")
                pairs = get_script_args(
                    bisection_commit=cse.bisection,
                    pre_bisection_commit=pre_bisection,
                    cse=cse,
                    bldr=bldr,
                )

                script = diopter.reduction_checks.make_interestingness_check(
                    check=reduction_test,
                    sanitize=False,
                    sanitize_flags="-I/usr/include/csmith-2.3.0/",
                    add_args={"pairs": pairs},
                )
                print(script)

                cse.original = Code.make("dkajslkfj")
                with Session(engine) as session:
                    cse = session.merge(cse)
                    session.commit()
                # if res := rdcr.reduce(cse.original.code, script, jobs):
                #    cse.reduced = Code.make(res)
                #    session.merge(cse)
                #    session.commit()
                import pdb

                pdb.set_trace()

    with Session(engine) as session:
        for cse in session.scalars(select(Case).where(Case.bisection.is_(None))):
            if bis := bsctr.bisect(
                cse.target_marker,
                bisection_test,
                bad_rev=cse.target_settings[0].rev,
                good_rev=cse.attacker_settings[0].rev,
                project=CompilerProject.LLVM,
                repo=llvm_repo,
            ):
                cse.bisection = bis
                session.merge(cse)
                session.commit()
    # gen_pipeline(0)
    exit(0)
    num_lvl = getattr(logging, "INFO")
    logging.basicConfig(level=num_lvl)

    def initializer():
        engine.dispose()

    with multiprocessing.Pool(jobs, initializer=initializer) as p:
        p.map(gen_pipeline, range(jobs))
