from copy import deepcopy
from automata import Automaton
from .dispatcher import Rule
import pathlib
from functools import reduce
from operator import or_ as union


def S_single(N, R, S, X):
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

    def get_parse_results(self):
        return dict()


class HaltIterable:
    def __init__(self, iterable):
        self.iterable = iterable

    def __iter__(self):
        for x in self.iterable:
            yield x
        yield None


class GrammarParser:
    p = pathlib.Path('ll/grammar.xml').absolute()
    print(p)
    A = Automaton(p)    
    
    def __init__(self, filename, actions=NilAction()):
        with open(filename) as fp:
            s = fp.read()
        if not GrammarParser.A.parse(s):
            raise GrammarParserException('Not a grammar')
        res = GrammarParser.A.get_parse_results()
        rules = res["ruleset"]
        for i, r in enumerate(rules):
            print(i, r.left, r.laction, r.right, r.raction)
        self.nt = set(r.left for r in rules)
#        print(f"Non-terminals: {self.nt}")
        self.enumerate_rules(rules)
#        for r in rules:
#            print(r.nleft, r.nright, r.actions)
        St = self.start_sets(rules)
#        print(St)
        Fo = self.follow_sets(rules, St)
#        print(Fo)
        Te = self.term_sets(rules, St, Fo)
#        print(Te)
        if not self.isLL(rules, Te):
            raise GrammarParserException('Not an LL(1)-grammar')
        self.table = self.build_table(St, Fo, Te, rules)
#        for i, t in enumerate(self.table):
#            print(t)
        self.actions = actions

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
                print(j, i)
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
        print(S)
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
                if not tk:
                    table[n+k].terminals = Te[i]
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

    def parse(self, token_stream):
        stk = []
        s = HaltIterable(token_stream)
        tab = 0
        
        it = iter(s)
        token = next(it)
        stk.append((-1, []))

        while True:
            t = self.table[tab]
            print(tab, '\t', t, stk, token)
            if token in t.terminals:
                if t.accept:
                    A = t.action
                    if A:
                        if not self.actions(A, token):
                            return False
                    token = next(it)
                if t.stack:
                    stk.append((tab, [t.action]))
                if t.ret:
                    tab, A = stk.pop()
                    for a in A:
                        if a:
                            if not self.actions(a, token):
                                return False
                    if tab < 0:
                        break
                    tab += 1
                    continue
                if t.jump >= 0:
                    if t.action and not t.accept and not t.stack:
                        stk[-1][1].append(t.action)
                    tab = t.jump
            elif not t.error:
                tab += 1
            else:
                break
        return not token and not stk

    def get_parse_results(self):
        return self.actions.get_parse_results()
