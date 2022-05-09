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

import utils
from utils import Case, CompilerSetting, NestedNamespace, Scenario

from ccbuildercached import get_compiler_config

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
            ColumnInfo("scenario_id", "INTEGER", "NOT NULL"),
            ColumnInfo("bisection", "CHAR(40)"),
            ColumnInfo("reduced_code_sha1", "CHAR(40)"),
            ColumnInfo("timestamp", "FLOAT", "NOT NULL"),
            ColumnInfo(
                "UNIQUE(code_sha1, marker, bad_setting_id, scenario_id, bisection, reduced_code_sha1) "
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
        "compiler_setting": [
            ColumnInfo("compiler_setting_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ColumnInfo("compiler", "TEXT", "NOT NULL"),
            ColumnInfo("rev", "CHAR(40)", "NOT NULL"),
            ColumnInfo("opt_level", "TEXT", "NOT NULL"),
            ColumnInfo("additional_flags", "TEXT"),
        ],
        "good_settings": [
            ColumnInfo("case_id", "", "REFERENCES cases(case_id) NOT NULL"),
            ColumnInfo(
                "compiler_setting_id",
                "",
                "REFERENCES compiler_setting(compiler_setting_id) NOT NULL",
            ),
        ],
        "scenario_ids": [
            ColumnInfo("scenario_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        ],
        "scenario": [
            ColumnInfo(
                "scenario_id", "", "REFERENCES scenario_ids(scenario_id) PRIMARY KEY"
            ),
            ColumnInfo("generator_version", "INTEGER", "NOT NULL"),
            ColumnInfo("bisector_version", "INTEGER", "NOT NULL"),
            ColumnInfo("reducer_version", "INTEGER", "NOT NULL"),
            ColumnInfo("instrumenter_version", "INTEGER", "NOT NULL"),
            ColumnInfo("csmith_min", "INTEGER", "NOT NULL"),
            ColumnInfo("csmith_max", "INTEGER", "NOT NULL"),
            ColumnInfo("reduce_program", "TEXT", "NOT NULL"),
        ],
        "scenario_attacker": [
            ColumnInfo(
                "scenario_id", "", "REFERENCES scenario_ids(scenario_id) NOT NULL"
            ),
            ColumnInfo(
                "compiler_setting_id",
                "",
                "REFERENCES compiler_setting(compiler_setting_id) NOT NULL",
            ),
        ],
        "scenario_target": [
            ColumnInfo(
                "scenario_id", "", "REFERENCES scenario_ids(scenario_id) NOT NULL"
            ),
            ColumnInfo(
                "compiler_setting_id",
                "",
                "REFERENCES compiler_setting(compiler_setting_id) NOT NULL",
            ),
        ],
        "timing": [
            ColumnInfo("case_id", "", "REFERENCES cases(case_id) PRIMARY KEY"),
            ColumnInfo("generator_time", "FLOAT"),
            ColumnInfo("generator_try_count", "INTEGER"),
            ColumnInfo("bisector_time", "FLOAT"),
            ColumnInfo("bisector_steps", "INTEGER"),
            ColumnInfo("reducer_time", "FLOAT"),
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

    def record_case(self, case: Case) -> RowID:
        """Save a case to the DB and get its ID.

        Args:
            case (Case): Case to save.

        Returns:
            RowID: ID of case.
        """

        bad_setting_id = self.record_compiler_setting(case.bad_setting)
        with self.con:
            good_setting_ids = [
                self.record_compiler_setting(good_setting)
                for good_setting in case.good_settings
            ]
        scenario_id = self.record_scenario(case.scenario)

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
                    scenario_id,
                    bisection,
                    reduced_code_sha1,
                    case.timestamp,
                ),
            )
            case_id = RowID(cur.lastrowid)
            cur.executemany(
                "INSERT INTO good_settings VALUES (?,?)",
                ((case_id, gs_id) for gs_id in good_setting_ids),
            )

        return case_id

    def record_compiler_setting(self, compiler_setting: CompilerSetting) -> RowID:
        """Save a compiler setting to the DB and get its ID.

        Args:
            self:
            compiler_setting (CompilerSetting): compiler setting to save.

        Returns:
            RowID: ID of saved compiler setting.
        """
        if s_id := self.get_compiler_setting_id(compiler_setting):
            return s_id
        with self.con:
            cur = self.con.cursor()
            cur.execute(
                "INSERT INTO compiler_setting VALUES (NULL,?,?,?,?)",
                (
                    compiler_setting.compiler_config.name,
                    compiler_setting.rev,
                    compiler_setting.opt_level,
                    compiler_setting.get_flag_str(),
                ),
            )
            ns_id = RowID(cur.lastrowid)

        return ns_id

    def record_scenario(self, scenario: Scenario) -> RowID:
        """Save a scenario to the DB and get its ID.

        Args:
            scenario (Scenario): Scenario to save.

        Returns:
            RowID: ID of `scenario`
        """
        if s_id := self.get_scenario_id(scenario):
            return s_id
        target_ids = [
            self.record_compiler_setting(target_setting)
            for target_setting in scenario.target_settings
        ]
        attacker_ids = [
            self.record_compiler_setting(attacker_setting)
            for attacker_setting in scenario.attacker_settings
        ]
        with self.con:
            ns_id = self.get_new_scenario_id(no_commit=True)

            def insert_settings(table: str, settings: list[RowID]) -> None:
                self.con.executemany(
                    f"INSERT INTO {table} VALUES (?,?)",
                    ((ns_id, s) for s in settings),
                )

            insert_settings("scenario_target", target_ids)
            insert_settings("scenario_attacker", attacker_ids)

            self.con.execute(
                "INSERT INTO scenario VALUES (?,?,?,?,?,?,?,?)",
                (
                    ns_id,
                    scenario.generator_version,
                    scenario.bisector_version,
                    scenario.reducer_version,
                    scenario.instrumenter_version,
                    self.config.csmith.min_size,
                    self.config.csmith.max_size,
                    os.path.basename(self.config.creduce),
                ),
            )
        return ns_id

    def get_new_scenario_id(self, no_commit: bool) -> RowID:
        """Get a new scenario ID.

        Args:
            no_commit (bool): Don't commit the change.

        Returns:
            RowID: New scenario id
        """
        cur = self.con.cursor()
        cur.execute("INSERT INTO scenario_ids VALUES (NULL)")
        if not no_commit:
            self.con.commit()
        return RowID(cur.lastrowid)

    def get_scenario_id(self, scenario: Scenario) -> Optional[RowID]:
        """See if there is already an ID for `scenario` in the database
        and return it if it does.

        Args:
            scenario (Scenario): scenario to get an ID for

        Returns:
            Optional[RowID]: RowID if the scenario exists
        """

        def get_scenario_ids(id_: RowID, table: str, id_str: str) -> set[int]:
            cursor = self.con.cursor()
            return set(
                s_id[0]
                for s_id in cursor.execute(
                    f"SELECT scenario_id FROM {table} WHERE {id_str}== ? ",
                    (id_,),
                ).fetchall()
            )

        # Get all scenario's which have the same versions
        candidate_ids: set[RowID] = set(
            [
                r[0]
                for r in self.con.execute(
                    "SELECT scenario_id FROM scenario"
                    " WHERE generator_version == ?"
                    " AND bisector_version == ?"
                    " AND reducer_version == ?"
                    " AND instrumenter_version == ?"
                    " AND csmith_min == ?"
                    " AND csmith_max == ?"
                    " AND reduce_program == ?",
                    (
                        scenario.generator_version,
                        scenario.bisector_version,
                        scenario.reducer_version,
                        scenario.instrumenter_version,
                        self.config.csmith.min_size,
                        self.config.csmith.max_size,
                        self.config.creduce,
                    ),
                ).fetchall()
            ]
        )

        # Get compiler setting ids of scenario
        target_ids: list[RowID] = []
        for setting in scenario.target_settings:
            if not (s_id := self.get_compiler_setting_id(setting)):
                return None
            target_ids.append(s_id)

        attacker_ids: list[RowID] = []
        for setting in scenario.attacker_settings:
            if not (s_id := self.get_compiler_setting_id(setting)):
                return None
            attacker_ids.append(s_id)

        # Compare compiler setting IDs
        candidate_ids = candidate_ids & reduce(
            lambda x, y: x & y,
            (
                get_scenario_ids(target_id, "scenario_target", "compiler_setting_id")
                for target_id in target_ids
            ),
        )
        if not candidate_ids:
            return None

        candidate_ids = reduce(
            lambda x, y: x & y,
            chain(
                (
                    get_scenario_ids(
                        attacker_id, "scenario_attacker", "compiler_setting_id"
                    )
                    for attacker_id in attacker_ids
                ),
                (candidate_ids,),
            ),
        )

        if not candidate_ids:
            return None
        return RowID(next(candidate_ids.__iter__()))

    def get_compiler_setting_id(
        self, compiler_setting: CompilerSetting
    ) -> Optional[RowID]:
        """Get the ID of a given CompilerSetting, if it is in the DB.

        Args:
            compiler_setting (CompilerSetting): CompilerSetting to get the id of.

        Returns:
            Optional[RowID]: The ID, if found.
        """
        result = self.con.execute(
            "SELECT compiler_setting_id "
            "FROM compiler_setting "
            "WHERE compiler == ? AND rev == ? AND opt_level == ? AND additional_flags == ?",
            (
                compiler_setting.compiler_config.name,
                compiler_setting.rev,
                compiler_setting.opt_level,
                "|".join(compiler_setting.get_flag_cmd()),
            ),
        ).fetchone()

        if not result:
            return None
        s_id = RowID(result[0])

        return s_id

    @cache
    def get_compiler_setting_from_id(
        self, compiler_setting_id: int
    ) -> Optional[CompilerSetting]:
        """Get a compiler setting from a compiler_setting_id, if the ID exists.

        Args:
            self:
            compiler_setting_id (int): Compiler setting ID to get the compiler setting of

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

        compiler, rev, opt_level, flags = res
        return CompilerSetting(
            get_compiler_config(compiler, self.config.repodir),
            rev,
            opt_level,
            flags.split("|"),
        )

    @cache
    def get_scenario_from_id(self, scenario_id: RowID) -> Optional[Scenario]:
        """Get a scenario from a specified ID.

        Args:
            scenario_id (RowID): ID of scenario to get

        Returns:
            Optional[Scenario]: Scenario corresponding to RowID
        """

        def get_settings(
            self: CaseDatabase, table: str, s_id: int
        ) -> list[CompilerSetting]:

            ids = self.con.execute(
                f"SELECT compiler_setting_id FROM {table} WHERE scenario_id == ?",
                (s_id,),
            ).fetchall()
            pre = [self.get_compiler_setting_from_id(row[0]) for row in ids]

            # For the type checker. It can't possibly know about the constraints
            # in the DB.
            settings = [c for c in pre if c]

            return settings

        target_settings = get_settings(self, "scenario_target", scenario_id)
        attacker_settings = get_settings(self, "scenario_attacker", scenario_id)
        scenario = Scenario(target_settings, attacker_settings)

        res = self.con.execute(
            "SELECT generator_version, bisector_version, reducer_version, instrumenter_version FROM scenario WHERE scenario_id == ?",
            (scenario_id,),
        ).fetchone()

        if not res:
            return None

        generator_version, bisector_version, reducer_version, instrumenter_version = res

        scenario.generator_version = generator_version
        scenario.bisector_version = bisector_version
        scenario.reducer_version = reducer_version
        scenario.instrumenter_version = instrumenter_version

        return scenario

    def get_case_from_id(self, case_id: RowID) -> Optional[Case]:
        """Get a case from the database based on its ID.
        Note: the case will *NOT* replace reduced code with
        massaged code.

        Args:
            case_id (int): ID of wanted case

        Returns:
            Optional[Case]: Returns case if it exists
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
            scenario_id,
            bisection,
            reduced_code_sha1,
            timestamp,
        ) = res

        good_settings_ids = self.con.execute(
            "SELECT compiler_setting_id FROM good_settings WHERE case_id == ?",
            (case_id,),
        ).fetchall()

        code = self.get_code_from_id(code_sha1)
        if not code:
            raise DatabaseError("Missing original code")

        reduced_code = self.get_code_from_id(reduced_code_sha1)

        scenario = self.get_scenario_from_id(scenario_id)

        # Get Settings
        bad_setting = self.get_compiler_setting_from_id(bad_setting_id)
        pre_good_settings = [
            self.get_compiler_setting_from_id(row[0]) for row in good_settings_ids
        ]

        # There should never be a problem here (TM) because of the the DB
        # FOREIGN KEY constraints.
        good_settings = [gs for gs in pre_good_settings if gs]
        if not bad_setting:
            raise DatabaseError("Bad setting id was not found")
        if not scenario:
            raise DatabaseError("Scenario id was not found")

        case = Case(
            code,
            marker,
            bad_setting,
            good_settings,
            scenario,
            reduced_code=reduced_code,
            bisection=bisection,
            path=None,
            timestamp=timestamp,
        )

        return case

    def get_case_from_id_or_die(self, case_id: RowID) -> Case:
        pre_check_case = self.get_case_from_id(case_id)
        if not pre_check_case:
            print("No case with this ID.", file=sys.stderr)
            exit(1)
        else:
            case = pre_check_case
        return case

    def update_case(self, case_id: RowID, case: Case) -> None:
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

        bad_setting_id = self.record_compiler_setting(case.bad_setting)
        scenario_id = self.record_scenario(case.scenario)

        with self.con:
            # REPLACE is just an alias for INSERT OR REPLACE
            self.con.execute(
                "INSERT OR REPLACE INTO cases VALUES (?,?,?,?,?,?,?,?)",
                (
                    case_id,
                    code_sha1,
                    case.marker,
                    bad_setting_id,
                    scenario_id,
                    case.bisection,
                    reduced_code_sha1,
                    case.timestamp,
                ),
            )

    def record_timing(
        self,
        case_id: RowID,
        generator_time: Optional[float] = None,
        generator_try_count: Optional[int] = None,
        bisector_time: Optional[float] = None,
        bisector_steps: Optional[int] = None,
        reducer_time: Optional[float] = None,
    ) -> None:
        """Record timing metric for `case_id`

        Args:
            case_id (RowID):
            generator_time (Optional[float]): Time the generator took
            generator_try_count (Optional[int]): How often the generator tried
            bisector_time (Optional[float]): How long the bisector took
            bisector_steps (Optional[int]): How many steps the bisector made
            reducer_time (Optional[float]): How long the reducer took

        Returns:
            None:
        """

        with self.con:
            self.con.execute(
                "INSERT OR REPLACE INTO timing VALUES(?,?,?,?,?,?)",
                (
                    case_id,
                    generator_time,
                    generator_try_count,
                    bisector_time,
                    bisector_steps,
                    reducer_time,
                ),
            )

    def get_timing_from_id(
        self, case_id: RowID
    ) -> tuple[
        Optional[float], Optional[int], Optional[float], Optional[int], Optional[float]
    ]:
        """Get the timing entries for a case.

        Args:
            self:
            case_id (RowID): case_id

        Returns:
            tuple[
                Optional[float], Optional[int], Optional[float], Optional[int], Optional[float]
            ]: Generator time, generator try count, bisector time, bisector steps, reducer time
        """

        res = self.con.execute(
            "SELECT * FROM timing WHERE case_id == ?", (case_id,)
        ).fetchone()
        if not res:
            return (None, None, None, None, None)
        _, g_time, gtc, b_time, b_steps, r_time = res
        return g_time, gtc, b_time, b_steps, r_time

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
