#!/usr/bin/env python

import argparse
import shutil
import re
import os
import subprocess
from tempfile import NamedTemporaryFile
from collections import defaultdict

from process_signature import MarkerSets, OptimizationLevelSignature, CompilerSignature, Signature
from utils import get_compiler_name_and_version


def verify_prerequisites(args):
    for cc in args['cc']:
        assert shutil.which(cc), f'{cc} does not exist or it is not executable'


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Find missed DCE opportunities in the given file and compilers',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-m',
        '--markers',
        help='The optimization markers used for differential testing.',
        default='DCEFunc')
    parser.add_argument('--flags',
                        help='Flags passed to all compilers',
                        default='')
    parser.add_argument('cc', help='Compilers to use.', nargs='+')
    parser.add_argument('file', help='The file to reduce')

    return parser.parse_args()


def set_of_all_markers(file, marker_prefix):
    p = re.compile(f'.*{marker_prefix}([0-9]*).*')
    all_markers = set()
    with open(file, 'r') as f:
        for line in f.readlines():
            line = line.strip()
            m = p.match(line)
            if m:
                all_markers.add((f'{marker_prefix}{m.group(1)}'))
    return all_markers


def set_of_alive_markers(compiler, flags, file, marker_prefix):
    p = re.compile(f'.*[call|jmp].*{marker_prefix}([0-9]*).*')
    alive_markers=set()
    with NamedTemporaryFile(suffix='.s', delete=False) as asm:
        asm.close()
        cmd = [compiler, '-S', file, f'-o{asm.name}'] + flags.split()
        result = subprocess.run(cmd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=8)
        assert result.returncode == 0
        with open(asm.name, 'r') as f:
            for line in f.readlines():
                line = line.strip()
                m = p.match(line)
                if m:
                    alive_markers.add(f'DCEFunc{m.group(1)}')
        os.remove(asm.name)
        return alive_markers


def get_marker_set(compiler, flags, file, marker_prefix):
    all_markers = set_of_all_markers(file, marker_prefix)
    alive_markers = set_of_alive_markers(compiler, flags, file, marker_prefix)
    return MarkerSets(all_markers - alive_markers, alive_markers)



def compute_signature(compilers, flags, file, marker_prefix):
    levels = ['1', '2', 's', '3']
    return Signature(file, [
        CompilerSignature(*get_compiler_name_and_version(cc), [
            OptimizationLevelSignature(
                level,
                get_marker_set(cc, flags + f' -O{level}', file, marker_prefix))
            for level in levels
        ]) for cc in compilers
    ])

def find_missed(signature):
    dead_markers = signature.all_dead_markers()
    found_by=defaultdict(list)
    missed_by=defaultdict(list)
    for cc in signature.compilers:
        for level in cc.optimization_levels:
            for marker in dead_markers:
                if marker in level.markers.dead:
                    found_by[marker].append((cc.name, cc.version, level.level))
                else:
                    assert marker in level.markers.alive
                    missed_by[marker].append((cc.name, cc.version, level.level))
    return missed_by, found_by


if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    signature = compute_signature(args['cc'], args['flags'], args['file'],
                                  args['markers'])
    missed_by, found_by, = find_missed(signature)
    for marker in missed_by.keys():
        for cc_bad, version_bad, level_bad in missed_by[marker]:
            print(f'{marker} {cc_bad} {version_bad} O{level_bad}', end='')
            print('|' + ','.join(
                map(lambda x: x[0] + ' ' + x[1] + ' O' + x[2],
                    found_by[marker])))
