#!/usr/bin/env python3

import argparse
import shutil
import re
import subprocess
from tempfile import NamedTemporaryFile

from utils import cc_opt_pair_arg, opt_level_arg, get_compiler_name_and_version


def verify_prerequisites(args):
    assert shutil.which(
        args['cc-bad']
    ), f'{args["cc-bad"]} does not exist or it is not executable'
    for cc, opt in args['cc-good']:
        assert opt in ['O1', 'O2', 'Os',
                       'O3'], f'{opt} is not a valid optimization level'
        assert shutil.which(cc), f'{cc} does not exist or it is not executable'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=
        'Check if the marker is not eliminated by the first compiler but is eliminated by the rest',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '--common-flags',
        help='Flags passed to all compilers (including for sanity checks)',
        default='')
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
    parser.add_argument(
        '-m',
        '--markers',
        help='The optimization markers used for differential testing.',
        default='DCEFunc')
    parser.add_argument('file', help='The file to reduce')
    parser.add_argument('missed-marker', help='The missed optimization marker')

    return parser.parse_args()


def check_marker_in_asm(cc, file, flags, marker):
    with NamedTemporaryFile(suffix='.s') as asmf:
        cmd = [cc, file, '-S', f'-o{asmf.name}'] + flags.split()
        cc_name, _ = get_compiler_name_and_version(cc)

        result = subprocess.run(cmd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        assert result.returncode == 0
        with open(asmf.name, 'r') as f:
            #remove the +'\n' hack when the markers are fixed
            text = f.read()
            if marker + '\n' in text:
                return True
            if marker + '@PLT' in text:
                return True
        return False


def check_marker_against_compilers(cc_bad, cc_bad_O, good_compilers,
                                   common_flags, file, missed_marker):
    if not check_marker_in_asm(cc_bad, file, common_flags + f' -{cc_bad_O}',
                               missed_marker):
        return False
    for cc, opt_level in good_compilers:
        if check_marker_in_asm(cc, file, common_flags + f' -{opt_level}',
                               missed_marker):
            return False
    return True


if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    exit(not check_marker_against_compilers(
        args['cc-bad'], args['O'], args['cc-good'], args['common_flags'],
        args['file'], args['missed-marker']))
