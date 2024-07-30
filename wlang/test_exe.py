import unittest
from unittest.mock import patch

from . import ast, sym, exe
import z3
from unittest.mock import MagicMock

class TestExe (unittest.TestCase):
    def test_two(self):
        prg1 = "havoc x; assume x > 10;assume false"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 1)
    def test_one(self):
        prg1 = "havoc x; assume x>10; assert x<9; assert x>10"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 1)
    def test_three(self):
        prg1 = "havoc x; assert x<9"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 2)
    def test_four(self):
        prg1 = "x := 10;print_state;skip"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 1)

    def test_14(self):
        prg1 = "havoc x; assume false"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()

        with patch.object(engine, 'visit', return_value=[]):
            out = engine.run(ast1, st)
            self.assertEquals(len(out), 0)
    def test_five(self):
        prg1 = "havoc x;r:=0;if x>8 then r:=x-7 else r:=x-9; if x<5 then r:=x-2"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 3)
    def test_six(self):
        prg1 = "x:=5;r:=0;if x>8 then r:=x-7 else r:=x-9; if x<=5 then r:=x-2"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 1)
    def test_seven(self):
        prg1 = "havoc x;if x>0 then if x>5 then a := 1 else b := 1 else c := 1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 3)
    def test_eight(self):
        prg1 = "havoc x, y;assume y >= 0;c := 0;r := x;while c < y do{r := r + 1;c := c + 1};assert r = x + y"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 12)
    def test_nine(self):
        prg1 = "havoc x;while x > 2 do x:=x-1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 12)
   
    def test_ten(self):
        prg1 = "havoc x;while x < 20 do x:=x+1"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = [s for s in engine.run(ast1, st)]
        self.assertEquals(len(out), 12)
    def test_eleven(self):
        prg1 = "x:=2; while x<1 do x:=x+1; assert x>4;assume x<0"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = engine.run(ast1, st)
        self.assertEquals(len(out), 1)
    def test_twelve(self):
        prg1 = "havoc x; assume x>20;while x > 10 do x:=x-1"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = engine.run(ast1, st)
        self.assertEquals(len(out), 1)
    def test_d(self):
        prg1 = "havoc x; assume x > 10; assert x < 5"
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        st.sym_state.mk_error()
        parent, child = st.fork()
        self.assertTrue(child.sym_state.is_error())
    def test_thirteen(self):
        st = exe.ExeState()
        repr(st)

    def test_fourteen(self):
        mock_solver = MagicMock()
        mock_solver.check.return_value = z3.unsat
        with patch('z3.Solver', return_value=mock_solver):
            st = exe.ExeState()
            init_state = st._get_init_state()
            self.assertIsNone(init_state)
    def test_fifteen(self):
        st =  exe.ExeState()
        st.mk_infeasable()

    def test_sixteen(self):
        prg1 = "havoc x; assume false"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()

        with patch.object(engine, 'visit', return_value=[]):
            out = engine.run(ast1, st)
            self.assertEquals(len(out), 0)
    
    def test_seventeen(self):
        prg1 = "skip"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = engine.run(ast1, st)
        self.assertEquals(len(out), 1)
    
    def test_eighteen(self):
        prg1 = "x:=2; if x=4 then x:=6 else x:=6"  
        ast1 = ast.parse_string(prg1)
        engine = exe.ExeExec()
        st = exe.ExeState()
        out = engine.run(ast1, st)
        self.assertEquals(len(out), 1)
    
    def test_nineteen(self):
        state = exe.ExeState()
        state.mk_error() 

        stmt_list = ast.StmtList([ast.SkipStmt()])

        executor = exe.ExeExec()

        result_states = executor.visit_StmtList(stmt_list, state=state)

    @patch('sys.argv', ['wlang.exe', 'wlang/test1.prg'])
    def test_main(self):
        self.assertEqual(exe.main(),0)
    @patch('sys.argv', ['wlang.exe', 'wlang/test_invalid.prg'])
    def test_main2(self):
        self.assertEqual(exe.main(),0)

