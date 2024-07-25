import unittest
from unittest.mock import patch

from . import ast, sym, exe

class TestExe (unittest.TestCase):
    def test_two(self):
        prg1 = "havoc x; assume x > 10; assert x > 15"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_one(self):
        prg1 = "x := 10;print_state"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_three(self):
        prg1 = "havoc x;while x < 3 do {havoc y;while y < 3 do y := y + 1;x := x + 1}"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_four(self):
        prg1 = "havoc x;while x < 20 do{x := x + 1;if x < 4 then y := 1};"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_five(self):
        prg1 = "havoc x;if x>0 then if x>5 then a := 1 else b := 1 else c := 1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_six(self):
        prg1 = "havoc x;while x < 20do{x := x + 1;if x < 4 then y := 1};"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_seven(self):
        prg1 = "havoc x;while x < 20 do x:=x+1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_eight(self):
        prg1 = "havoc x, y;assume y >= 0;c := 0;r := x;while c < ydo{r := r + 1;c := c + 1};assert r = x + y"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)