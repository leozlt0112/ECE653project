import unittest
from unittest.mock import patch

from . import ast, sym, exe
import z3
from unittest.mock import MagicMock

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
        self.assertEquals(len(out), 1)
    """
    def test_three(self):
        prg1 = "havoc x;while x < 3 do {havoc y;while y < 3 do y := y + 1;x := x + 1}"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    """
    def test_four(self):
        prg1 = "havoc x;while x < 20 do{x := x + 1;if x < 4 then y := 1}"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 23)
    def test_five(self):
        prg1 = "havoc x;if x>0 then if x>5 then a := 1 else b := 1 else c := 1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 3)
    def test_six(self):
        prg1 = "havoc x;while x < 20 do{x := x + 1;if x < 4 then y := 1}"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 23)
    def test_seven(self):
        prg1 = "havoc x;while x < 20 do x:=x+1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 12)
    def test_eight(self):
        prg1 = "havoc x, y;assume y >= 0;c := 0;r := x;while c < y do{r := r + 1;c := c + 1};assert r = x + y"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 12)
    def test_nine(self):
        prg1 = "havoc x;y:=x+2;if (x*6)>y then x:=12 else y:=14;if y>12 then y:=13 else y:=20"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 3)
    def test_fork_with_error_state(self):
        prg1 = "havoc x; assume x > 10; assert x < 5"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        st.sym_state.mk_error()
        parent, child = st.fork()
        self.assertTrue(child.sym_state.is_error())
    def test_repr(self):
        st = exe.ExeState()
        repr(st)

    def test_get_init_state_returns_none(self):
        mock_solver = MagicMock()
        mock_solver.check.return_value = z3.unsat
        with patch('z3.Solver', return_value=mock_solver):
            st = exe.ExeState()
            init_state = st._get_init_state()
            self.assertIsNone(init_state)
    def test_mk_infeasable(self):
        st =  exe.ExeState()
        st.mk_infeasable()

    def test_no_states_produced(self):
        prg1 = "havoc x; assume false"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()

        with patch.object(engine, 'visit', return_value=[]):
            out = engine.run(ast1, st)
            self.assertEquals(len(out), 0)
    def test_no_states_produced(self):
        prg1 = "skip"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = engine.run(ast1, st)
        self.assertEquals(len(out), 1)
    