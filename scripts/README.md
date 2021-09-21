# Examples


`generate_interesting_case.py` can generate a test case which contains at least one missed marker for a give compiler at `-O3` but eliminated at either `-O1`,`-O2`, or `-Os`; additional compilers which can eliminate can be used, e.g.:

`./generate_interesting_case.py --dcei ~/dce_instrumenter/build/bin/dcei  --csmith-include-path /usr/include/csmith-2.3.0 gcc clang12 clang11 clang10 | tee test_case.c` 

This generates `test_case.c` which contains at least one marker missed by `gcc -O3` and found by `gcc` at lower optimization levels or by `clang10`, `clang11`, or `clang12` at any optimization level.
The first few lines in `test_case.c` contain the missed markers in comments of the form: `MarkerName BadCompiler Optlevel| [GoodCompiler Optlevel]+`, e.g.:

`//DCEFunc1,gcc 11.1.0 O3|clang 12.0.1 O2,clang 12.0.1 Os,clang 12.0.1 O3`

`reduced_missed_opportunity.py` tries to reduce a case for a particular missed marker, e.g.:

`./reduce_missed_opportunity.py --common-flags '-I /usr/include/csmith-2.3.0/' --static-annotator ~/dce_instrumenter/build/bin/dcei gcc -O3 clang,O2 clang,O3 test_case.c DCEFunc1 reduction_output_dir`

`reduction_output_dir` will contain the reduced C file.

### Prerequisites:
- [dce_instrumenter](https://gitlab.inf.ethz.ch/theodort/dce_instrumenter)
- creduce
- csmith
- gcc
- clang
- ccomp (CompCert)
