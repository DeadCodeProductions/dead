import argparse
import subprocess
from pathlib import Path


def make_output_dir(path):
    path = Path(path)
    assert not path.exists(), f'{path} already exists'
    try:
        path.mkdir()
    except:
        assert False, f'Could not create {path}'


def cc_opt_pair_arg(s):
    s = s.split(',')
    if len(s) != 2:
        raise argparse.ArgumentTypeError(
            f'{s} should contain exactly one comma')
    return s[0], s[1]


def opt_level_arg(s):
    if s not in ['1', '2', 's', '3']:
        raise argparse.ArgumentTypeError(
            f'O{opt} is not a valid optimization level')
    return 'O' + s

def get_compiler_name_and_version(compiler):
    result = subprocess.run([compiler, '--version'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    assert result.returncode == 0
    line = result.stdout.decode('utf-8').split('\n')[0].split()
    return line[0], line[2]

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
