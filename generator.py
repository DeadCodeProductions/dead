#!/usr/bin/env python3

import dataclasses
import logging
import os
import re
import signal
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from multiprocessing import Process, Queue
from os.path import join as pjoin
from random import randint
from tempfile import NamedTemporaryFile
from typing import Optional, Union

from sanitize import sanitize

import builder
import parsers
import patcher
import utils



def run_csmith(csmith):
    tries = 0
    while True:
        options = [
            "arrays",
            "bitfields",
            "checksum",
            "comma-operators",
            "compound-assignment",
            "consts",
            "divs",
            "embedded-assigns",
            "jumps",
            "longlong",
            "force-non-uniform-arrays",
            "math64",
            "muls",
            "packed-struct",
            "paranoid",
            "pointers",
            "structs",
            "inline-function",
            "return-structs",
            "arg-structs",
            "dangling-global-pointers",
        ]

        cmd = [
            csmith, '--no-unions', '--safe-math', '--no-argc', '--no-volatiles',
            '--no-volatile-pointers'
        ]
        for option in options:
            if randint(0, 1):
                cmd.append(f'--{option}')
            else:
                cmd.append(f'--no-{option}')
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)
        if result.returncode == 0:
            return result.stdout.decode('utf-8')
        else:
            tries += 1
            if tries > 10:
                raise Exception("CSmith failed 10 times in a row!")
            

def instrument_program(dcei, file, include_paths):
    cmd = [dcei, file]
    for path in include_paths:
        cmd.append(f'--extra-arg=-isystem{path}')
    result = subprocess.run(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    assert result.returncode == 0
    return "DCEFunc"

def annotate_program_with_static(annotator, file, include_paths):
    cmd = [annotator, file]
    for path in include_paths:
        cmd.append(f'--extra-arg=-isystem{path}')
    result = subprocess.run(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        raise Exception("Static annotator failed to annotate {file}!")

def generate_file(config, additional_flags: str):
    additional_flags += f" -I {config.csmith.include_path}"
    while True:
        try:
            logging.debug("Generating new candidate...")
            candidate = run_csmith(config.csmith.executable)
            if len(candidate) > config.csmith.max_size: continue
            if len(candidate) < config.csmith.min_size: continue
            with NamedTemporaryFile(suffix='.c') as ntf:
                with open(ntf.name, 'w') as f:
                    print(candidate, file=f)
                logging.debug("Checking if program is sane...")
                if not sanitize(config.gcc.sane_version, 
                                config.llvm.sane_version,
                                config.ccomp, 
                                ntf.name, 
                                additional_flags):
                    continue
                include_paths = utils.find_include_paths(config.llvm.sane_version, ntf.name, additional_flags)
                include_paths.append("-I " + config.csmith.include_path)
                logging.debug("Instrumenting candidate...")
                marker_prefix = instrument_program(config.dcei, ntf.name, include_paths)
                with open(ntf.name, 'r') as f:
                    return marker_prefix, f.read()

            return marker_prefix, candidate
        except subprocess.TimeoutExpired:
            pass

@dataclass
class ReduceCase():
    code: str
    marker: str
    bad_setting: utils.CompilerSetting
    good_settings: list[utils.CompilerSetting]

    def __str__(self):
        s = f"//marker::: {self.marker}\n"\
            + f"//bad::: {self.bad_setting}\n"\
            + "//good::: " + "\n//good::: ".join(map(str, self.good_settings))\
            + "\n" + self.code
        return s
    
    @staticmethod
    def from_file(path: os.PathLike, config):
        with open(path, "r") as f:
            marker_line = f.readline()
            bad_line = f.readline()
            good_lines = []
            curr = f.readline() # One good setting must exist
            while curr.startswith("//good:::"):
                good_lines.append(curr)
                curr = f.readline()
            code = "".join([curr] + f.readlines())
        # Extract  
        marker = marker_line.split(":::")[1].strip()
        bad_setting = utils.CompilerSetting.from_str(bad_line.split(":::")[1], config)
        good_settings = [ utils.CompilerSetting.from_str(l.split(":::")[1], config) for l in good_lines ]

        return ReduceCase(code, marker, bad_setting, good_settings)

    @staticmethod
    def from_str(s: str, config):
        sl = s.split("\n")
        marker_line = sl[0]
        bad_line = sl[1]
        i = 2
        while sl[i].startswith("//good:::"):
            i+=1
        good_lines = sl[1:i]
        code = "\n".join(sl[i:])

        # Extract  
        marker = marker_line.split(":::")[1].strip()
        bad_setting = utils.CompilerSetting.from_str(bad_line.split(":::")[1], config)
        good_settings = [ utils.CompilerSetting.from_str(l.split(":::")[1], config) for l in good_lines ]

        return ReduceCase(code, marker, bad_setting, good_settings)


@contextmanager
def compile_context(code: str):
    fd_code, code_file = tempfile.mkstemp(suffix=".c")
    fd_asm, asm_file = tempfile.mkstemp(suffix=".s")

    with open(code_file, "w") as f:
        f.write(code)

    try:
        yield (code_file, asm_file)
    finally:
        os.remove(code_file)
        os.close(fd_code)
        os.remove(asm_file)
        os.close(fd_asm)

def set_of_all_markers(code: str, marker_prefix: str):
    fd_file, file = tempfile.mkstemp(suffix=".c")
    with open(file, "w") as f:
        f.write(code)

    p = re.compile(f'.*{marker_prefix}([0-9]*).*')
    all_markers = set()
    with open(file, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            m = p.match(line)
            if m:
                all_markers.add((f'{marker_prefix}{m.group(1)}'))
    os.remove(file)
    os.close(fd_file)
    return all_markers


class InterestingCaseGenerator():

    def __init__(self, config: utils.NestedNamespace, patchdb, cores: Optional[int]=None):
        self.config = config
        self.patchdb = patchdb
        self.builder = builder.Builder(config, patchdb, cores)


    def find_alive_markers(self, code: str, compiler_setting: utils.CompilerSetting, marker_prefix: str) -> set[str]:
        alive_markers = set()

        # Extract alive markers
        alive_regex = re.compile(f'.*[call|jmp].*{marker_prefix}([0-9]*).*')

        asm = self.get_asm_str(code, compiler_setting)

        for line in asm.split("\n"):
            line = line.strip()
            m = alive_regex.match(line)
            if m:
                alive_markers.add(f'{marker_prefix}{m.group(1)}')

        return alive_markers
    
    def get_asm_str(self, code: str, compiler_setting: utils.CompilerSetting) -> str:
        # Get the assembly output of `code` compiled with `compiler_setting` as str

        compiler_path = self.builder.build(compiler_setting.compiler_config, compiler_setting.rev)
        compiler_exe = pjoin(compiler_path, "bin", compiler_setting.compiler_config.name)

        with compile_context(code) as context_res:
            code_file, asm_file = context_res

            cmd = f"{compiler_exe} -S {code_file} -o{asm_file} -O{compiler_setting.opt_level} -I{self.config.csmith.include_path}"
            utils.run_cmd(cmd)

            with open(asm_file, 'r') as f:
                return f.read()

    
    def is_interesting_wrt_marker(self, case: ReduceCase) -> bool:
        # Checks if the bad_setting does include the marker and 
        # all the good settings do not.

        # TODO: handle hardcoded DCEFunc
        found_in_bad = self.find_alive_markers(case.code, case.bad_setting, "DCEFunc")
        uninteresting = False
        if case.marker not in found_in_bad:
            uninteresting = True
        for good_setting in case.good_settings:
            found_in_good = self.find_alive_markers(case.code, good_setting, "DCEFunc")
            if case.marker in found_in_good:
                uninteresting = True
                break
        return not uninteresting

    def is_interesting_wrt_ccc(self, case: ReduceCase) -> bool:
        # Checks if there is a callchain between main and the marker
        with NamedTemporaryFile(suffix='.c') as tf:
            with open(tf.name, "w") as f:
                f.write(case.code)

            #TODO: Handle include_paths better
            include_paths =  utils.find_include_paths(self.config.llvm.sane_version, tf.name, 
                                                      f"-I{self.config.csmith.include_path}")
            cmd = [ self.config.ccc, tf.name, '--from=main', f'--to={case.marker}']

            for path in include_paths:
                cmd.append(f'--extra-arg=-isystem{path}')
            result = subprocess.run(cmd,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL,
                                    timeout=8)
            if result.returncode != 0:
                logging.debug("CCC failed")
                return False
            output=result.stdout.decode('utf-8')
            return f'call chain exists between main -> {case.marker}'.strip() == output.strip()

    def is_interesting_with_static_globals(self, case: ReduceCase) -> bool:
        # TODO: Why do we do this?

        with NamedTemporaryFile(suffix='.c') as tf:
            with open(tf.name, 'w') as new_cfile:
                print(case.code, file=new_cfile)

            #TODO: Handle include_paths better
            include_paths =  utils.find_include_paths(self.config.llvm.sane_version, tf.name, 
                                                      f"-I{self.config.csmith.include_path}")
            annotate_program_with_static(self.config.static_annotator, tf.name, include_paths)

            with open(tf.name, "r") as annotated_file:
                static_code = annotated_file.read()

            asm_bad = self.get_asm_str(static_code, case.bad_setting)
            uninteresting = False
            if case.marker not in asm_bad:
                uninteresting = True
            for good_setting in case.good_settings:
                asm_good = self.get_asm_str(static_code, good_setting)
                if case.marker in asm_good:
                    uninteresting = True
                    break
            return not uninteresting

                
    def is_interesting_with_empty_marker_bodies(self, case: ReduceCase):
        #TODO: find way for hardcoded marker_prefix DCEFunc
        marker_prefix = "DCEFunc"
        p = re.compile(f'void {marker_prefix}(.*)\(void\);')
        empty_body_code = ""
        for line in case.code.split("\n"):
            m = p.match(line)
            if m:
                empty_body_code += f"\nvoid {marker_prefix}{m.group(1)}(void){{}}"
            else:
                empty_body_code += f"\n{line}"

        with NamedTemporaryFile(suffix='.c') as tf:
            with open(tf.name, 'w') as f:
                f.write(empty_body_code)
        
            return sanitize(self.config.gcc.sane_version, 
                            self.config.llvm.sane_version,
                            self.config.ccomp,
                            tf.name,
                            f"-I{self.config.csmith.include_path}"
                        )


    def is_interesting(self, case: ReduceCase):
        # TODO: Optimization potential. Less calls to clang etc.
        # when tests are combined.
        res = ( self.is_interesting_wrt_marker(case),
                self.is_interesting_wrt_ccc(case),
                self.is_interesting_with_static_globals(case),
                self.is_interesting_with_empty_marker_bodies(case))
        
        logging.debug(f"is_interesting test: {res}")
        return all(res)

    def generate_interesting_case(self, 
                                  target_compiler: utils.CompilerSetting,
                                  target_opt_levels: list[str],
                                  additional_compiler: list[utils.CompilerSetting]):

        all_opt_levels = ['1', '2', 's', '3']

        target_tests = []
        for opt in target_opt_levels:
            cp = dataclasses.replace(target_compiler)
            cp.opt_level = opt
            target_tests.append(cp)

        tests = []
        for opt in all_opt_levels:
            for setting in additional_compiler + [ target_compiler ]:
                cp = dataclasses.replace(setting)
                cp.opt_level = opt
                tests.append(cp)

        try_counter = 0
        while True:
            logging.debug("Generating new candidate...")
            marker_prefix, candidate_code = generate_file(self.config, "")

            # Find alive markers
            logging.debug("Getting alive markers...")
            target_alive_marker_list = [ (tt, self.find_alive_markers(candidate_code, tt, marker_prefix))
                                     for tt in target_tests ]

            tester_alive_marker_list = [ (tt, self.find_alive_markers(candidate_code, tt, marker_prefix))
                                     for tt in tests ]

            target_alive_markers = set()
            for _, marker_set in target_alive_marker_list:
                target_alive_markers.update(marker_set)

            # Extract reduce cases
            logging.debug("Extracting reduce cases...")
            for marker in target_alive_markers:
                good = []
                for good_setting, good_alive_markers in tester_alive_marker_list:
                    if marker not in good_alive_markers: # i.e. the setting eliminated the call
                        good.append(good_setting)

                # Find bad cases
                if len(good) > 0:
                    for bad_setting, bad_alive_markers in target_alive_marker_list:
                        if marker in bad_alive_markers: # i.e. the setting didn't eliminate the call
                            # Create reduce case
                            case = ReduceCase(code=candidate_code,
                                              marker=marker,
                                              bad_setting=bad_setting,
                                              good_settings=good)
                            if self.is_interesting(case):
                                logging.info(f"Try {try_counter}: Found case! LENGTH: {len(candidate_code)}")
                                return case
            else:
                logging.info(f"Try {try_counter}: Found no case. Onto the next one!")
                try_counter += 1

    def _wrapper_interesting(self, 
                                  queue: Queue,
                                  target_compiler: utils.CompilerSetting,
                                  target_opt_levels: list[str],
                                  additional_compiler: list[utils.CompilerSetting]
                                ):
        logging.info("Starting worker...")
        while True:
            case = self.generate_interesting_case(target_compiler, target_opt_levels, additional_compiler)
            queue.put(str(case))

    
    def parallel_interesting_case(self,
                                  target_compiler: utils.CompilerSetting,
                                  target_opt_levels: list[str],
                                  additional_compiler: list[utils.CompilerSetting],
                                  processes: int,
                                  output_dir: os.PathLike,
                                  start_stop: Optional[bool]=False):
        queue = Queue()

        # Create processes
        procs = [ Process(target=self._wrapper_interesting, args=(queue, target_compiler, target_opt_levels, additional_compiler)) for _ in range(processes)]

        # Start processes
        for p in procs:
            p.daemon = True
            p.start()
        
        # read queue
        counter = 0
        while True:
            # TODO: handle process failure
            case: str = queue.get()

            h = hash(case)
            h = max(h, -h)
            path = pjoin(output_dir, f"case_{counter:08}-{h:019}.c")
            with open(path, "w") as f:
                logging.debug("Writing case to {path}...")
                f.write(case)
                f.flush()

            counter += 1
            if start_stop:
                # Send processes to "sleep"
                logging.debug("Stopping workers...")
                for p in procs:
                    if p.pid is None:
                        continue
                    os.kill(p.pid, signal.SIGSTOP)
            yield path 
            if start_stop:
                logging.debug("Restarting workers...")
                # Awake processes again for further search
                for p in procs:
                    if p.pid is None:
                        continue
                    os.kill(p.pid, signal.SIGCONT)


if __name__ == '__main__':
    config, args = utils.get_config_and_parser(parsers.generator_parser())

    cores = None if args.cores is None else args.cores

    patchdb = patcher.PatchDB(config.patchdb)
    case_generator = InterestingCaseGenerator(config, patchdb, cores)

    if args.interesting:
        if args.target is None:
            print("--target is required for --interesting")
            exit(1)
        else:
            compiler = args.target[0]
            if compiler == "gcc":
                compiler_config = config.gcc
            elif compiler == "llvm" or compiler == "clang":
                compiler_config = config.llvm
            else:
                print(f"Unknown compiler project {compiler}")
                exit(1)
            # Use full hash to avoid ambiguity
            repo = patcher.Repo(compiler_config.repo, compiler_config.main_branch)
            rev = repo.rev_to_commit(args.target[1])
            target_setting = utils.CompilerSetting(compiler_config, rev)


        additional_compiler = []
        if args.additional_compiler is not None:
            len_addcomp = len(args.additional_compiler)
            if  len_addcomp % 2 == 1:
                print(f"Odd number of arguments for --additional-compiler; must be of form [PROJECT REV]*")
                exit(1)
            else:
                for i in range(0, len_addcomp, 2):
                    compiler = args.additional_compiler[i]
                    if compiler == "gcc":
                        compiler_config = config.gcc
                    elif compiler == "llvm" or compiler == "clang":
                        compiler_config = config.llvm
                    else:
                        print(f"Unknown compiler project {compiler}")
                        exit(1)
                    # Use full hash to avoid ambiguity
                    repo = patcher.Repo(compiler_config.repo, compiler_config.main_branch)
                    rev = repo.rev_to_commit(args.additional_compiler[i+1])
                    setting = utils.CompilerSetting(compiler_config, rev)
                    additional_compiler.append(setting)

        target_opt_levels = args.target_opt_levels 

        if args.output_directory is None:
            print("Missing output directory!")
            exit(1)
        else:
            output_dir = os.path.abspath(args.output_directory)
            os.makedirs(output_dir, exist_ok=True)

        if args.parallel is not None:
            amount_cases = args.amount if args.amount is not None else 0
            amount_processes = max(1, args.parallel)
            gen = case_generator.parallel_interesting_case(target_compiler=target_setting, 
                                                     target_opt_levels=target_opt_levels,
                                                     additional_compiler=additional_compiler,
                                                     processes=amount_processes,
                                                     output_dir=output_dir,
                                                     start_stop=False)
            for i in range(amount_cases):
                print(next(gen))
        else:
            case_generator.generate_interesting_case(target_compiler=target_setting, 
                                                     target_opt_levels=target_opt_levels,
                                                     additional_compiler=additional_compiler)
