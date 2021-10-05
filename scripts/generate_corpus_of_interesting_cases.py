#!/usr/bin/env python3

import argparse
import shutil
from pathlib import Path
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed

from tqdm import tqdm

from utils import make_output_dir
from generate_interesting_case import generate_interesting_case


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
    assert shutil.which(
        args['target-cc']
    ), f'{args["target-cc"]} does not exist or it is not executable'
    for cc in args['additional-cc']:
        assert shutil.which(cc), f'{cc} does not exist or it is not executable'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate case with DCE missed opportunity',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--dcei',
                        help='Path to the dcei binary.',
                        default='dcei')
    parser.add_argument('--csmith',
                        help='Path to the CSmith binary.',
                        default='csmith')
    parser.add_argument('--csmith-include-path',
                        help='Path to the CSmith include directory.',
                        required=True)
    parser.add_argument('--ccomp',
                        help='Path to the CompCert binary.',
                        default='ccomp')
    parser.add_argument(
        '--sanity-gcc',
        help='Path to the gcc binary (used for sanity checks).',
        default='gcc')
    parser.add_argument(
        '--sanity-clang',
        help='Path to the clang binary (used for sanity checks).',
        default='clang')
    parser.add_argument('--flags',
                        help='Flags passed to all compilers.',
                        default='')
    parser.add_argument(
        '-m',
        '--markers',
        help='The optimization markers used for differential testing.',
        default='DCEFunc')
    parser.add_argument('--onlyO3',
               default=True,
               action=argparse.BooleanOptionalAction,
               help='Only check for O3 regressions.')
    parser.add_argument('-j',
                        type=int,
                        help='Number of parallel jobs.',
                        default=cpu_count())
    parser.add_argument('target-cc',
                        help='The compiler to test for missed opportunities.')
    parser.add_argument('additional-cc',
                        nargs='*',
                        help='Additional compilers to test against.')
    parser.add_argument('outputdir', help='Output directory')
    parser.add_argument('n',
                        type=int,
                        default=1000,
                        help='Number of cases to generate')

    return parser.parse_args()

if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    make_output_dir(args['outputdir'])
    with ProcessPoolExecutor(args['j']) as p:
        fs = [p.submit(generate_interesting_case, args) for _ in range(args['n'])]
        for i, case_future in enumerate(
                tqdm(as_completed(fs), total=args['n'], dynamic_ncols=True)):
            case = case_future.result()
            with open(
                    Path(args['outputdir']) /
                ('case' + str(i).zfill(len(str(args['n']))) + '.c'), 'w') as f:
                for missed_marker in case.missed_markers:
                    print(f'//{missed_marker.name},{case.bad_compiler}|' +
                          ','.join(map(str, missed_marker.good_compilers)),
                          file=f)
                print(case.code, file=f)
