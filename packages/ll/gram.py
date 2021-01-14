import inspect
from copy import deepcopy
from ..automata import Automaton
from .dispatcher import Rule, Dispatcher
import pathlib
from functools import reduce
from operator import or_ as union


def S_single(N, R, S, X):
    if isinstance(X, set):
        if X & N:
            raise GrammarParserException('Non-terminal in terminal range')
        else:
            return X
    if X not in N:
        return {X}
    else:
        return reduce(union, (s for i, s in enumerate(S)
                              if R[i].left == X))


def S_chain(N, R, S, A):
    d = {''} if all('' in S_single(N, R, S, X) for X in A) else set()
    ret = set()
    for X in A:
        sX = S_single(N, R, S, X)
        ret |= sX - {''}
        if '' not in sX:
            break
    return ret | d


class TableRow:
    def __init__(self):
        self.terminals = set()
        self.action = ''
        self.jump = -1
        self.accept = False
        self.stack = False
        self.ret = False
        self.error = False

    def __str__(self):
        s = (f"{self.terminals}\t"
             f"{self.action if self.action else 'NIL'}\t"
             f"{self.jump}\t"
             f"{self.accept}\t"
             f"{self.stack}\t"
             f"{self.ret}\t"
             f"{self.error}")
        return s

    def __repr__(self):
        return str(self)


class GrammarParserException(Exception):
    pass


class NilAction:
    def __init__(self):
        pass

    def __call__(self, A, t):
        return True


class HaltIterable:
    def __init__(self, iterable):
        self.iterable = iterable

    def __iter__(self):
        for x in self.iterable:
            yield x
        yield ''


class GrammarParser:
    p = pathlib.Path(__file__).parent / 'grammar.xml'
    D = Dispatcher()
    A = Automaton(str(p), D)
    
    def __init__(self, filename, disp=NilAction()):
        with open(filename) as fp:
            s = fp.read()
        if not GrammarParser.A.parse(s):
            raise GrammarParserException('Not a grammar')
        rules = GrammarParser.D.ruleset
        for i, r in enumerate(rules):
            print(i, r.left, r.laction if r.laction else '\'\'', r.right, r.raction)
        self.nt = set(r.left for r in rules)
        self.enumerate_rules(rules)
        for r in rules:
            print(r.nleft, r.nright, r.laction, r.raction)
        St = self.start_sets(rules)
        Fo = self.follow_sets(rules, St)
        Te = self.term_sets(rules, St, Fo)
        if not self.isLL(rules, Te):
            raise GrammarParserException('Not an LL(1)-grammar')
        self.table = self.build_table(St, Fo, Te, rules)
        self.denonify()
        self.dispatcher = disp

    def enumerate_rules(self, R):
        count = 0
        i = 0
        prev = R[0].left
        while i < len(R):
            if R[i].left == prev:
#                print(f'Encountered same rule {R[i].left, R[i].right}')
                R[i].nleft = count
                count += 1
                i += 1
            else:
#                print(f'Encountered different rule {R[i].left, R[i].right}')
                j = i-1
                while j > 0 and R[j-1].left == prev:
                    j -= 1
#                print(j, i)
                while j < i:
                    R[j].nright = count
                    count += len(R[j].right)
                    j += 1
                prev = R[i].left
        j = i-1
        while j > 0 and R[j-1].left == prev:
            j -= 1
#            print(j, i)
        while j < i:
            R[j].nright = count
            count += len(R[j].right)
            j += 1

    def start_sets(self, R):
        S = [set() for i, _ in enumerate(R)]
        new = True
        while new:
            new = False
            curS = []
            for i, s in enumerate(S):
                Sn = S_chain(self.nt, R, S, R[i].right)
                if not Sn <= s:
                    new = True
                curS.append(s | Sn)
            S = curS
        return S

    def follow_sets(self, R, St):
        S = {n: set() for n in self.nt}
        S[R[0].left].add(None)
#         print(S)
        new = True
        while new:
            new = False
            curS = deepcopy(S)
            for n in S:
                for r in R:
                    for i in range(len(r.right)):
                        if n == r.right[i]:
                            chain = r.right[i+1:]
                            
                            s = S_chain(self.nt, R, St, chain)
                            if not chain or '' in s:
                                s |= S[r.left]
                            s -= {''}
                            if not s <= S[n]:
                                new = True
                            curS[n] |= s
            S = curS
        return S

    def term_sets(self, R, St, Fo):
        S = [St[i]-{''} for i, _ in enumerate(R)]
        S = [S[i] | Fo[R[i].left] if '' in St[i] else S[i] for i, _ in enumerate(R)]
        return S

    def isLL(self, R, Te):
        for i, ti in enumerate(Te):
            for j, tj in enumerate(Te):
                if i != j and R[i].left == R[j].left and ti & tj:
                    print(f'Rules {i}({R[i].left}, {ti}), {j}({R[j].left}, {tj})')
                    return False
        return True

    def build_table(self, St, Fo, Te, R):
        Ml = set(r.nleft for r in R)
        Mr = set(r.nright+len(r.right)-1 for r in R)
#        print(Ml, Mr)
        table = [TableRow() for i in range(max(Mr)+1)]
        for i, r in enumerate(R):
            n = r.nleft
#            print(n)
            table[n].terminals = Te[i]
            table[n].action = r.laction
            table[n].jump = r.nright
            table[n].accept = False
            table[n].stack = False
            table[n].ret = False
            #print(n+1)
            table[n].error = n+1 not in Ml
            n = r.nright
            for k, tk in enumerate(r.right):
#                print(n, n+k)

                # terminals
                if not tk: # пустая строка
                    table[n+k].terminals = Te[i]
                elif isinstance(tk, set):
                    table[n+k].terminals = tk
                elif tk not in self.nt:
                    table[n+k].terminals = {tk}
                else:
                    chain = r.right[k:]
                    S = S_chain(self.nt, R, St, chain)
                    if '' in S:
                        S |= Fo[r.left]
                    S -= {''}
                    table[n+k].terminals = S

                table[n+k].action = r.raction[k]

                # jump
                if tk not in self.nt:
                    table[n+k].jump = n+k+1 if n+k not in Mr else -1
                else:
                    for j, r2 in enumerate(R):
                        if r2.left == tk:
                            table[n+k].jump = r2.nleft
                            break
                
                table[n+k].accept = tk and tk not in self.nt
                table[n+k].stack = tk in self.nt and n+k not in Ml
                table[n+k].stack &= n+k not in Mr
                table[n+k].ret = tk not in self.nt and n+k in Mr
                table[n+k].error = True
        return table

    def denonify(self):
        for t in self.table:
            if None in t.terminals:
                t.terminals -= {None}
                t.terminals.add('')

    def parse(self, token_stream):
        self.dispatcher.reset()
        stk = []
        s = HaltIterable(token_stream)
        tab = 0
        
        it = iter(s)
        token = next(it)
        stk.append(-1)

        while True:
            t = self.table[tab]
            print(tab, '\t', t, stk, token)
            if token in t.terminals:
                if t.accept:
                    A = t.action
                    if A:
                        if not self.dispatcher(A, token):
                            return False
                    token = next(it)
                if t.stack:
                    stk.append(tab)
                if t.ret:
                    tab = stk.pop()
                    if tab < 0:
                        break
                    tab += 1
                    continue
                if t.jump >= 0:
                    tab = t.jump
            elif not t.error:
                tab += 1
            else:
                break
        return not token and not stk
