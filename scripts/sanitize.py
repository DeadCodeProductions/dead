#!/usr/bin/env python3

import argparse
import shutil
import os
import subprocess
from tempfile import NamedTemporaryFile


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


def parse_arguments():
    parser = argparse.ArgumentParser(
        description=
        'Sanitize a file with compiler warning, CompCert and the Undefined Behavior Sanitizer',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--ccomp',
                        help='Path to the CompCert binary.',
                        default='ccomp')
    parser.add_argument('--sanity-gcc',
                        help='Path to the gcc binary.',
                        default='gcc')
    parser.add_argument('--sanity-clang',
                        help='Path to the clang binary.',
                        default='clang')
    parser.add_argument('--flags',
                        help='Flags passed to all compilers',
                        default='')
    parser.add_argument(
        '--cc-timeout',
        help='After how many seconds of compilation time to abort.',
        default=8)
    parser.add_argument(
        '--exe-timeout',
        help='After how many seconds of execution time to abort.',
        default=2)
    parser.add_argument(
        '--compcert-timeout',
        help=
        'After how many seconds of CompCert interpretation tion time to abort.',
        default=16)
    parser.add_argument(
        'file', help='The file to sanitize, must be executable and return 0.')
    return parser.parse_args()


def get_cc_output(cc, file, flags, cc_timeout):
    cmd = [
        cc, file, '-c', '-o/dev/null', '-Wall', '-Wextra', '-Wpedantic', '-O1',
        '-Wno-builtin-declaration-mismatch'
    ]
    if flags:
        cmd.extend(flags.split())
    result = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            timeout=cc_timeout)
    return result.returncode, result.stdout.decode('utf-8')


def check_cc_warnings(cc_output):
    warnings = [
        'conversions than data arguments', 'incompatible redeclaration',
        'ordered comparison between pointer', 'eliding middle term',
        'end of non-void function', 'invalid in C99', 'specifies type',
        'should return a value', 'uninitialized', 'incompatible pointer to',
        'incompatible integer to', 'comparison of distinct pointer types',
        'type specifier missing', 'uninitialized', 'Wimplicit-int',
        'division by zero', 'without a cast', 'control reaches end',
        'return type defaults', 'cast from pointer to integer',
        'useless type name in empty declaration', 'no semicolon at end',
        'type defaults to', 'too few arguments for format',
        'incompatible pointer', 'ordered comparison of pointer with integer',
        'declaration does not declare anything', 'expects type',
        'comparison of distinct pointer types', 'pointer from integer',
        'incompatible implicit', 'excess elements in struct initializer',
        'comparison between pointer and integer',
        'return type of ‘main’ is not ‘int’', 'past the end of the array',
        'no return statement in function returning non-void'
    ]
    for warning in warnings:
        if warning in cc_output:
            return False
    return True


def check_compiler_warnings(clang, gcc, file, flags, cc_timeout):
    def check_cc(cc, file, flags):
        rc, output = get_cc_output(cc, file, flags, cc_timeout)
        if rc != 0:
            return False
        return check_cc_warnings(output)

    return check_cc(clang, file, flags) and check_cc(gcc, file, flags)


def verify_with_ccomp(ccomp, file, flags, compcert_timeout):
    cmd = [
        ccomp,
        file,
        '-interp',
        '-fall',
    ]
    if flags:
        cmd.extend(flags.split())
    result = subprocess.run(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=compcert_timeout)
    return result.returncode == 0


def use_ub_sanitizers(clang, file, flags, cc_timeout, exe_timeout):
    cmd = [clang, file, '-O1', '-fsanitize=undefined,address']
    if flags:
        cmd.extend(flags.split())

    with NamedTemporaryFile(suffix='.exe', delete=False) as exe:
        exe.close()
        os.chmod(exe.name, 0o777)
        cmd.append(f'-o{exe.name}')
        result = subprocess.run(cmd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=cc_timeout)
        if result.returncode != 0:
            if os.path.exists(exe.name):
                os.remove(exe.name)
            return False
        result = subprocess.run(exe.name,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                timeout=exe_timeout)
        os.remove(exe.name)
        if result.returncode != 0:
            return False
        return True


def sanitize(gcc,
             clang,
             ccomp,
             file,
             flags,
             cc_timeout=8,
             exe_timeout=2,
             compcert_timeout=16):
    return all((check_compiler_warnings(gcc, clang, file, flags, cc_timeout),
                use_ub_sanitizers(clang, file, flags, cc_timeout, exe_timeout),
                verify_with_ccomp(ccomp, file, flags, compcert_timeout)))


if __name__ == '__main__':
    args = vars(parse_arguments())
    verify_prerequisites(args)
    exit(not sanitize(args['sanity_gcc'], args['sanity_clang'], args['ccomp'],
                      args['file'], args['flags'], args['cc_timeout'],
                      args['exe_timeout'], args['compcert_timeout']))
