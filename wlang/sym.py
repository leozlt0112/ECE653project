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

from functools import reduce
import sys

import io 
import z3

from . import ast, int


class SymState(object):
    def __init__(self, solver=None):
        # environment mapping variables to symbolic constants
        self.env = dict()
        # path condition
        self.path = list()
        self._solver = solver
        if self._solver is None:
            self._solver = z3.Solver()

        # true if this is an error state
        self._is_error = False

    def add_pc(self, *exp):
        """Add constraints to the path condition"""
        self.path.extend(exp)
        self._solver.append(exp)
        self._solver.push()
    
    def pop_pc(self, *exp):
        """Remove constraints to the path condition"""
        self.path.pop()
        self._solver.pop()

    def is_error(self):
        return self._is_error

    def mk_error(self):
        self._is_error = True

    def is_empty(self):
        """Check whether the current symbolic state has any concrete states"""
        res = self._solver.check()
        return res == z3.unsat

    def pick_concerete(self):
        """Pick a concrete state consistent with the symbolic state.
           Return None if no such state exists"""
        res = self._solver.check()
        if res != z3.sat:
            return None
        model = self._solver.model()
        st = int.State()
        for (k, v) in self.env.items():
            st.env[k] = model.eval(v, model_completion=True)
        return st

    def fork(self):
        """Fork the current state into two identical states that can evolve separately"""
        child = SymState()
        child.env = dict(self.env)
        child.add_pc(*self.path)

        return (self, child)

    def __repr__(self):
        return str(self)

    def to_smt2(self):
        """Returns the current state as an SMT-LIB2 benchmark"""
        return self._solver.to_smt2()

    def __str__(self):
        buf = io.StringIO()
        for k, v in self.env.items():
            buf.write(str(k))
            buf.write(': ')
            buf.write(str(v))
            buf.write('\n')
        buf.write('pc: ')
        buf.write(str(self.path))
        buf.write('\n')

        return buf.getvalue()


class SymExec(ast.AstVisitor):
    def __init__(self):
        pass

    def run(self, ast, state):
        states = self.visit(ast, state=state)
        if (len(states) > 0):
            return states
        else:
            return []

    def visit_IntVar(self, node, *args, **kwargs):
        return kwargs['state'].env[node.name]

    def visit_BoolConst(self, node, *args, **kwargs):
        return z3.BoolVal(node.val)

    def visit_IntConst(self, node, *args, **kwargs):
        return z3.IntVal(node.val)

    def visit_RelExp(self, node, *args, **kwargs):
        lhs = self.visit(node.arg(0), *args, **kwargs)
        rhs = self.visit(node.arg(1), *args, **kwargs)
        if node.op == "<=":
            return lhs <= rhs
        if node.op == "<":
            return lhs < rhs
        if node.op == "=":
            return lhs == rhs
        if node.op == ">=":
            return lhs >= rhs
        if node.op == ">":
            return lhs > rhs

    def visit_BExp(self, node, *args, **kwargs):
        kids = [self.visit(a, *args, **kwargs) for a in node.args]

        if node.op == "not":
            assert node.is_unary()
            assert len(kids) == 1
            return z3.Not(kids[0])

        fn = None
        base = None
        if node.op == "and":
            fn = lambda x, y: z3.And(x,y)
            base = z3.BoolVal(True)
        elif node.op == "or":
            fn = lambda x, y: z3.Or(x,y)
            base = z3.BoolVal(False)

        assert fn is not None
        return reduce(fn, kids, base)

    def visit_AExp(self, node, *args, **kwargs):
        kids = [self.visit(a, *args, **kwargs) for a in node.args]

        fn = None

        if node.op == "+":
            fn = lambda x, y: x + y

        elif node.op == "-":
            fn = lambda x, y: x - y

        elif node.op == "*":
            fn = lambda x, y: x * y

        elif node.op == "/":
            fn = lambda x, y: x / y

        assert fn is not None
        return reduce(fn, kids)

    def visit_SkipStmt(self, node, *args, **kwargs):
        return [kwargs["state"]]

    def visit_PrintStateStmt(self, node, *args, **kwargs):
        return [kwargs["state"]]

    def visit_AsgnStmt(self, node, *args, **kwargs):
        st = kwargs["state"]
        rhs = self.visit(node.rhs, *args, **kwargs)
        st.env[node.lhs.name] = rhs
        return [st]

    def visit_IfStmt(self, node, *args, **kwargs):
        cond = self.visit(node.cond, *args, **kwargs)

        st: SymState = kwargs["state"]
        then_st, else_st = st.fork()

        then_st.add_pc(cond)
        else_st.add_pc(z3.Not(cond))

        states = []

        if not then_st.is_empty():
            then_states = self.visit(node.then_stmt, state=then_st)
            states.extend(then_states)

        if not else_st.is_empty():
            else_states = [else_st]
            if node.has_else() :
                else_states = self.visit(node.else_stmt, state=else_st)
            states.extend(else_states)

        return states
    
    def visit_WhileStmt(self, node, *args, **kwargs):
        depth = kwargs.get('depth', 0)

        st: SymState = kwargs["state"]
        init_states = [st]

        if node.inv:
            pass # TODO inv support
        
        # Run loop
        states = []

        for s in init_states:
            cond = self.visit(node.cond, *args, state=s)
            
            true_st, false_st = s.fork()

            true_st.add_pc(cond)
            false_st.add_pc(z3.Not(cond))

            if not false_st.is_empty():
                states.extend([false_st])

            # Limit to 10 iterations
            if not true_st.is_empty() and depth < 10:
                true_states = self.visit(node.body, state=true_st)
                for true_st in true_states:
                    if not true_st.is_empty():
                        loop_states = self.visit(node, state=true_st, depth=depth+1)
                        states.extend(loop_states)

        return states

    def visit_AssertStmt(self, node, *args, **kwargs):
        cond = self.visit(node.cond, *args, **kwargs)

        st: SymState = kwargs["state"]
        true_st, false_st = st.fork()

        states = []

        # Don't forget to print an error message if an assertion might be violated
        false_st.add_pc(z3.Not(cond))
        if not false_st.is_empty():
            print("Assertion error: " + str(node))
            print("State: " + str(false_st))
            print("Concrete State: " + str(false_st.pick_concerete()))
            false_st.mk_error()
            states.append(false_st)

        true_st.add_pc(cond)

        # if there is no possible true state we should remove this state
        if not true_st.is_empty():
            states.append(true_st)
        return states
        
    def visit_AssumeStmt(self, node, *args, **kwargs):
        cond = self.visit(node.cond, *args, **kwargs)

        st: SymState = kwargs["state"]
        st.add_pc(cond)

        states = []

        if not st.is_empty():
            states.append(st)
        
        return states

    def visit_HavocStmt(self, node, *args, **kwargs):
        st = kwargs["state"]
        for v in node.vars:
            st.env[v.name] = z3.FreshInt(v.name)
        return [st]

    def visit_StmtList(self, node, *args, **kwargs):
        states = kwargs["state"]
        if not isinstance(states, list):
            states = [states]
    
        for stmt in node.stmts:
            new_states = []
            for st in states:
                res_state = self.visit(stmt, state=st)
                new_states.extend(res_state)

            states = new_states
        return states


def _parse_args():
    import argparse
    ap = argparse.ArgumentParser(prog='sym',
                                 description='WLang Interpreter')
    ap.add_argument('in_file', metavar='FILE',
                    help='WLang program to interpret')
    args = ap.parse_args()
    return args


def main():
    args = _parse_args()
    prg = ast.parse_file(args.in_file)
    st = SymState()
    sym = SymExec()

    states = sym.run(prg, st)
    if len(states) == 0:
        print('[symexec]: no output states')
    else:
        count = 0
        for out in states:
            count = count + 1
            print('[symexec]: symbolic state reached')
            print(out)
        print('[symexec]: found', count, 'symbolic states')
    return 0


if __name__ == '__main__':
    sys.exit(main())
