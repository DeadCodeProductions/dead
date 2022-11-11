# type:ignore
import hashlib
import os
import sqlite3
import sys
import zlib
from dataclasses import dataclass
from functools import cache, reduce
from itertools import chain
from pathlib import Path
from typing import ClassVar, Optional

import ccbuilder

import utils
from utils import NestedNamespace
from dead.utils import RegressionCase

from diopter.compiler import CompilerExe, CompilationSetting


class DatabaseError(Exception):
    pass


@dataclass
class ColumnInfo:
    name: str
    typename: str
    constrains: str = ""

    def __str__(self) -> str:
        return f"{self.name} {self.typename} {self.constrains}"


RowID = int


class CaseDatabase:
    config: NestedNamespace
    con: sqlite3.Connection
    tables: ClassVar[dict[str, list[ColumnInfo]]] = {
        "cases": [
            ColumnInfo("case_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ColumnInfo("code_sha1", "", "REFERENCES code(code_sha1) NOT NULL"),
            ColumnInfo("marker", "TEXT", "NOT NULL"),
            ColumnInfo("bad_setting_id", "INTEGER", "NOT NULL"),
            ColumnInfo("good_setting_id", "INTEGER", "NOT NULL"),
            ColumnInfo("bisection", "CHAR(40)"),
            ColumnInfo("reduced_code_sha1", "CHAR(40)"),
            ColumnInfo("timestamp", "FLOAT", "NOT NULL"),
            ColumnInfo(
                "UNIQUE(code_sha1, marker, bad_setting_id, good_setting_id_id, bisection, reduced_code_sha1) "
                "ON CONFLICT REPLACE",
                "",
            ),
        ],
        "code": [
            ColumnInfo("code_sha1", "CHAR(40)", "PRIMARY KEY"),
            ColumnInfo("compressed_code", "BLOB"),
        ],
        "reported_cases": [
            ColumnInfo("case_id", "", "REFERENCES cases(case_id) PRIMARY KEY"),
            ColumnInfo("massaged_code_sha1", "", "REFERENCES code(code_sha1)"),
            ColumnInfo("bug_report_link", "TEXT"),
            ColumnInfo("fixed_by", "CHAR(40)"),
        ],
        "compilation_setting": [
            ColumnInfo("compiler_setting_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ColumnInfo("compiler", "TEXT", "NOT NULL"),
            ColumnInfo("rev", "CHAR(40)", "NOT NULL"),
            ColumnInfo("opt_level", "INT", "NOT NULL"),
            ColumnInfo("additional_flags", "TEXT"),
        ],
    }

    def __init__(self, config: NestedNamespace, db_path: Path) -> None:
        self.config = config
        self.con = sqlite3.connect(db_path, timeout=60)
        self.create_tables()

    def create_tables(self) -> None:
        def make_query(table: str, columns: list[ColumnInfo]) -> str:
            column_decl = ",".join(str(column) for column in columns)
            return f"CREATE TABLE IF NOT EXISTS {table} (" + column_decl + ")"

        for table, columns in CaseDatabase.tables.items():
            self.con.execute(make_query(table, columns))

    def record_code(self, code: str) -> str:
        """Inserts `code` into the database's `code`-table and returns its
        sha1-hash which serves as a key.

        Args:
            code (str): code to be inserted

        Returns:
            str: SHA1 of code which serves as the key.
        """
        # Take the hash before the compression to handle changes
        # in the compression library.
        code_sha1 = hashlib.sha1(code.encode("utf-8")).hexdigest()
        compressed_code = zlib.compress(code.encode("utf-8"), level=9)

        self.con.execute(
            "INSERT OR IGNORE INTO code VALUES (?, ?)", (code_sha1, compressed_code)
        )
        return code_sha1

    def get_code_from_id(self, code_id: str) -> Optional[str]:
        """Get code from the database if it exists.

        Args:
            code_id (str): SHA1 of code

        Returns:
            Optional[str]: Saved code if it exists, else None
        """

        res = self.con.execute(
            "SELECT compressed_code FROM code WHERE code_sha1 == ?", (code_id,)
        ).fetchone()
        if res:
            code = zlib.decompress(res[0]).decode("utf-8")
            return code
        else:
            return None

    def record_reported_case(
        self,
        case_id: RowID,
        massaged_code: Optional[str],
        bug_report_link: Optional[str],
        fixed_by: Optional[str],
    ) -> None:
        """Save additional information for an already saved case.

        Args:
            case_id (RowID): case_id
            massaged_code (Optional[str]): adapted reduced code for better reduction.
            bug_report_link (Optional[str]): Link to the bug report.
            fixed_by (Optional[str]): If the case is already fixed.

        Returns:
            None:
        """
        code_sha1 = None
        if massaged_code:
            code_sha1 = self.record_code(massaged_code)

        with self.con:
            self.con.execute(
                "INSERT OR REPLACE INTO reported_cases VALUES (?,?,?,?)",
                (
                    case_id,
                    code_sha1,
                    bug_report_link,
                    fixed_by,
                ),
            )

    def record_case(self, case: RegressionCase) -> RowID:
        """Save a case to the DB and get its ID.

        Args:
            case (RegressionCase): Case to save.

        Returns:
            RowID: ID of case.
        """

        bad_setting_id = self.record_compilation_setting(case.bad_setting)
        good_setting_id = self.record_compilation_setting(case.good_setting)

        with self.con:
            cur = self.con.cursor()
            bisection = case.bisection
            reduced_code_sha1 = (
                self.record_code(case.reduced_code) if case.reduced_code else None
            )

            code_sha1 = self.record_code(case.code)

            cur.execute(
                "INSERT INTO cases VALUES (NULL,?,?,?,?,?,?,?)",
                (
                    code_sha1,
                    case.marker,
                    bad_setting_id,
                    good_setting_id,
                    bisection,
                    reduced_code_sha1,
                    case.timestamp,
                ),
            )
            if not cur.lastrowid:
                raise DatabaseError("No last row id was returned")
            case_id = RowID(cur.lastrowid)
        return case_id

    def record_compilation_setting(self, compiler_setting: CompilationSetting) -> RowID:
        """Save a compiler setting to the DB and get its ID.

        Args:
            self:
            compiler_setting (CompilationSetting): compiler setting to save.

        Returns:
            RowID: ID of saved compiler setting.
        """
        if s_id := self.get_compilation_setting_id(compiler_setting):
            return s_id
        with self.con:
            cur = self.con.cursor()
            cur.execute(
                "INSERT INTO compiler_setting VALUES (NULL,?,?,?,?)",
                (
                    compiler_setting.compiler.project.to_string(),
                    compiler_setting.compiler.revision,
                    compiler_setting.opt_level.value,
                    "|".join(compiler_setting.flags)
                    + "###"
                    + "|".join(compiler_setting.include_paths)
                    + "###"
                    + "|".join(compiler_setting.system_include_paths),
                ),
            )
            if not cur.lastrowid:
                raise DatabaseError("No last row id was returned")
            ns_id = RowID(cur.lastrowid)

        return ns_id

    def get_compilation_setting_id(
        self, compiler_setting: CompilationSetting
    ) -> Optional[RowID]:
        """Get the ID of a given CompilerSetting, if it is in the DB.

        Args:
            compiler_setting (CompilationSetting): CompilerSetting to get the id of.

        Returns:
            Optional[RowID]: The ID, if found.
        """
        result = self.con.execute(
            "SELECT compiler_setting_id "
            "FROM compiler_setting "
            "WHERE compiler == ? AND rev == ? AND opt_level == ? AND additional_flags == ?",
            (
                compiler_setting.compiler.project.to_string(),
                compiler_setting.compiler.revision,
                compiler_setting.opt_level.value,
                "|".join(compiler_setting.flags)
                + "###"
                + "|".join(compiler_setting.include_paths)
                + "###"
                + "|".join(compiler_setting.system_include_paths),
            ),
        ).fetchone()

        if not result:
            return None
        s_id = RowID(result[0])

        return s_id

    @cache
    def get_compilation_setting_from_id(
        self, compiler_setting_id: int, builder: ccbuilder.Builder
    ) -> Optional[CompilationSetting]:
        """Get a compiler setting from a compiler_setting_id, if the ID exists.

        Args:
            self:
            compiler_setting_id (int): Compiler setting ID to get the compiler setting of
            builder (ccbuilder.Builder)

        Returns:
            Optional[CompilerSetting]: Compiler setting with ID `compiler_setting_id`
        """

        res = self.con.execute(
            "SELECT compiler, rev, opt_level, additional_flags"
            " FROM compiler_setting"
            " WHERE compiler_setting_id == ?",
            (compiler_setting_id,),
        ).fetchone()

        if not res:
            return None

        compiler, rev, opt_level, flags_includes = res
        flags, include_paths, system_include_paths = flags_includes.split("###")
        project, repo = ccbuilder.get_compiler_info(
            compiler.lower(), Path(self.config.repodir)
        )
        # we shouldn't really be building here, we need a ccbuilder.cache_lookup()
        return CompilationSetting(
            compiler=compiler.CompilerExe(
                project, rev, builder.build(project, rev, True)
            ),
            opt_level=compiler.OptLevel(int(opt_level)),
            flags=flags.split("|"),
            include_paths=include_paths.split("|"),
            system_include_paths=system_include_paths.split("|"),
        )

    def get_case_from_id(self, case_id: RowID) -> Optional[RegressionCase]:
        """Get a case from the database based on its ID.
        Note: the case will *NOT* replace reduced code with
        massaged code.

        Args:
            case_id (int): ID of wanted case

        Returns:
            Optional[RegressionCase]: Returns case if it exists
        """
        if not (
            res := self.con.execute(
                "SELECT * FROM cases WHERE case_id == ?", (case_id,)
            ).fetchone()
        ):
            return None

        (
            _,
            code_sha1,
            marker,
            bad_setting_id,
            good_setting_id,
            bisection,
            reduced_code_sha1,
            timestamp,
        ) = res

        code = self.get_code_from_id(code_sha1)
        if not code:
            raise DatabaseError("Missing original code")

        reduced_code = self.get_code_from_id(reduced_code_sha1)

        # Get Settings
        bad_setting = self.get_compilation_setting_from_id(bad_setting_id)
        good_setting = self.get_compilation_setting_from_id(good_setting_id)

        # There should never be a problem here (TM) because of the the DB
        # FOREIGN KEY constraints.
        if not bad_setting:
            raise DatabaseError("Bad setting id was not found")
        if not good_setting:
            raise DatabaseError("Good setting id was not found")

        return RegressionCase(
            code,
            marker,
            bad_setting,
            good_setting,
            reduced_code=reduced_code,
            bisection=bisection,
            timestamp=timestamp,
        )

    def get_case_from_id_or_die(self, case_id: RowID) -> RegressionCase:
        pre_check_case = self.get_case_from_id(case_id)
        if not pre_check_case:
            print("No case with this ID.", file=sys.stderr)
            exit(1)
        else:
            case = pre_check_case
        return case

    def update_case(self, case_id: RowID, case: RegressionCase) -> None:
        """Update case with ID `case_id` with the values of `case`

        Args:
            case_id (str): ID of case to update
            case (Case): Case to get the info from

        Returns:
            None:
        """
        code_sha1 = self.record_code(case.code)

        if case.reduced_code:
            reduced_code_sha1: Optional[str] = self.record_code(case.reduced_code)
        else:
            reduced_code_sha1 = None

        bad_setting_id = self.record_compilation_setting(case.bad_setting)
        good_setting_id = self.record_compilation_setting(case.good_setting)

        with self.con:
            # REPLACE is just an alias for INSERT OR REPLACE
            self.con.execute(
                "INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?,?)",
                (
                    case_id,
                    code_sha1,
                    case.marker,
                    bad_setting_id,
                    good_setting_id,
                    case.bisection,
                    reduced_code_sha1,
                    case.timestamp,
                ),
            )

    def get_report_info_from_id(
        self, case_id: RowID
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Get report infos for case_id.
        The order is massaged_code, link, fixed_by commit.

        Args:
            self:
            case_id (RowID): case_id

        Returns:
            tuple[Optional[str], Optional[str], Optional[str]]:
        """

        res = self.con.execute(
            "SELECT * FROM reported_cases WHERE case_id == ?", (case_id,)
        ).fetchone()
        if not res:
            return (None, None, None)

        _, massaged_code_sha1, link, fixed_by = res

        massaged_code = self.get_code_from_id(massaged_code_sha1)
        return massaged_code, link, fixed_by
