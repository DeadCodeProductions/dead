#!/usr/bin/env python3

import argparse
import shutil
import subprocess
from sanitize import sanitize
from random import randint
from tempfile import NamedTemporaryFile

def verify_prerequisites(args):
    assert shutil.which(
        args['dcei']
    ), 'dcei (DCE Instrumenter) does not exist or it is not executable (can be specified with --dcei)'
    assert shutil.which(
        args['csmith']
    ), 'csmith does not exist or it is not executable (can be specified with --csmith)'
    assert shutil.which(
        args['ccomp']
    ), 'ccomp (CompCert) does not exist or it is not executable (can be specified with --ccomp)'
    assert shutil.which(
        args['sanity_gcc']
    ), 'gcc (used for sanity checks) does not exist or it is not executable (can be specified with --gcc-sanity)'
    assert shutil.which(
        args['sanity_clang']
    ), 'clang (used for sanity checks) does not exist or it is not executable (can be specified with --gcc-sanity)'

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate a file with csmith for use in DCE testing',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--dcei',
                        help='Path to the dcei binary.',
                        default='dcei')
    parser.add_argument('--csmith',
                        help='Path to the CSmith binary.',
                        default='csmith')
    parser.add_argument('--ccomp',
                        help='Path to the CompCert binary.',
                        default='ccomp')
    parser.add_argument('--sanity-gcc',
                        help='Path to the gcc binary.',
                        default='gcc')
    parser.add_argument('--sanity-clang',
                        help='Path to the clang binary.',
                        default='clang')
    parser.add_argument('--flags',
                        help='Flags passed to all compilers'
                        ' (the csmith include path should be specified here)',
                        default='')
    return parser.parse_args()


def run_csmith(csmith):
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
    assert result.returncode == 0
    return result.stdout.decode('utf-8')


def find_include_paths(clang, file, flags):
    cmd = [clang, file, '-c', '-o/dev/null', '-v']
    if flags:
        cmd.extend(flags.split())
    result = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    assert result.returncode == 0
    output = result.stdout.decode('utf-8').split('\n')
    start = next(i for i, line in enumerate(output)
                 if '#include <...> search starts here:' in line) + 1
    end = next(i for i, line in enumerate(output) if 'End of search list.' in line)
    return [output[i].strip() for i in range(start, end)]


def instrument_program(dcei, file, include_paths):
    cmd = [dcei, file]
    for path in include_paths:
        cmd.append(f'--extra-arg=-isystem{path}')
    result = subprocess.run(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    assert result.returncode == 0

def generate_file(args):
    while True:
        try:
            candidate = run_csmith(args['csmith'])
            if len(candidate) > 1000000: continue
            if len(candidate) < 100000: continue
            with NamedTemporaryFile(suffix='.c') as ntf:
                with open(ntf.name, 'w') as f:
                    print(candidate, file=f)
                if not sanitize(args['sanity_gcc'], args['sanity_clang'],
                                args['ccomp'], ntf.name, args['flags']):
                    continue
                include_paths = find_include_paths(args['sanity_clang'], ntf.name, args['flags'])
                instrument_program(args['dcei'], ntf.name, include_paths)
                with open(ntf.name, 'r') as f:
                    return f.read()

            return candidate
        except subprocess.TimeoutExpired:
            pass

if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    print(generate_file(args))
