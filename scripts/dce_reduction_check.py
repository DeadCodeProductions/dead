#!/usr/bin/env python3

import argparse
import shutil
import re
import os
import subprocess
from tempfile import NamedTemporaryFile

from sanitize import sanitize
from check_marker import check_marker_against_compilers, opt_level_arg, cc_opt_pair_arg
from utils import find_include_paths

def verify_prerequisites(args):
    assert shutil.which(
        args['static_annotator']
    ), 'f["static_annotator"] does not exist or it is not executable (can be specified with --static-annotator)'
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
        description='Reduction check to use with creduce',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
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
    parser.add_argument('--static-annotator',
                        help='Path to the static-annotator binary.',
                        required=True)
    parser.add_argument(
        'cc-bad', help='Compiler which cannot eliminate the missed marker.')
    parser.add_argument('-O', type=opt_level_arg,
                        help='Optimization level of the first compiler',
                        default='')
    parser.add_argument(
        'cc-good',
        nargs='+',
        type=cc_opt_pair_arg,
        help=
        'Pairs of (compiler, optimization levels) which can eliminate the missed marker.'
    )
    parser.add_argument(
        '-m',
        '--markers',
        help='The optimization markers used for differential testing.',
        default='DCEFunc')
    parser.add_argument('file', help='The file to reduce')
    parser.add_argument('missed-marker', help='The missed optimization marker')

    return parser.parse_args()

def temporary_file_with_empty_marker_bodies(file, marker):
    tf = NamedTemporaryFile(suffix='.c')
    p = re.compile(f'void {marker}(.*)\(void\);')
    with open(file, 'r') as f, open(tf.name, 'w') as new_cfile:
        for line in f.readlines():
            m = p.match(line)
            if m:
                print(f'void {marker}{m.group(1)}(void){{}}', file=new_cfile)
            else:
                print(line, file=new_cfile, end='')
    return tf

def annotate_program_with_static(annotator, file, include_paths):
    cmd = [annotator, file]
    for path in include_paths:
        cmd.append(f'--extra-arg=-isystem{path}')
    result = subprocess.run(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    assert result.returncode == 0

def temporary_file_with_static_globals(annotator, file, include_paths):
    tf = NamedTemporaryFile(suffix='.c')
    with open(file, 'r') as f, open(tf.name, 'w') as new_cfile:
        print(f.read(), file=new_cfile)
    annotate_program_with_static(annotator, tf.name, include_paths)
    return tf

def check_marker_signatures(file, markers):
    p = re.compile(f'void {markers}.*\((.*)\);')
    with open(file, 'r') as f:
        lines = f.readlines()
    for line in lines:
        if m := p.match(line):
            if m.group(1) != 'void':
                return False
    return True

if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    if not check_marker_signatures(args['file'], args['markers']):
        exit(1)
    try:
        include_paths = find_include_paths(args['sanity_clang'], args['file'], args['common_flags'])
        with temporary_file_with_static_globals(args['static_annotator'], args['file'], include_paths) as cfile:
            interesting = check_marker_against_compilers(
                args['cc-bad'], args['O'], args['cc-good'],
                args['common_flags'], cfile.name, args['missed-marker'])
        if not interesting:
            exit(1)
        with temporary_file_with_empty_marker_bodies(args['file'],
                                                     args['markers']) as cfile:
            if not sanitize(args['sanity_gcc'], args['sanity_clang'],
                            args['ccomp'], cfile.name, args['common_flags']):
                exit(1)
        exit(0)
    except subprocess.TimeoutExpired:
        exit(1)
    except AssertionError:
        exit(1)
