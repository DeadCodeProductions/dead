#!/usr/bin/env python3

import argparse
import shutil
import re
import subprocess
from tempfile import NamedTemporaryFile
from sanitize import sanitize


def verify_prerequisites(args):
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
    assert shutil.which(
        args['cc-good']
    ), f'{args["cc-good"]} does not exist or it is not executable'


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
    parser.add_argument(
        'cc-bad', help='Compiler which cannot eliminate the missed marker.')
    parser.add_argument('--cc-bad-flags',
                        help='Flags passed to the bad compiler.',
                        default='')
    parser.add_argument('cc-good',
                        help='Compiler which can eliminate the missed marker.')
    parser.add_argument('--cc-good-flags',
                        help='Flags passed to the good compiler.',
                        default='')
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


def check_marker_in_asm(cc, file, flags, marker):
    with NamedTemporaryFile(suffix='.s') as asmf:
        cmd = [cc, file, '-S', f'-o{asmf.name}'] + flags.split()
        result = subprocess.run(cmd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        assert result.returncode == 0
        with open(asmf.name, 'r') as f:
            #remove the +'\n' hack when the markers are fixed
            if marker+'\n' in f.read():
                return True
        return False


if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    with temporary_file_with_empty_marker_bodies(args['file'],
                                                 args['markers']) as cfile:
        if not sanitize(args['sanity_gcc'], args['sanity_clang'],
                        args['ccomp'], cfile.name, args['common_flags']):
            exit(1)
    if check_marker_in_asm(
            args['cc-bad'], args['file'],
            args['cc_bad_flags'] + ' ' + args['common_flags'],
            args['missed-marker']) and not check_marker_in_asm(
                args['cc-good'], args['file'], args['cc_good_flags'] + ' ' +
                args['common_flags'], args['missed-marker']):
        exit(0)
    exit(1)
