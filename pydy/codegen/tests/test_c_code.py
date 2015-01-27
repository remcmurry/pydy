#!/usr/bin/env python
"""
Write a C file plus header to evaluate one or more matrices/vectors.

needs to optionally cse all the items

Mass matrix + forcing: a matrix and vector of expressions

rhs: vector of expressions

Mass matrix + forcing + output vector

rhs + output vector

kinematic equation vector

"""
import os

import sympy as sm
from nose.tools import assert_raises

from ...models import multi_mass_spring_damper
from ..c_code import CMatrixGenerator


class TestCMatrixGenerator():

    def setup(self):

        self.prefix = 'boogly_bee'

        sys = multi_mass_spring_damper(6, True, True)

        self.matrices = (sys.eom_method.mass_matrix,
                         sys.eom_method.forcing)

        self.arguments = (sys.constants_symbols,
                          sys.coordinates,
                          sys.speeds,
                          sys.specifieds_symbols)

        self.generator = CMatrixGenerator(self.matrices, self.arguments)

    def test_init(self):

        assert self.generator.matrices == self.matrices
        assert self.generator.arguments == self.arguments

        # Make sure an error is risen if not enough arguments are provided.
        arguments = self.arguments[:-1]

        assert_raises(ValueError, CMatrixGenerator, self.matrices, arguments)

    def test_generate_cse(self):

        pd = sm.symbols('pydy_:13')

        (c1, c2, k5, m1, k0, c3, c5, k1, c4, m4, k2, k3, m5, m2, m3, k4, c0,
         g, m0) = self.arguments[0]
        x0, x1, x2, x3, x4, x5 = self.arguments[1]
        v0, v1, v2, v3, v4, v5 = self.arguments[2]
        f5, f2, f3, f0, f4, f1 = self.arguments[3]

        expected_subexprs = [
            (pd[0], m4 + m5),
            (pd[1], m3 + pd[0]),
            (pd[2], m2 + pd[1]),
            (pd[3], m1 + pd[2]),
            (pd[4], f2),
            (pd[5], f3),
            (pd[6], f4),
            (pd[7], f5),
            (pd[8], g*m2),
            (pd[9], g*m3),
            (pd[10], g*m4),
            (pd[11], g*m5),
            (pd[12], (g*m1 + pd[10] + pd[11] + pd[4] + pd[5] + pd[6] + pd[7]
                      + pd[8] + pd[9] + f1))]

        expected_simplified_matrices = (
            sm.Matrix([[m0 + pd[3], pd[3], pd[2], pd[1], pd[0], m5],
                       [pd[3],      pd[3], pd[2], pd[1], pd[0], m5],
                       [pd[2],      pd[2], pd[2], pd[1], pd[0], m5],
                       [pd[1],      pd[1], pd[1], pd[1], pd[0], m5],
                       [pd[0],      pd[0], pd[0], pd[0], pd[0], m5],
                       [m5,         m5,    m5,    m5,    m5,    m5]]),
            sm.Matrix([-c0*v0 + g*m0 - k0*x0 + pd[12] + f0,
                       -c1*v1 - k1*x1 + pd[12],
                       -c2*v2 - k2*x2 + pd[10] + pd[11] + pd[4] + pd[5] +
                           pd[6] + pd[7] + pd[8] + pd[9],
                       -c3*v3 - k3*x3 + pd[10] + pd[11] + pd[5] + pd[6] +
                           pd[7] + pd[9],
                       -c4*v4 - k4*x4 + pd[10] + pd[11] + pd[6] + pd[7],
                       -c5*v5 - k5*x5 + pd[11] + pd[7]]))

        self.generator._generate_cse()

        assert self.generator.subexprs == expected_subexprs
        assert self.generator.simplified_matrices == expected_simplified_matrices

    def test_generate_pydy_c_printer(self):

        PyDyCCodePrinter = self.generator._generate_pydy_c_printer()

        printer = PyDyCCodePrinter()

        assert printer.doprint(self.arguments[0][3]) == 'input_0[3]'
        assert printer.doprint(self.arguments[1][5]) == 'input_1[5]'
        assert printer.doprint(self.arguments[2][1]) == 'input_2[1]'
        assert printer.doprint(self.arguments[3][2]) == 'input_3[2]'

    def test_generate_comma_lists(self):

        expected = (('c1, c2, k5, m1, k0, c3, c5, k1, c4, m4, k2, k3, m5, '
                     'm2, m3, k4, c0, g, m0'),
                    'x0(t), x1(t), x2(t), x3(t), x4(t), x5(t)',
                    'v0(t), v1(t), v2(t), v3(t), v4(t), v5(t)',
                    'f5(t), f2(t), f3(t), f0(t), f4(t), f1(t)')

        assert self.generator.comma_lists() == expected

    def test_generate_code_blocks(self):

        expected = {}

        expected['input_args'] = \
"""\
              double input_0[19],
              double input_1[6],
              double input_2[6],
              double input_3[6],\
"""

        expected['output_args'] = \
"""\
              double output_0[36],
              double output_1[6]\
"""

        expected['input_docstring'] = \
"""\
input_0[19] : [c1, c2, k5, m1, k0, c3, c5, k1, c4, m4, k2, k3, m5, m2, m3, k4,
c0, g, m0]
input_1[6] : [x0(t), x1(t), x2(t), x3(t), x4(t), x5(t)]
input_2[6] : [v0(t), v1(t), v2(t), v3(t), v4(t), v5(t)]
input_3[6] : [f5(t), f2(t), f3(t), f0(t), f4(t), f1(t)]\
"""

        expected['subexprs'] = \
"""\
    double pydy_0 = input_0[9] + input_0[12];
    double pydy_1 = input_0[14] + pydy_0;
    double pydy_2 = input_0[13] + pydy_1;
    double pydy_3 = input_0[3] + pydy_2;
    double pydy_4 = input_3[1];
    double pydy_5 = input_3[2];
    double pydy_6 = input_3[4];
    double pydy_7 = input_3[0];
    double pydy_8 = input_0[17]*input_0[13];
    double pydy_9 = input_0[17]*input_0[14];
    double pydy_10 = input_0[17]*input_0[9];
    double pydy_11 = input_0[17]*input_0[12];
    double pydy_12 = input_0[17]*input_0[3] + pydy_10 + pydy_11 + pydy_4 +
    pydy_5 + pydy_6 + pydy_7 + pydy_8 + pydy_9 + input_3[5];\
"""

        expected['outputs'] = \
"""\
    output_0[0] = input_0[18] + pydy_3;
    output_0[1] = pydy_3;
    output_0[2] = pydy_2;
    output_0[3] = pydy_1;
    output_0[4] = pydy_0;
    output_0[5] = input_0[12];
    output_0[6] = pydy_3;
    output_0[7] = pydy_3;
    output_0[8] = pydy_2;
    output_0[9] = pydy_1;
    output_0[10] = pydy_0;
    output_0[11] = input_0[12];
    output_0[12] = pydy_2;
    output_0[13] = pydy_2;
    output_0[14] = pydy_2;
    output_0[15] = pydy_1;
    output_0[16] = pydy_0;
    output_0[17] = input_0[12];
    output_0[18] = pydy_1;
    output_0[19] = pydy_1;
    output_0[20] = pydy_1;
    output_0[21] = pydy_1;
    output_0[22] = pydy_0;
    output_0[23] = input_0[12];
    output_0[24] = pydy_0;
    output_0[25] = pydy_0;
    output_0[26] = pydy_0;
    output_0[27] = pydy_0;
    output_0[28] = pydy_0;
    output_0[29] = input_0[12];
    output_0[30] = input_0[12];
    output_0[31] = input_0[12];
    output_0[32] = input_0[12];
    output_0[33] = input_0[12];
    output_0[34] = input_0[12];
    output_0[35] = input_0[12];

    output_1[0] = -input_0[16]*input_2[0] + input_0[17]*input_0[18] -
    input_0[4]*input_1[0] + pydy_12 + input_3[3];
    output_1[1] = -input_0[0]*input_2[1] - input_0[7]*input_1[1] + pydy_12;
    output_1[2] = -input_0[1]*input_2[2] - input_0[10]*input_1[2] + pydy_10 +
    pydy_11 + pydy_4 + pydy_5 + pydy_6 + pydy_7 + pydy_8 + pydy_9;
    output_1[3] = -input_0[5]*input_2[3] - input_0[11]*input_1[3] + pydy_10 +
    pydy_11 + pydy_5 + pydy_6 + pydy_7 + pydy_9;
    output_1[4] = -input_0[8]*input_2[4] - input_0[15]*input_1[4] + pydy_10 +
    pydy_11 + pydy_6 + pydy_7;
    output_1[5] = -input_0[6]*input_2[5] - input_0[2]*input_1[5] + pydy_11 +
    pydy_7;\
"""

        self.generator._generate_cse()
        self.generator._generate_code_blocks()

        for k, v in self.generator.code_blocks.items():
            assert v == expected[k]

    def test_doprint(self):

        expected_header = """\
void evaluate(
              double input_0[19],
              double input_1[6],
              double input_2[6],
              double input_3[6],
              double output_0[36],
              double output_1[6]
             );
/*

input_0[19] : [c1, c2, k5, m1, k0, c3, c5, k1, c4, m4, k2, k3, m5, m2, m3, k4,
c0, g, m0]
input_1[6] : [x0(t), x1(t), x2(t), x3(t), x4(t), x5(t)]
input_2[6] : [v0(t), v1(t), v2(t), v3(t), v4(t), v5(t)]
input_3[6] : [f5(t), f2(t), f3(t), f0(t), f4(t), f1(t)]

*/\
"""

        expected_source = """\
#include <math.h>
#include "boogly_bee.h"

void evaluate(
              double input_0[19],
              double input_1[6],
              double input_2[6],
              double input_3[6],
              double output_0[36],
              double output_1[6]
             )
{

    double pydy_0 = input_0[9] + input_0[12];
    double pydy_1 = input_0[14] + pydy_0;
    double pydy_2 = input_0[13] + pydy_1;
    double pydy_3 = input_0[3] + pydy_2;
    double pydy_4 = input_3[1];
    double pydy_5 = input_3[2];
    double pydy_6 = input_3[4];
    double pydy_7 = input_3[0];
    double pydy_8 = input_0[17]*input_0[13];
    double pydy_9 = input_0[17]*input_0[14];
    double pydy_10 = input_0[17]*input_0[9];
    double pydy_11 = input_0[17]*input_0[12];
    double pydy_12 = input_0[17]*input_0[3] + pydy_10 + pydy_11 + pydy_4 +
    pydy_5 + pydy_6 + pydy_7 + pydy_8 + pydy_9 + input_3[5];

    output_0[0] = input_0[18] + pydy_3;
    output_0[1] = pydy_3;
    output_0[2] = pydy_2;
    output_0[3] = pydy_1;
    output_0[4] = pydy_0;
    output_0[5] = input_0[12];
    output_0[6] = pydy_3;
    output_0[7] = pydy_3;
    output_0[8] = pydy_2;
    output_0[9] = pydy_1;
    output_0[10] = pydy_0;
    output_0[11] = input_0[12];
    output_0[12] = pydy_2;
    output_0[13] = pydy_2;
    output_0[14] = pydy_2;
    output_0[15] = pydy_1;
    output_0[16] = pydy_0;
    output_0[17] = input_0[12];
    output_0[18] = pydy_1;
    output_0[19] = pydy_1;
    output_0[20] = pydy_1;
    output_0[21] = pydy_1;
    output_0[22] = pydy_0;
    output_0[23] = input_0[12];
    output_0[24] = pydy_0;
    output_0[25] = pydy_0;
    output_0[26] = pydy_0;
    output_0[27] = pydy_0;
    output_0[28] = pydy_0;
    output_0[29] = input_0[12];
    output_0[30] = input_0[12];
    output_0[31] = input_0[12];
    output_0[32] = input_0[12];
    output_0[33] = input_0[12];
    output_0[34] = input_0[12];
    output_0[35] = input_0[12];

    output_1[0] = -input_0[16]*input_2[0] + input_0[17]*input_0[18] -
    input_0[4]*input_1[0] + pydy_12 + input_3[3];
    output_1[1] = -input_0[0]*input_2[1] - input_0[7]*input_1[1] + pydy_12;
    output_1[2] = -input_0[1]*input_2[2] - input_0[10]*input_1[2] + pydy_10 +
    pydy_11 + pydy_4 + pydy_5 + pydy_6 + pydy_7 + pydy_8 + pydy_9;
    output_1[3] = -input_0[5]*input_2[3] - input_0[11]*input_1[3] + pydy_10 +
    pydy_11 + pydy_5 + pydy_6 + pydy_7 + pydy_9;
    output_1[4] = -input_0[8]*input_2[4] - input_0[15]*input_1[4] + pydy_10 +
    pydy_11 + pydy_6 + pydy_7;
    output_1[5] = -input_0[6]*input_2[5] - input_0[2]*input_1[5] + pydy_11 +
    pydy_7;

}\
"""
        self.generator._generate_cse()
        self.generator._generate_code_blocks()

        header, source = self.generator.doprint()

        assert header == expected_header
        lines = expected_source.split('\n')
        assert source == '\n'.join(lines[:1] + lines[2:])

        header, source = self.generator.doprint(prefix=self.prefix)

        assert header == expected_header
        assert source == expected_source

    def test_write(self):

        self.generator._generate_cse()
        self.generator._generate_code_blocks()

        header, source = self.generator.doprint(prefix=self.prefix)

        self.generator.write(self.prefix)

        with open(self.prefix + '.h') as f:
            assert f.read() == header

        with open(self.prefix + '.c') as f:
            assert f.read() == source

    def teardown(self):

        if os.path.isfile(self.prefix + '.h'):
            os.remove(self.prefix + '.h')

        if os.path.isfile(self.prefix + '.c'):
            os.remove(self.prefix + '.c')
