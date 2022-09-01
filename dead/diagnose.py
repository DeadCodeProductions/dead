# we need some kind of sanitization report from 
# diopter.sanitizer to simplify this
def diagnose_case() -> None:
    print("Diagnose is currently broken")
    exit(0)
    # width = 50

    # def ok_fail(b: bool) -> str:
        # if b:
            # return "OK"
        # else:
            # return "FAIL"

    # def nice_print(name: str, value: str) -> None:
        # print(("{:.<" f"{width}}}").format(name), value)

    # if args.case_id:
        # case = ddb.get_case_from_id_or_die(args.case_id)
    # else:
        # case = utils.Case.from_file(config, Path(args.file))

    # repo = case.bad_setting.repo

    # if args.targets or args.additional_compilers:
        # if not args.targets_default_opt_levels:
            # args.targets_default_opt_levels = [case.bad_setting.opt_level]
        # if not args.additional_compilers_default_opt_levels:
            # args.additional_compilers_default_opt_levels = [case.bad_setting.opt_level]

        # scenario = utils.get_scenario(config, args)

        # if scenario.target_settings:
            # scenario.target_settings[
                # 0
            # ].additional_flags = case.bad_setting.additional_flags
            # case.bad_setting = scenario.target_settings[0]
        # if scenario.attacker_settings:
            # for gs in scenario.attacker_settings:
                # gs.additional_flags = case.good_settings[0].additional_flags
            # case.good_settings = scenario.attacker_settings

    # # Replace

    # def sanitize_values(
        # config: utils.NestedNamespace,
        # case: utils.Case,
        # prefix: str,
        # chkr: checker.Checker,
    # ) -> None:
        # empty_body_code = chkr._emtpy_marker_code_str(case)
        # with tempfile.NamedTemporaryFile(suffix=".c") as tf:
            # with open(tf.name, "w") as f:
                # f.write(empty_body_code)
                # res_comp_warnings = checker.check_compiler_warnings(
                    # config.gcc.sane_version,
                    # config.llvm.sane_version,
                    # Path(tf.name),
                    # case.bad_setting.get_flag_str(),
                    # 10,
                # )
                # nice_print(
                    # prefix + "Sanity: compiler warnings",
                    # ok_fail(res_comp_warnings),
                # )
                # res_use_ub_san = checker.use_ub_sanitizers(
                    # config.llvm.sane_version,
                    # Path(tf.name),
                    # case.bad_setting.get_flag_str(),
                    # 10,
                    # 10,
                # )
                # nice_print(
                    # prefix + "Sanity: undefined behaviour", ok_fail(res_use_ub_san)
                # )
                # res_ccomp = checker.verify_with_ccomp(
                    # config.ccomp,
                    # Path(tf.name),
                    # case.bad_setting.get_flag_str(),
                    # 10,
                # )
                # nice_print(
                    # prefix + "Sanity: ccomp",
                    # ok_fail(res_ccomp),
                # )

    # def checks(case: utils.Case, prefix: str) -> None:
        # nice_print(
            # prefix + "Check marker", ok_fail(chkr.is_interesting_wrt_marker(case))
        # )
        # nice_print(prefix + "Check CCC", ok_fail(chkr.is_interesting_wrt_ccc(case)))
        # nice_print(
            # prefix + "Check static. annotated",
            # ok_fail(chkr.is_interesting_with_static_globals(case)),
        # )
        # res_empty = chkr.is_interesting_with_empty_marker_bodies(case)
        # nice_print(prefix + "Check empty bodies", ok_fail(res_empty))
        # if not res_empty:
            # sanitize_values(config, case, prefix, chkr)

    # print(("{:=^" f"{width}}}").format(" Values "))

    # nice_print("Marker", case.marker)
    # nice_print("Code lenght", str(len(case.code)))
    # nice_print("Bad Setting", str(case.bad_setting))
    # same_opt = [
        # gs for gs in case.good_settings if gs.opt_level == case.bad_setting.opt_level
    # ]
    # nice_print(
        # "Newest Good Setting",
        # str(utils.get_latest_compiler_setting_from_list(repo, same_opt)),
    # )

    # checks(case, "")
    # cpy = copy.deepcopy(case)
    # if not (
        # code_pp := preprocessing.preprocess_csmith_code(
            # case.code, utils.get_marker_prefix(case.marker), case.bad_setting, bldr
        # )
    # ):
        # print("Code could not be preprocessed. Skipping perprocessed checks")
    # else:
        # cpy.code = code_pp
        # checks(cpy, "PP: ")

    # if case.reduced_code:
        # cpy = copy.deepcopy(case)
        # cpy.code = case.reduced_code
        # checks(cpy, "Reduced: ")

    # if args.case_id:
        # massaged_code, _, _ = ddb.get_report_info_from_id(args.case_id)
        # if massaged_code:
            # cpy.code = massaged_code
            # checks(cpy, "Massaged: ")

    # if case.bisection:
        # cpy = copy.deepcopy(case)
        # nice_print("Bisection", case.bisection)
        # cpy.bad_setting.rev = case.bisection
        # prev_rev = repo.rev_to_commit(case.bisection + "~")
        # nice_print("Bisection prev commit", prev_rev)
        # bis_res_og = chkr.is_interesting(cpy, preprocess=False)
        # cpy.bad_setting.rev = prev_rev
        # bis_prev_res_og = chkr.is_interesting(cpy, preprocess=False)

        # nice_print(
            # "Bisection test original code", ok_fail(bis_res_og and not bis_prev_res_og)
        # )
        # cpy = copy.deepcopy(case)
        # if cpy.reduced_code:
            # cpy.code = cpy.reduced_code
            # cpy.bad_setting.rev = case.bisection
            # bis_res = chkr.is_interesting(cpy, preprocess=False)
            # cpy.bad_setting.rev = prev_rev
            # bis_prev_res = chkr.is_interesting(cpy, preprocess=False)
            # nice_print(
                # "Bisection test reduced code", ok_fail(bis_res and not bis_prev_res)
            # )

    # if case.reduced_code:
        # print(case.reduced_code)

