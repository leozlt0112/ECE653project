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
        buf.write('Init Concrete State: ')
        buf.write('\n')
        buf.write(str(self._get_init_state()))
        buf.write('\n') 
        buf.write('Concrete State: ')
        buf.write('\n')
        buf.write(str(self.con_state))
        buf.write('\n')     
        buf.write('Symbolic State: ')
        buf.write('\n')
        buf.write(str(self.sym_state))

        return buf.getvalue()
    
    def _get_init_state(self):
        res = self.sym_state._solver.check()
        if res == z3.sat:
            model = self.sym_state._solver.model()
            st = int.State()
            for var in model:
                concrete_value = model[var]
                st.env[str(var).split("!")[0]] = concrete_value.as_long()
            return st
        else:
            return None
    
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
        st: ExeState = kwargs["state"]

        # Evaluate conditionwha
        con_cond = self.con_vistor.visit(node.cond, state=st.con_state)
        sym_cond = self.sym_vistor.visit(node.cond, state=st.sym_state)
        
        # Fork execution state
        passed_st, failed_st = st.fork()

        # Update path condition
        passed_st.sym_state.add_pc(sym_cond)
        failed_st.sym_state.add_pc(z3.Not(sym_cond))

        states = []

        # if both branches are SAT we need to compute new concrete assignments
        if not (passed_st.sym_state.is_empty() or failed_st.sym_state.is_empty()):
            if con_cond:
                # if concrete cond is true false_st needs new concrete assignments
                failed_st.con_state.env = _pick_concrete(failed_st.sym_state)
            else:
                # if concrete cond is false true_st needs new concrete assignments
                passed_st.con_state.env = _pick_concrete(passed_st.sym_state)

            passed_states = self.visit(node.then_stmt, state=passed_st)
            states.extend(passed_states)

            if node.has_else():
                failed_states = self.visit(node.else_stmt, state=failed_st)
                states.extend(failed_states)
            else:
                states.extend([failed_st])

            return states

        # if we make it here only 1 path is SAT
        if con_cond:
            passed_states = self.visit(node.then_stmt, state=passed_st)
            states.extend(passed_states)
        else:
            if node.has_else():
                failed_states = self.visit(node.else_stmt, state=failed_st)
                states.extend(failed_states)
            else:
                states.extend([failed_st])
        
        return states

    def visit_WhileStmt(self, node, *args, **kwargs):
        depth = kwargs.get('depth', 0)

        st: ExeState = kwargs["state"]

        con_cond = self.con_vistor.visit(node.cond, state=st.con_state)
        sym_cond = self.sym_vistor.visit(node.cond, state=st.sym_state)

        states = []

        # fork execution state
        true_st, false_st = st.fork()

        true_st.sym_state.add_pc(sym_cond)
        false_st.sym_state.add_pc(z3.Not(sym_cond))

        # if both branches are SAT we need to compute new concrete assignments
        if not (true_st.sym_state.is_empty() or false_st.sym_state.is_empty()):
            if con_cond:
                # if concrete cond is true false_st needs new concrete assignments
                false_st.con_state.env = _pick_concrete(false_st.sym_state)
            else:
                # if concrete cond is false true_st needs new concrete assignments
                true_st.con_state.env = _pick_concrete(true_st.sym_state)

            states.extend([false_st]) # Add the false state to output

            # evaluate loop
            if depth < 10:
                true_states: list[ExeState] = self.visit(node.body, state=true_st) # get program states after executing loop body
                for true_st in true_states:
                    # Extract states for next iteration of the loop
                    loop_states = self.visit(node, state=true_st, depth=depth+1)
                    states.extend(loop_states)
            else:
                # if depth is greater than 10 this loop is complex and we will let the loop finish concretely
                true_states: list[ExeState] = self.visit(node.body, state=true_st) # get program states after executing loop body
                for true_st in true_states:
                    true_st.con_state = self.con_vistor.visit(node, state=true_st.con_state)
                    _concretize_sym_state(true_st)
                    states.extend([true_st])
            
            return states

        # if we make it here only a single branch is SAT
        if con_cond:
            # true_st is SAT
            # evaluate loop
            if depth < 10:
                true_states: list[ExeState] = self.visit(node.body, state=true_st) # get program states after executing loop body
                for true_st in true_states:
                    # Extract states for next iteration of the loop
                    loop_states = self.visit(node, state=true_st, depth=depth+1)
                    states.extend(loop_states)
            else:
                # if depth is greater than 10 this loop is complex and we will let the loop finish concretely
                true_states: list[ExeState] = self.visit(node.body, state=true_st) # get program states after executing loop body
                for true_st in true_states:
                    true_st.con_state = self.con_vistor.visit(node, state=true_st.con_state)
                    _concretize_sym_state(true_st)
                    states.extend([true_st])
        else:
            # false_st is SAT
            states.extend([false_st]) # Add the false state to output

        return states
    
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

def _concretize_sym_state(state: ExeState):
    """
    Helper method to handle updating symbolic state when an execution path is too complex.
    This method replaces symbolic variables with their concrete values and resets the path conditions.
    """
    con_env = state.con_state.env
    sym_env = state.sym_state.env

    # Add constraints that force the symbolic state to match the concrete state
    for v in con_env.keys():
        sym_env[v] = z3.IntVal(con_env[v])
        constraint = sym_env[v] == z3.IntVal(con_env[v])
        state.sym_state.add_pc(constraint)

    return state

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