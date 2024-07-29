# The MIT License (MIT)
# Copyright (c) 2016 Arie Gurfinkel

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import unittest
from unittest.mock import patch

from . import ast, sym


class TestSym (unittest.TestCase):
    def test_one(self):
        prg1 = "havoc x; assume x > 10; assert x > 15"
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)

    def test_assume_assume(self):
        prg1 = "havoc x; assume false"
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        con = st.pick_concerete()
        self.assertEquals(con, None)
        self.assertEquals(len(out), 0)
    
    def test_SymState_methods(self):
        prg1 = "havoc x; assume x > 10; assert x > 15"
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)

        self.assertTrue(out[0].is_error())
        self.assertFalse(out[1].is_error())
        state = """x: x!12
pc: [10 < x!12, 15 < x!12]
"""
        self.assertEquals(repr(out[1]),state)

    @patch('sys.argv', ['wlang.sym','wlang/test1.prg'])
    def test_main(self):
        self.assertEqual(sym.main(), 0)

    @patch('sys.argv', ['wlang.sym','wlang/test2.prg'])
    def test_main2(self):
        self.assertEqual(sym.main(), 0)

    def test_if(self):
        prg1 =  """
                    havoc x;
                    if x < 3 then {
                        if x >= 1 then
                            y := 1
                        else
                            y := 2
                    }
                    else {
                        if x <= 10 then
                            z := 1
                        else
                            z := 2
                    }
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 4)

    def test_while(self):
        prg1 =  """
                    havoc x;
                    while x < 3 do 
                        x := x + 1
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 11)

        prg1 =  """
                    havoc x;
                    while x < 3 do 
                        if true then
                            x := x + 1
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 11)

    def test_relExp(self):
        prg1 =  """
                    havoc x;
                    if x = 0 then 
                        x := 1
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)

    def test_BExp(self):
        prg1 =  """
                    havoc x;
                    if not (x = 0) then 
                        x := 1
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)

        prg1 =  """
                    havoc x;
                    if x > 0 and x < 5 or x > 10 then 
                        x := 1
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)

    def test_leftovers(self):
        prg1 =  """
                    x := 1 + 2 - 3 * 4 / 5;
                    if x > 0 then 
                        skip
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 1)

    def test_bug(self):
        prg1 =  """
                    i := 0;
                    j := 0;
                    while i < 5 do {
                        while j < 3 do 
                            j := j + 1;
                        j := 0;
                        i := i + 1
                    };
                    assert i = 4;
                    print_state
                """
        ast1 = ast.parse_string(prg1)
        engine = sym.SymExec()
        st = sym.SymState()
        out = [s for s in engine.run(ast1, st) if not s.is_error()]
        self.assertEquals(len(out), 0)
