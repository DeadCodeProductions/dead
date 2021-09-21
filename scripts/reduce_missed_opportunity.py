#!/bin/env python3

import argparse
import shutil
import os
import multiprocessing
from pathlib import Path
import subprocess

from check_marker import opt_level_arg, cc_opt_pair_arg
from utils import make_output_dir

def verify_prerequisites(args):
    assert shutil.which(
        args['static_annotator']
    ), 'f["static_annotator"] does not exist or it is not executable (can be specified with --static-annotator)'
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
    parser = argparse.ArgumentParser(description='Reduces a missed opportunity with the help of creduce')
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
    parser.add_argument('-j',
                            type=int,
                            help='Number of creduce jobs.',
                            default=multiprocessing.cpu_count())
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

    parser.add_argument('file', help='The file to reduce')
    parser.add_argument('missed-marker', help='The missed optimization marker')

    parser.add_argument('outputdir', type=str, help='Output directory')

    return parser.parse_args()


if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    make_output_dir(args['outputdir'])
    script_name=str( Path(args['outputdir']) / (Path(args['file']).stem + '_' + args['missed-marker'] + '.sh'))
    with open(script_name , 'w') as f:
        print('#/usr/bin/env bash', file=f)
        print(f'{Path(__file__).parent.resolve()}/dce_reduction_check.py'
              f' -m {args["markers"]} --common-flags "{args["common_flags"]}"'
              f' --static-annotator {os.path.abspath(args["static_annotator"])}'
              f' {args["cc-bad"]} -{args["O"]} ' +
              ' '.join(map(lambda x: ','.join(x), args['cc-good'])) +
              f' {Path(args["file"]).name} {args["missed-marker"]}',
              file=f)
    os.chmod(script_name, 0o777)
    shutil.copyfile(args['file'], Path(args['outputdir'])/Path(args['file']).name)
    os.chdir(args['outputdir'])
    subprocess.run([
        'creduce', '--n', str(args["j"]),
        Path(script_name).name,
        Path(args['file']).name
    ])
