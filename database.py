import os
import sqlite3
import time
import zlib
from dataclasses import dataclass
from functools import reduce
from itertools import chain
from pathlib import Path
from typing import ClassVar, Optional, Union

from utils import Case, CompilerSetting, NestedNamespace, Scenario


@dataclass
class ColumnInfo:
    name: str
    typename: str
    constrains: str = ""

    def __str__(self) -> str:
        return f"{self.name} {self.typename} {self.constrains}"


@dataclass
class RowID:
    val: int


class CaseDatabase:
    con: sqlite3.Connection
    tables: ClassVar[dict[str, list[ColumnInfo]]] = {
        "cases": [
            ColumnInfo("case_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ColumnInfo("code", "TEXT", "NOT NULL"),
            ColumnInfo("marker", "TEXT", "NOT NULL"),
            ColumnInfo("bad_setting", "INTEGER", "NOT NULL"),
            ColumnInfo("scenario", "INTEGER", "NOT NULL"),
            ColumnInfo("timestamp", "FLOAT", "NOT NULL"),
        ],
        "reported_cases": [
            ColumnInfo("case_id", "INTEGER", "NOT NULL"),
            ColumnInfo("massaged_code", "TEXT", "NOT NULL"),
            ColumnInfo("bug_report_link", "TEXT", "NOT NULL"),
            ColumnInfo("fixed_by", "TEXT"),
        ],
        "good_settings": [
            ColumnInfo("case_id", "INTEGER", "NOT NULL"),
            ColumnInfo("good_setting_id", "INTEGER", "NOT NULL"),
        ],
        "reduced_codes": [
            ColumnInfo("case_id", "INTEGER", "NOT NULL"),
            ColumnInfo("reduced_code", "TEXT", "NOT NULL"),
        ],
        "bisections": [
            ColumnInfo("case_id", "INTEGER", "NOT NULL"),
            ColumnInfo("bisection", "TEXT", "NOT NULL"),
        ],
        "compiler_settings": [
            ColumnInfo("compiler_setting_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
            ColumnInfo("compiler", "TEXT", "NOT NULL"),
            ColumnInfo("rev", "TEXT", "NOT NULL"),
            ColumnInfo("opt_level", "TEXT"),
        ],
        "compiler_settings_additional_flags": [
            ColumnInfo("compiler_setting_id", "INTEGER", "NOT NULL"),
            ColumnInfo("flag", "TEXT", "NOT NULL"),
        ],
        "scenarios": [
            ColumnInfo("scenario_id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        ],
        "scenario_targets": [
            ColumnInfo("scenario_id", "INTEGER", "NOT NULL"),
            ColumnInfo("target_id", "INTEGER", "NOT NULL"),
        ],
        "scenario_attackers": [
            ColumnInfo("scenario_id", "INTEGER", "NOT NULL"),
            ColumnInfo("attacker_id", "INTEGER", "NOT NULL"),
        ],
        "scenario_misc": [
            ColumnInfo("scenario_id", "INTEGER", "NOT NULL"),
            ColumnInfo("generator_version", "INTEGER", "NOT NULL"),
            ColumnInfo("bisector_version", "INTEGER", "NOT NULL"),
            ColumnInfo("reducer_version", "INTEGER", "NOT NULL"),
            ColumnInfo("instrumenter_version", "INTEGER", "NOT NULL"),
            ColumnInfo("csmith_min", "INTEGER", "NOT NULL"),
            ColumnInfo("csmith_max", "INTEGER", "NOT NULL"),
            ColumnInfo("reduce_program", "TEXT", "NOT NULL"),
        ],
    }

    def __init__(self, db_path: Path) -> None:
        self.con = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self) -> None:
        def make_query(table: str, columns: list[ColumnInfo]) -> str:
            column_decl = ",".join(str(column) for column in columns)
            return f"CREATE TABLE IF NOT EXISTS {table} (" + column_decl + ")"

        with self.con:
            for table, columns in CaseDatabase.tables.items():
                self.con.execute(make_query(table, columns))

    def record_reported_case(
        self,
        case_id: RowID,
        massaged_code: str,
        bug_report_link: str,
        fixed_by: Optional[str],
    ) -> None:
        with self.con:
            self.con.execute(
                "INSERT INTO reported_cases VALUES (?,?,?,?)",
                (
                    case_id.val,
                    massaged_code,
                    bug_report_link,
                    fixed_by,
                ),
            )

    def record_case(
        self, config: NestedNamespace, case: Case, timestamp: Optional[float] = None
    ) -> RowID:
        if not timestamp:
            timestamp = time.time()
        bad_setting_id = self.record_compiler_setting(case.bad_setting)
        with self.con:
            good_setting_ids = [
                self.record_compiler_setting(good_setting)
                for good_setting in case.good_settings
            ]
        scenario_id = self.record_scenario(config, case.scenario)

        with self.con:
            cur = self.con.cursor()
            # Can we use CaseDatabase.table_columnsHow to automate this and make it less error prone?
            cur.execute(
                "INSERT INTO cases VALUES (NULL,?,?,?,?,?)",
                (
                    zlib.compress(case.code.encode()),
                    case.marker,
                    bad_setting_id.val,
                    scenario_id.val,
                    timestamp,
                ),
            )
            case_id = RowID(cur.lastrowid)
            cur.executemany(
                "INSERT INTO good_settings VALUES (?,?)",
                ((case_id.val, gs_id.val) for gs_id in good_setting_ids),
            )
            cur.executemany(
                "INSERT INTO reduced_codes VALUES (?,?)",
                ((case_id.val, code) for code in case.reduced_code),
            )

            cur.executemany(
                "INSERT INTO bisections VALUES (?,?)",
                ((case_id.val, bisection) for bisection in case.bisections),
            )

        return case_id

    def record_compiler_setting(self, compiler_setting: CompilerSetting) -> RowID:
        if s_id := self.get_compiler_setting_id(compiler_setting):
            return s_id
        with self.con:
            cur = self.con.cursor()
            cur.execute(
                "INSERT INTO compiler_settings VALUES (NULL,?,?,?)",
                (
                    compiler_setting.compiler_config.name,
                    compiler_setting.rev,
                    compiler_setting.opt_level,
                ),
            )
            ns_id = RowID(cur.lastrowid)

        with self.con:
            if compiler_setting.additional_flags:
                cur.executemany(
                    "INSERT INTO compiler_settings_additional_flags VALUES (?,?)",
                    ((ns_id.val, flag) for flag in compiler_setting.additional_flags),
                )

        return ns_id

    def record_scenario(self, config: NestedNamespace, scenario: Scenario) -> RowID:
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
                    ((ns_id.val, s.val) for s in settings),
                )

            insert_settings("scenario_targets", target_ids)
            insert_settings("scenario_attackers", attacker_ids)

            self.con.execute(
                "INSERT INTO scenario_misc VALUES (?,?,?,?,?,?,?,?)",
                (
                    ns_id.val,
                    scenario._generator_version,
                    scenario._bisector_version,
                    scenario._reducer_version,
                    scenario._instrumenter_version,
                    config.csmith.min_size,
                    config.csmith.max_size,
                    os.path.basename(config.creduce),
                ),
            )
        return ns_id

    def get_new_scenario_id(self, no_commit: bool) -> RowID:
        cur = self.con.cursor()
        cur.execute("INSERT INTO scenarios VALUES (NULL)")
        if not no_commit:
            self.con.commit()
        return RowID(cur.lastrowid)

    def get_scenario_id(self, scenario: Scenario) -> Optional[RowID]:
        def get_scenario_ids(id_: RowID, table: str, id_str: str) -> set[int]:
            cursor = self.con.cursor()
            return set(
                s_id[0]
                for s_id in cursor.execute(
                    f"SELECT scenario_id " f"FROM {table} " f"WHERE {id_str}== ? ",
                    (id_.val,),
                ).fetchall()
            )

        target_ids = []
        for setting in scenario.target_settings:
            if not (s_id := self.get_compiler_setting_id(setting)):
                return None
            target_ids.append(s_id)

        attacker_ids = []
        for setting in scenario.attacker_settings:
            if not (s_id := self.get_compiler_setting_id(setting)):
                return None
            attacker_ids.append(s_id)

        candidate_ids = reduce(
            lambda x, y: x & y,
            (
                get_scenario_ids(target_id, "scenario_targets", "target_id")
                for target_id in target_ids
            ),
        )
        if not candidate_ids:
            return None

        candidate_ids = reduce(
            lambda x, y: x & y,
            chain(
                (
                    get_scenario_ids(attacker_id, "scenario_attackers", "attacker_id")
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
        result = self.con.execute(
            "SELECT compiler_setting_id "
            "FROM compiler_settings "
            "WHERE compiler == ? AND rev == ? AND opt_level == ?  ",
            (
                compiler_setting.compiler_config.name,
                compiler_setting.rev,
                compiler_setting.opt_level,
            ),
        ).fetchone()

        if not result:
            return None
        s_id = RowID(result[0])

        if compiler_setting.additional_flags:
            return (
                s_id
                if set(compiler_setting.additional_flags)
                == set(
                    result[0]
                    for result in self.con.execute(
                        "SELECT flag "
                        "From compiler_settings_additional_flags "
                        "WHERE compiler_setting_id == ?",
                        (s_id.val,),
                    ).fetchall()
                )
                else None
            )
        return s_id
