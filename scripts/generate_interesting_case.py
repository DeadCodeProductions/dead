#!/usr/bin/env python3

import argparse
import shutil
import os
from sys import stderr
from tempfile import NamedTemporaryFile
from contextlib import contextmanager
from dataclasses import dataclass

from generate_case import generate_file
from find_missed_opportunities import compute_signature, find_missed, get_compiler_name_and_version


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
    parser.add_argument('target-cc',
                        help='The compiler to test for missed opportunities.')
    parser.add_argument('additional-cc',
                        nargs='*',
                        help='Additional compilers to test against.')
    return parser.parse_args()


@contextmanager
def temporary_file(contents):
    ntf = NamedTemporaryFile(suffix='.c', mode='w', delete=False)
    print(contents, file=ntf)
    ntf.close()
    try:
        yield ntf
    finally:
        ntf.close()
        if os.path.exists(ntf.name):
            os.remove(ntf.name)


@dataclass
class CompilerInfo:
    name: str
    version: str
    optimization_level: str

    def __str__(self):
        return f'{self.name} {self.version} O{self.optimization_level}'

@dataclass
class MissedMarker:
    name: str
    good_compilers: list[CompilerInfo]


@dataclass
class CaseWithMissedDCE:
    code: str
    bad_compiler: CompilerInfo
    missed_markers: list[MissedMarker]


def generate_interesting_case(args):
    #TODO: add this csmith path flag to all scripts and drop this
    args['flags'] += f' -I {args["csmith_include_path"]}'
    target_name, target_version = get_compiler_name_and_version(
        args['target-cc'])
    while True:
        candidate = generate_file(args)
        with temporary_file(candidate) as f:
            signature = compute_signature([args['target-cc']] +
                                          args['additional-cc'], args['flags'],
                                          f.name, args['markers'])
            missed_by, found_by = find_missed(signature)

            markers_missed_by_target = [
                marker for marker, compilers in missed_by.items()
                for cc in compilers if cc == (target_name, target_version, '3')
            ]
            if markers_missed_by_target:
                return CaseWithMissedDCE(
                    candidate, CompilerInfo(target_name, target_version, '3'),
                    [
                        MissedMarker(
                            marker,
                            [CompilerInfo(*cc) for cc in found_by[marker]])
                        for marker in markers_missed_by_target
                    ])
            print('Discarding candidate.', file=stderr)


if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    case = generate_interesting_case(args)
    for missed_marker in case.missed_markers:
        print(f'//{missed_marker.name},{case.bad_compiler}|' +
              ','.join(map(str, missed_marker.good_compilers)))
    print(case.code)
