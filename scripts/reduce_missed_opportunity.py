#!/bin/env python3

import argparse
import shutil
import os
import re
import multiprocessing
import subprocess
from pathlib import Path

from check_marker import opt_level_arg, cc_opt_pair_arg
from utils import make_output_dir


def verify_prerequisites(args):
    assert shutil.which(
        args['static_annotator']
    ), 'f["static_annotator"] does not exist or it is not executable (can be specified with --static-annotator)'
    assert shutil.which(
        args['ccc']
    ), 'f["ccc"] does not exist or it is not executable (can be specified with --ccc)'
    assert shutil.which(
        args['creduce']
    ), 'creduce  does not exist or it is not executable (can be specified with --creduce)'
    assert shutil.which(
        args['ccomp']
    ), 'ccomp (CompCert) does not exist or it is not executable (can be specified with --ccomp)'
    assert shutil.which(
        args['sanity_gcc']
    ), 'gcc (used for sanity checks) does not exist or it is not executable (can be specified with --gcc-sanity)'
    assert shutil.which(
        args['sanity_clang']
    ), 'clang (used for sanity checks) does not exist or it is not executable (can be specified with --gcc-sanity)'
    assert shutil.which(
        args['cc-bad']
    ), f'{args["cc-bad"]} does not exist or it is not executable'
    for cc, opt in args['cc-good']:
        assert opt in ['O1', 'O2', 'Os',
                       'O3'], f'{opt} is not a valid optimization level'
        assert shutil.which(cc), f'{cc} does not exist or it is not executable'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Reduces a missed opportunity with the help of creduce')
    parser.add_argument('--creduce',
                        help='Path to the creduce binary.',
                        default='creduce')
    parser.add_argument('--ccomp',
                        help='Path to the CompCert binary.',
                        default='ccomp')
    parser.add_argument(
        '--sanity-gcc',
        help='Path to the gcc binary, only used for sanity checks.',
        default='gcc')
    parser.add_argument(
        '--sanity-clang',
        help='Path to the clang binary, only used for sanity checks.',
        default='clang')
    parser.add_argument(
        '--common-flags',
        help='Flags passed to all compilers (including for sanity checks)',
        default='')
    parser.add_argument(
        '-m',
        '--markers',
        help='The optimization markers used for differential testing.',
        default='DCEFunc')
    parser.add_argument('--static-annotator',
                        help='Path to the static-annotator binary.',
                        required=True)
    parser.add_argument('--ccc',
                        help='Path to the call chain checker binary.',
                        required=True)
    parser.add_argument(
        '--preprocess',
        default=True,
        action=argparse.BooleanOptionalAction,
        help=
        'Preprocess the file before reducing it. Only tested with CSmith files.'
    )
    parser.add_argument('-j',
                        type=int,
                        help='Number of creduce jobs.',
                        default=multiprocessing.cpu_count())
    parser.add_argument(
        'cc-bad', help='Compiler which cannot eliminate the missed marker.')
    parser.add_argument('-O',
                        type=opt_level_arg,
                        help='Optimization level of the first compiler',
                        default='')
    parser.add_argument(
        'cc-good',
        nargs='+',
        type=cc_opt_pair_arg,
        help=
        'Pairs of (compiler, optimization levels) which can eliminate the missed marker.'
    )

    parser.add_argument('file', help='The file to reduce')
    parser.add_argument('missed-marker', help='The missed optimization marker')

    parser.add_argument('outputdir', type=str, help='Output directory')

    return parser.parse_args()


def find_marker_decl_range(lines, markers):
    p = re.compile(f'void {markers}(.*)\(void\);')
    first = 0
    for i, line in enumerate(lines):
        if p.match(line):
            first = i
            break
    for i, line in enumerate(lines[first + 1:], start=first + 1):
        if p.match(line):
            continue
        else:
            last = i
            break
    return first, last


def find_platform_main_end(lines):
    p = re.compile('.*platform_main_end.*')
    for i, line in enumerate(lines):
        if p.match(line):
            return i


def remove_platform_main_begin(lines):
    p = re.compile('.*platform_main_begin.*')
    for line in lines:
        if not p.match(line):
            yield line


def remove_print_hash_value(lines):
    p = re.compile('.*print_hash_value = 1.*')
    for line in lines:
        if not p.match(line):
            yield line


def preprocess_csmith_file(cc, flags, file, markers):
    file = Path(file)
    new_file = file.with_stem(file.stem + '_pp')
    cmd = [cc, file, '-P', '-E'] + flags.split()
    result = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    assert result.returncode == 0
    lines = result.stdout.decode('utf-8').split('\n')
    marker_range = find_marker_decl_range(lines, markers)
    platform_main_end_line = find_platform_main_end(lines)
    marker_decls = lines[marker_range[0]:marker_range[1]]

    lines = lines[platform_main_end_line + 1:]
    lines = remove_print_hash_value(remove_platform_main_begin(lines))
    lines = marker_decls + [
        'typedef unsigned int size_t;', 'typedef signed char int8_t;',
        'typedef short int int16_t;', 'typedef int int32_t;',
        'typedef long long int int64_t;', 'typedef unsigned char uint8_t;',
        'typedef unsigned short int uint16_t;',
        'typedef unsigned int uint32_t;',
        'typedef unsigned long long int uint64_t;',
        'int printf (const char *, ...);',
        'void __assert_fail (const char *__assertion, const char *__file, unsigned int __line, const char *__function);',
        'static void', 'platform_main_end(uint32_t crc, int flag)'
    ] + list(lines)
    with open(str(new_file), 'w') as f:
        print('\n'.join(lines), file=f)
    return new_file

if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    make_output_dir(args['outputdir'])
    cfile = Path(args['outputdir']) / Path(args['file']).name
    shutil.copyfile(args['file'], cfile)
    if args['preprocess']:
        cfile = preprocess_csmith_file(args['cc-bad'], args['common_flags'], cfile, args['markers'])
    script_name = str(
        Path(args['outputdir']) /
        (Path(args['file']).stem + '_' + args['missed-marker'] + '.sh'))
    with open(script_name, 'w') as f:
        print('#/usr/bin/env bash', file=f)
        print('TMPD=$(mktemp -d)', file=f)
        print('trap \'{ rm -rf "$TMPD"; }\' INT TERM EXIT', file=f)
        print(
            f'{Path(__file__).parent.resolve()}/dce_reduction_check.py'
            f' -m {args["markers"]} --common-flags "{args["common_flags"]}"'
            f' --static-annotator {os.path.abspath(args["static_annotator"])}'
            f' --ccc {os.path.abspath(args["ccc"])}'
            f' {args["cc-bad"]} -{args["O"]} ' +
            ' '.join(map(lambda x: ','.join(x), args['cc-good'])) +
            f' {cfile.name} {args["missed-marker"]}',
            file=f)
    os.chmod(script_name, 0o777)
    os.chdir(args['outputdir'])
    subprocess.run(
        ['creduce', '--n',
         str(args["j"]),
         Path(script_name).name, cfile.name])
