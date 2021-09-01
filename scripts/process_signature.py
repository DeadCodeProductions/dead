#!/usr/bin/env python3.9

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from itertools import groupby
from operator import itemgetter
import sys


@dataclass
class MarkerSets:
    dead: set[str]
    alive: set[str]


@dataclass
class OptimizationLevelSignature:
    level: str
    markers: MarkerSets

    def all_markers(self):
        return self.markers.dead & self.markers.alive

    def validate(self):
        assert len(self.all_markers()) == 0

    @staticmethod
    def from_dict(sig_dict):
        return OptimizationLevelSignature(
            sig_dict['level'],
            MarkerSets(set(sig_dict['dead_markers']),
                       set(sig_dict['alive_markers'])))


@dataclass
class CompilerSignature:
    name: str
    version: str
    optimization_levels: list[OptimizationLevelSignature]

    def find_dead(self, markers):
        good_versions = []
        for m in markers:
            for opt_level in self.optimization_levels:
                if m in opt_level.markers.dead:
                    good_versions.append(
                        (m, self.name, self.version, opt_level.level))
        return good_versions


    def get_O3(self):
        for opt_level in self.optimization_levels:
            if opt_level.level=='3':
                return opt_level
        raise RuntimeError(f'Could not find O3 in {name} {version}')

    def filter_optimization_level(self, level):
        return CompilerSignature(
            self.name, self.version,
            [l for l in self.optimization_levels if l.level == level])

    def optimization_levels_with_marker_dead(self, marker):
        levels = []
        for opt_level in self.optimization_levels:
            if marker in opt_level.markers.dead:
                levels.append(opt_level.level)
        return levels

    def dead_markers_at_O3(self):
        for opt_level in self.optimization_levels:
            if opt_level.level == '3':
                return opt_level.markers.dead
        raise RuntimeError('No O3 signature')

    def all_dead_markers(self):
        dead_markers=set()
        for opt in self.optimization_levels:
            dead_markers |= opt.markers.dead
        return dead_markers

    def validate(self):
        levels = set()
        all_marker_sets = []
        for opt_level in self.optimization_levels:
            opt_level.validate()

            assert opt_level.level not in levels
            levels.add(opt_level.level)
            all_marker_sets.append(opt_level.all_markers())

        assert all(ms == all_marker_sets[0] for ms in all_marker_sets)

    @staticmethod
    def from_dict(sig_dict):
        path = Path(sig_dict['CC'])
        cc = path.stem
        version = path.parts[-3].split('-')[1]
        return CompilerSignature(cc, version, [
            OptimizationLevelSignature.from_dict(opt)
            for opt in sig_dict['opt_level']
        ])


@dataclass
class Signature:
    file: str
    compilers: list[CompilerSignature]

    def find_dead(self, markers):
        good_versions=[]
        for cc in self.compilers:
            good_versions.extend(cc.find_dead(markers))
        return good_versions

    def get_target_cc_trunk_O3(self, target_cc):
        for cc in self.get_trunks():
            if cc.name == target_cc:
                return cc.get_O3()
        raise RuntimeError(f'Could not find O3 trunk of {target_cc}')

    def get_trunks(self):
        trunks = []
        for cc in self.compilers:
            if cc.version == 'trunk':
                trunks.append(cc)
        return trunks

    def get_trunk(self):
        trunks = self.get_trunks()
        assert len(trunks) == 1
        return trunks[0]

    def filter_trunk(self):
        return Signature(self.file, get_trunks())

    def filter_compiler(self, cc):
        return Signature(self.file,
                         [comp for comp in self.compilers if comp.name == cc])

    def filter_optimization_level(self, level):
        return Signature(
            self.file,
            [comp.filter_optimization_level(level) for comp in self.compilers])

    def missed_by_trunk_across_all(self):
        missed_markers = []
        dead = self.all_dead_markers()
        for cc in self.compilers:
            if cc.version != 'trunk':
                continue
            dead_O3 = cc.dead_markers_at_O3()
            missed = dead - dead_O3
            for m in missed:
                missed_markers.append((cc.name, m, [
                    (cc_other.name, cc_other.version, opt_level)
                    for cc_other in self.compilers for opt_level in
                    cc_other.optimization_levels_with_marker_dead(m)
                ]))
        return missed_markers

    def all_dead_markers(self):
        dead_markers=set()
        for cc in self.compilers:
            dead_markers |= cc.all_dead_markers()
        return dead_markers

    def validate(self):
        compilers = set()
        for cc in self.compilers:
            assert (cc.name, cc.version) not in compilers
            compilers.add((cc.name, cc.version))
            cc.validate()

    @staticmethod
    def from_dict(sig_dict):
        return Signature(
            sig_dict['file'],
            [CompilerSignature.from_dict(cc) for cc in sig_dict['CCs']])

def filter_latest_version(missed_opportunities):
    select_marker = itemgetter(0)
    select_compiler = itemgetter(1)
    select_version = itemgetter(2)
    select_level = itemgetter(3)
    missed_opportunities = sorted(missed_opportunities, key=select_marker)
    for _, missed_opportunities in groupby(missed_opportunities, key=select_marker):
        missed_opportunities = sorted(missed_opportunities, key=select_compiler)
        for _, missed_opportunities in groupby(missed_opportunities, key=select_compiler):
            level_order={'1':0, '2': 1, 's': 2, '3':3}
            missed_opportunities = sorted(
                missed_opportunities,
                key=lambda x:
                (level_order[select_level(x)], select_version(x)))
            yield(missed_opportunities[-1])

def find_missed_markers(signature, target_cc):
    O3_alive = signature.get_target_cc_trunk_O3(target_cc).markers.alive
    missed = list(filter_latest_version(signature.find_dead(O3_alive)))
    for m in missed:
        print(f'{target_cc} {signature.file} {m[0]} {m[1]} {m[2]} O{m[3]}')

def read_signature(sig_file):
    with open(sig_file, 'r') as f:
        signature = json.load(f)
    sig = Signature.from_dict(signature)
    sig.validate()
    return sig

def parse_arguments():
    parser = argparse.ArgumentParser('Process a signature file.', add_help=True)
    parser.add_argument('signature_file')
    parser.add_argument('--cc', required=True, choices=['gcc', 'clang'])
    parser.add_argument('--across-compilers',
                        default=False,
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('--across-levels',
                        default=False,
                        action=argparse.BooleanOptionalAction)
    parser.add_argument('--across-versions',
                        default=False,
                        action=argparse.BooleanOptionalAction)
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()
    if not any(
        (args.across_compilers, args.across_levels, args.across_versions)):
        print('At least one of --across-compilers, --across-levels,'
              'or --across-versions must be used.')
        sys.exit(1)

    signature = read_signature(args.signature_file)
    if not args.across_compilers:
        signature = signature.filter_compiler(args.cc)
    if not args.across_levels:
        signature = signature.filter_optimization_level('3')
    if not args.across_versions:
        signature = signature.filter_trunk()

    find_missed_markers(signature, args.cc)
