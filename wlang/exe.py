from functools import reduce
import sys

import io 
import z3

from . import ast, int, sym
from .bcolors import bcolors
import copy
class ExeState(object):
    def __init__(self, solver=None):
        self.con_state: int.State = int.State()
        self.sym_state: sym.SymState = sym.SymState()
        self._is_infeasable = False
        self._is_error = False

    def fork(self):
        """Fork the current state into two identical states that can evolve separately"""
        child = ExeState()

        child.con_state.env = dict(self.con_state.env)

        child.sym_state.env = dict(self.sym_state.env)
        child.sym_state.add_pc(*self.sym_state.path)
        if ( self.sym_state.is_error() ):
            child.sym_state.mk_error()

        return (self, child)
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        buf = io.StringIO()
        buf.write('Concrete State: ')
        buf.write('\n')
        buf.write(str(self.con_state))
        buf.write('\n')     
        buf.write('Symbolic State: ')
        buf.write('\n')
        buf.write(str(self.sym_state))

        return buf.getvalue()
    
    def mk_infeasable(self):
        self._is_infeasable = True

    def mk_error(self):
        self._is_error = True

    def is_valid(self):
        return not (self._is_infeasable or self._is_error or self.sym_state.is_error())
    
class ExeExec(ast.AstVisitor):
    def __init__(self):
        self.sym_vistor = sym.SymExec()
        self.con_vistor = int.Interpreter() 
        pass

    def run(self, ast, state):
        states = self.visit(ast, state=state)
        if (len(states) > 0):
            return states
        else:
            return []

    def visit_SkipStmt(self, node, *args, **kwargs):
        return [kwargs["state"]]

    def visit_PrintStateStmt(self, node, *args, **kwargs):
        return [kwargs["state"]]

    def visit_AsgnStmt(self, node, *args, **kwargs):
        st: ExeState = kwargs["state"]

        st.sym_state = self.sym_vistor.visit(node, state=st.sym_state)[0]
        st.con_state = self.con_vistor.visit(node, state=st.con_state)
        return [st]

    def visit_IfStmt(self, node, *args, **kwargs):
        new_states = []
        anothercopy = []
        take_copy = []
        st: ExeState = kwargs["state"]

        # Evaluate condition
        con_cond = self.con_vistor.visit(node.cond, state=st.con_state)
        sym_cond = self.sym_vistor.visit(node.cond, state=st.sym_state)
        
        # Fork execution state
        passed_st, failed_st = st.fork()

        # Update path condition
        passed_st.sym_state.add_pc(sym_cond)
        failed_st.sym_state.add_pc(z3.Not(sym_cond))
        else_states_con_then = []
        else_states_sym_then = []
        a = []
        else_states_sym_then_a = []
        # Process the 'then' branch
        if con_cond:
            then_states_con = self.con_vistor.visit(node.then_stmt, state=st.con_state)
            then_states_sym = self.sym_vistor.visit(node.then_stmt, state=st.sym_state)
        
            # Ensure then_states_con and then_states_sym are lists
            if not isinstance(then_states_con, list):
                then_states_con = [then_states_con]
            if not isinstance(then_states_sym, list):
                then_states_sym = [then_states_sym]

            # Merge concrete and symbolic states for 'then' branch
            for con, sym in zip(then_states_con, then_states_sym):
                new_state = ExeState()
                new_state.con_state = con
                new_state.sym_state = sym
                new_states.append(new_state)
            
            ## after forking is done, give new concrete state to match new condition
            anothercopy=copy.deepcopy(new_states)
            if not failed_st.sym_state.is_empty():
                if node.has_else():
                    failed_st.con_state.env = _pick_concrete(failed_st.sym_state)
                    else_states_con_then = self.con_vistor.visit(node.else_stmt, state=failed_st.con_state)
                    print(else_states_con_then)
                    else_states_sym_then = self.sym_vistor.visit(node.else_stmt, state=failed_st.sym_state)
                    st.sym_state.add_pc(z3.Not(sym_cond))

            if not isinstance(else_states_con_then, list):
                else_states_con_then = [else_states_con_then]
            if not isinstance(else_states_sym_then, list):

                #
                else_states_sym_then = [else_states_sym_then]
            for con, sym in zip(else_states_con_then, else_states_sym_then):
                new_state = ExeState()
                new_state.con_state = con
                new_state.sym_state = sym
                anothercopy.append(new_state)
            
        else:
            else_states_con = self.con_vistor.visit(node.else_stmt, state=st.con_state)
            else_states_sym = self.sym_vistor.visit(node.else_stmt, state=st.sym_state)
            if not isinstance(else_states_con, list):
                else_states_con = [else_states_con]
            if not isinstance(else_states_sym, list):
                else_states_sym = [else_states_sym]

            # Merge concrete and symbolic states for 'then' branch
            for con, sym in zip(else_states_con, else_states_sym):
                new_state = ExeState()
                new_state.con_state = con
                new_state.sym_state = sym
                print(new_state)
                new_states.append(new_state)
            take_copy = copy.deepcopy(new_states)
            if not passed_st.sym_state.is_empty():
                if node.has_else():
                    passed_st.con_state.env = _pick_concrete(passed_st.sym_state)
                    a = self.con_vistor.visit(node.then_stmt, state=passed_st.con_state)
                    else_states_sym_then_a= self.sym_vistor.visit(node.then_stmt, state=passed_st.sym_state)
                    st.sym_state.add_pc(z3.Not(sym_cond))

            if not isinstance(a, list):
                a = [a]
            if not isinstance(else_states_sym_then_a, list):
                else_states_sym_then = [else_states_sym_then_a]
            for con, sym in zip(a, else_states_sym_then_a):
                new_state = ExeState()
                new_state.con_state = con
                new_state.sym_state = sym
                take_copy.append(new_state)
        return take_copy + anothercopy
  
    def visit_WhileStmt(self, node, *args, **kwargs):
        pass
    
    def visit_AssertStmt(self, node, *args, **kwargs):
        st: ExeState = kwargs["state"]

        # evaluate condition 
        con_cond = self.con_vistor.visit(node.cond, state=st.con_state)
        sym_cond = self.sym_vistor.visit(node.cond, state=st.sym_state)
        
        # fork execution state
        passed_st, failed_st = st.fork()

        # update pc
        passed_st.sym_state.add_pc(sym_cond)
        failed_st.sym_state.add_pc(z3.Not(sym_cond))

        # if both branches are SAT we need to compute new concrete assignments
        if not (passed_st.sym_state.is_empty() or failed_st.sym_state.is_empty()):
            # TODO: If current concrete state passes cond we dont need to update 
            #       the concrete assignment for that path and vise-versa.
            passed_st.con_state = _pick_concrete(passed_st.sym_state)

            failed_st.con_state = _pick_concrete(failed_st.sym_state)
            _log_error("[Assert error]: Assert can fail.", node, failed_st)
            failed_st.mk_error()

            return [passed_st, failed_st]
        
        # if we make it here only a single branch is SAT
        if con_cond:
            return [passed_st]
        else:
            # concrete value failed assertion
            _log_error("[Assert error]: Assert always fails.", node, failed_st)
            st.mk_error()
            return [failed_st]
        
    def visit_AssumeStmt(self, node, *args, **kwargs):
        st: ExeState = kwargs["state"]

        cond = self.sym_vistor.visit(node.cond, state=st.sym_state)
        st.sym_state.add_pc(cond)

        if not st.sym_state.is_empty(): 
            # if we can generate a concrete assignment
            st.con_state.env = _pick_concrete(st.sym_state)
        else: 
            # following this assumption no concrete state exists
            _log_error("[Assume error]: Assumption cannot be satisfied.", node, st)
            st.mk_infeasable()

        return [st]

    def visit_HavocStmt(self, node, *args, **kwargs):
        st: ExeState = kwargs["state"]

        st.sym_state = self.sym_vistor.visit_HavocStmt(node, state=st.sym_state)[0]
        st.con_state = self.con_vistor.visit_HavocStmt(node, state=st.con_state)

        return [st]
        
    def visit_StmtList(self, node, *args, **kwargs):
        states: list[ExeState] | ExeState = kwargs["state"]
        if not isinstance(states, list):
            states = [states]
    
        for stmt in node.stmts:
            new_states = []
            for state in states:
                if state.is_valid():
                    # this is a valid state so we can compute the next state
                    res_state = self.visit(stmt, state=state)
                else: 
                    # this state is invalid we so don't execute it
                    res_state = [state]
                new_states.extend(res_state)

            states = new_states
        return states
    
def _log_error(message: str, node, state):
    print(f"{bcolors.FAIL}{message}")
    print(f"Node: \n{str(node)}")
    print(f"State: \n{str(state)}{bcolors.ENDC}\n")

def _pick_concrete(state: sym.SymState): 
    """
    Helper method for picking concrete values since sym.SymState.pick_concrete() 
    returns z3 objects which don't play nice when you try to evaluate them concretely
    """
    con_env = {}
    sym_env = state.pick_concerete().env
    for k, v in sym_env.items():
        con_env[str(k)] = v.as_long()
    return con_env

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
    st = ExeState()
    exe = ExeExec()

    states: list[ExeState] = exe.run(prg, st)

    valid_states = [s for s in states if s.is_valid()] # cull invalid states
    invalid_states = [s for s in states if not s.is_valid()]

    count = 0
    for out in invalid_states:
        count = count + 1
        print('[exec]: invalid state reached')
        print(out)
        print('[exec]: found', count, 'invalid states\n')

    if len(valid_states) == 0:
        print('[exec]: no valid output states')
    else:
        count = 0
        for out in valid_states:

            count = count + 1
            print('[exec]: state reached')
            print(out)
        print('[exec]: found', count, 'valid states')
    return 0


if __name__ == '__main__':
    sys.exit(main())