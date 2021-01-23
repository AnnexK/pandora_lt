from .interface import LRActionDispatcher
from .dispatcher import Rule, Dispatcher
from ..automata import Automaton
import pathlib
from typing import List, Set, Dict, Tuple, Iterator, Iterable, Optional, FrozenSet
from functools import reduce
from operator import or_ as union
from copy import copy


# исключение при разборе грамматики
class GrammarParserException(Exception):
    pass

# вычисление множеств стартовых символов
def S(N: Set[str], R: List[Rule], X: str) -> Set[str]:
    if X and X[0] == '\1':
        SX = set(X[1:])
        if SX & N:
            raise GrammarParserException('Nonterminal in terminal charset')
        return SX
    elif X not in N:
        return {X}
    else:
        return reduce(union, (r.start for r in R
                              if r.left == X))


class Situation:
    def __init__(self, rule: Rule, position: int, token: str):
        self.rule = rule
        self.pos = position
        self.tok = token

    def __hash__(self):
        return hash((id(self.rule), self.pos, self.tok))

    def __eq__(self, sit):
        return id(self.rule) == id(sit.rule) and self.pos == sit.pos and self.tok == sit.tok

    def __str__(self):
        l = self.rule.left
        r = self.rule.right
        p = self.pos
        t = self.tok
        fake = l[0] == '\0'
        return f"[{l if not fake else '$'} -> {r[:p]} . {r[p:]} | {t if t else 'NIL'}]"
    
    def __repr__(self):
        return str(self)

# состояние есть множество ситуаций
State = Set[Situation]
# а это вроде уже и не надо
# FrozenState = FrozenSet[Situation]
class TableAction:
    def __init__(self, act: str, sh: int, rd: Optional[Rule], hlt: bool):
        # id действия
        self.action: str = act
        # номер состояния в списке состояний
        self.shift: int = sh
        # Optional <=> nullable тип
        self.reduce: Optional[Rule] = rd
        self.halt: bool = hlt

# обертка для потока
class HaltIterable:
    def __init__(self, iterable: Iterable[str]):
        self.iterable = iterable

    def __iter__(self) -> Iterator[str]:
        for x in self.iterable:
            yield x
        yield ''


# диспетчер действий по умолчанию
class NilAction(LRActionDispatcher):
    def __init__(self):
        pass

    def __call__(self, A: str, t: str) -> bool:
        return True

    def reset(self):
        pass


class GrammarParser:
    p = pathlib.Path(__file__).parent / 'grammar.xml'
    D = Dispatcher()
    A = Automaton(str(p), D)
    Table = Dict[Tuple[int, FrozenSet[str]], TableAction]
    def __init__(self, filename: str, disp: LRActionDispatcher=NilAction()):
        with open(filename) as fp:
            s = fp.read()
        if not GrammarParser.A.parse(s):
            raise GrammarParserException('Not a grammar')

        self.nt = GrammarParser.D.nontermset
        # добавить фиктивное правило в начале
        rules = self._add_fake(GrammarParser.D.ruleset)
        # проверить пересечения терминалов-множеств
        self._check_inters()
        # добавить к правилам стартовые символы
        self._append_starts(rules)
        # построить список состояний и граф переходов
        self.I, R = self._build_graph(rules)
        # построить таблицу
        self.table: GrammarParser.Table = self.build_table(self.I, R, rules)
        self.disp = disp
    
    def _check_inters(self):
        # для всех различных пар терминалов (x, y)
        for x in self.D.elemset - self.nt:
            for y in self.D.elemset - self.nt - {x}:
                if x[0] == '\1' or y[0] == '\1':
                    sx = {x} if x[0] != '\1' else set(x[1:])
                    sy = {y} if y[0] != '\1' else set(y[1:])
                    if sx & sy:
                        raise GrammarParserException(f'Charset/char intersection: {x}, {y}')


    def _add_fake(self, rules: List[Rule]) -> List[Rule]:
        # фиктивное правило имеет в левой части нетерминал '\0'
        # такой нетерминал гарантированно не будет присутствовать в множестве нетерминалов
        # т.к. его не пропустит парсер грамматики
        fakerule = Rule('\0', '')
        fakerule.right.append(rules[0].left)
        fakerule.raction.append('')
        self.nt.add('\0')
        self.D.elemset.add('\0')
        # добавить правило в начало
        return [fakerule]+rules
        
    def _append_starts(self, R: List[Rule]):
        N = self.D.nontermset
        change = True
        while change:
            change = False
            s: List[Set[str]] = [r.start for r in R]
            for i, _ in enumerate(s):
                s[i] = S(self.nt, R, R[i].right[0])
                if not s[i] <= R[i].start:
                    change = True
            for i, _ in enumerate(s):
                R[i].start = s[i]

    # вычислить замыкание состояния I
    def _closure(self, I: State, R: List[Rule]):
        def sit_filter(s: Situation):
            # точка перед нетерминалом
            return not s.pos == len(s.rule.right) and s.rule.right[s.pos] in self.nt
        
        change = True
        while change:
            change = False
            tmp_I = copy(I)
            # для каждой LR ситуации [ A -> k . B t | a], B - нетерминал;
            for sit in filter(sit_filter, I):
                right = sit.rule.right
                B = right[sit.pos]
                a = sit.tok
                # для каждого нетерминала b из S(t+a);
                # S(t+a) = S(t), t непусто
                # иначе S(t+a) = S(a)
                tk = a if sit.pos+1 == len(right) else right[sit.pos+1]
                for b in S(self.nt, R, tk):
                    # для каждого правила B -> y;
                    for r in filter(lambda x: x.left == B, R):
                        s = Situation(r, 0, b)
                        if s not in I:
                            tmp_I.add(s)
            if not tmp_I <= I:
                change = True
                I |= tmp_I

    # вычислить переход(I, X)
    def _trans(self, i: State, x: str, rules: List[Rule]) -> State:
        j: State = set()
        # для всех ситуаций из i, где точка перед x
        for sit in i:
            if sit.pos < len(sit.rule.right) and sit.rule.right[sit.pos] == x:
                rx = sit.rule.right[sit.pos]
                if x == rx:
                    j.add(Situation(sit.rule, sit.pos+1, sit.tok))
        self._closure(j, rules)
        return j
    
    Graph = Dict[Tuple[int, int], str]
    def _build_graph(self, rules: List[Rule]) -> Tuple[List[State], Graph]:
        X = self.D.elemset
        s0 = set()
        s0.add(Situation(rules[0], 0, ''))
        self._closure(s0, rules)
        # список состояний
        I = [s0]
        # граф
        R: GrammarParser.Graph = dict()
        change = True
        while change:
            change = False
            cI = copy(I)
            for k, i in enumerate(I):
                for x in X:
                    j = self._trans(i, x, rules)
                    if j:
                        if j not in I:
                            cI.append(j)
                            r = len(cI)-1
                            change = True
                        else:
                            r = I.index(j)
                        if (k, r) not in R:
                            R[k, r] = x
                            change = True
            I = cI
        return I, R

    
    def build_table(self, I: List[State], R: Graph, rules: List[Rule]) -> Table:
        # отображение номера состояния и символа грамматики в действие
        ret: GrammarParser.Table = dict()

        # если грамматика принимает пустые строки,
        # то T(S0, EOF) = HALT
        if self.D.empty:
            ret[0, frozenset([''])] = TableAction(rules[0].laction, -1, None, True)
        for k, i in enumerate(I):
            for s in i:
                # точка не в конце правила -- пишем сдвиг
                if s.pos < len(s.rule.right):
                    X = s.rule.right[s.pos]
                    # множество символов для данного символа грамматики
                    # впрочем, вместо того, чтобы индексироваться по (int, frozenset) в словаре
                    # можно было разбить это множество на отдельные символы,
                    # добавить для каждого отдельного символа в словарь действие таблицы...
                    sX = frozenset(X[1:]) if X[0] == '\1' else frozenset({X})
                    for r, j in enumerate(I):
                        if R.get((k, r), '') == X:
                            # пробуем получить элемент из таблицы
                            retel = ret.get((k, sX), None)
                            # если элемент в таблице -- свертка, то ничего не делаем
                            if retel and retel.shift != -1:
                                continue
                            # иначе пишем свертку
                            else:
                                ret[k, sX] = TableAction(s.rule.raction[s.pos], r, None, False)
                # точка в конце правила -- пишем свертку
                else:
                    sT = frozenset({s.tok})
                    X = s.rule.left
                    # фиктивное правило -- пишем HALT
                    if X == '\0':
                        ret[k, sT] = TableAction('', -1, None, True)
                    else:
                        retel = ret.get((k, sT), None)
                        if retel and retel.reduce:
                            raise GrammarParserException('R-R conflict encountered')
                        elif retel is None:
                            ret[k, sT] = TableAction(s.rule.laction, -1, s.rule, False)
        return ret

    def parse(self, s: Iterable[str]) -> bool:
        # выборка элемента таблицы по лексеме
        def choice(s: int, t: str) -> Tuple[int, FrozenSet[str]]:
            for st, tg in filter(lambda x: x[0] == s and t in x[1], self.table):
                return st, tg
            # не нашли (filter пуст)
            return s, frozenset()
        
        sstk: List[int] = [0]
        gstk: List[FrozenSet[str]] = []

        self.disp.reset()
        it = iter(HaltIterable(s))
        t = next(it)

        while True:
            i, tg = choice(sstk[-1], t)
            if not tg: # не нашли (tg пусто, т.е. равно frozenset())
                return False
            ta = self.table[i, tg]
            if ta.halt:
                # выполнить действие при возможности и вернуть его результат
                return not ta.action or self.disp(ta.action, t)
            # в таблице сдвиг
            if ta.shift != -1:
                gstk.append(tg)
                sstk.append(ta.shift)

                if ta.action and not self.disp(ta.action, t):
                    return False
                t = next(it)
            # в таблице свертка
            elif ta.reduce:
                for k in ta.reduce.right:
                    sstk.pop()
                    gstk.pop()
                gstk.append(frozenset({ta.reduce.left}))
                if (sstk[-1], gstk[-1]) not in self.table:
                    return False
                sstk.append(self.table[sstk[-1], gstk[-1]].shift)
                if ta.action and not self.disp(ta.action, t):
                    return False
            # в таблице непонятно что
            # не должно возникать
            else:
                raise GrammarParserException('Fatal error: nonhalt table action without R and S')
        return True
