import inspect
from copy import deepcopy
from ..automata import Automaton
from .dispatcher import Rule, Dispatcher
from .dispatcher_iface import LLActionDispatcher
import pathlib
from functools import reduce
from operator import or_ as union
from typing import List, Tuple, Dict, Iterator, Iterable, Set


# вычислить S(X) для атома X (терминала или нетерминала)
# с учётом набора правил R и существующих множеств S
def S_single(N, R, S, X):
    # небольшой хак для множеств терминалов
    if X and X[0] == '\1':
        SX = set(X[1:])
        # во множестве X есть нетерминалы
        if SX & N:
            raise GrammarParserException('Non-terminal in terminal range')
        else:
            # S(X) = X, если X - терминал
            return SX
    # S(X) = X, если X - терминал
    if X not in N:
        return {X}
    # иначе S(X) -- объединение всех S правил, где X слева
    else:
        return reduce(union, (s for i, s in enumerate(S)
                              if R[i].left == X))


# вычислить S(A) для цепочки A
def S_chain(N, R, S, A):
    # пустая цепочка входит в S(A), если она входит во все S(x) для x из A
    d = {''} if all('' in S_single(N, R, S, X) for X in A) else set()
    ret = set()
    # перебираем элементы цепочки A и вычисляем для них S
    for X in A:
        sX = S_single(N, R, S, X)
        ret |= sX - {''}
        if '' not in sX:
            break
    return ret | d


# строка таблицы разбора
class TableRow:
    def __init__(self):
        # множество направляющих символов
        self.terminals = set()
        # действие, ассоциированное со строкой
        self.action = ''
        # индекс следующей строки
        self.jump = -1
        # принимается ли данный символ?
        self.accept = False
        # размещать ли строку на стеке?
        self.stack = False
        # генерировать ошибку или перейти к следующей альтернативе?
        self.error = False
        # вместо return используется значение jump

    def __str__(self):
        s = (f"{self.terminals}\t"
             f"{self.action if self.action else 'NIL'}\t"
             f"{self.jump}\t"
             f"{self.accept}\t"
             f"{self.stack}\t"
             f"{self.error}")
        return s

    def __repr__(self):
        return str(self)


# исключение при разборе грамматики
class GrammarParserException(Exception):
    pass


# диспетчер действий по умолчанию
class NilAction(LLActionDispatcher):
    def __init__(self):
        pass

    def __call__(self, A: str, t: str) -> bool:
        return True

    def reset(self):
        pass


# обертка для потока
class HaltIterable:
    def __init__(self, iterable: Iterable[str]):
        self.iterable = iterable

    def __iter__(self) -> Iterator[str]:
        for x in self.iterable:
            yield x
        yield ''


class GrammarParser:
    # путь до XML-файла грамматики
    p = pathlib.Path(__file__).parent / 'grammar.xml'
    D = Dispatcher()
    A = Automaton(str(p), D)
    
    def __init__(self, filename: str, disp: LLActionDispatcher=NilAction()):
        with open(filename) as fp:
            s = fp.read()
        if not GrammarParser.A.parse(s):
            raise GrammarParserException('Not a grammar')
        rules = GrammarParser.D.ruleset
        self.nt = GrammarParser.D.nt
        # пронумеровать правила
        self.enumerate_rules(rules)
        # стартовые символы для правил
        St = self.start_sets(rules)
        # последующие символы для нетерминалов
        Fo = self.follow_sets(rules, St)
        # направляющие символы для правил
        Te = self.term_sets(rules, St, Fo)
        # проверить грамматику на LL
        if not self.isLL(rules, Te):
            raise GrammarParserException('Not an LL(1)-grammar')
        # построить таблицу
        self.table = self.build_table(St, Fo, Te, rules)
        # заменить None в terminals на ''
        self.denonify()
        # установить диспетчер действий
        self.dispatcher = disp

    def enumerate_rules(self, R):
        # счетчик элементов правил
        count = 0
        # индекс правила
        i = 0
        # левая часть предыдущего правила
        prev = R[0].left
        while i < len(R):
            # если встречено правило с той же левой частью, что и предыдущее,
            # пронумеровать его и перейти к следующему
            if R[i].left == prev:
                R[i].nleft = count
                count += 1
                i += 1
            # если же нет, то вернуться к первому правилу с левой частью предыдущего
            # и нумеровать правые части
            else:
                j = i-1
                while j > 0 and R[j-1].left == prev:
                    j -= 1
                while j < i:
                    # номер первого элемента правой части
                    R[j].nright = count
                    # посчитать сразу все элементы правой части
                    count += len(R[j].right)
                    j += 1
                prev = R[i].left
        # нумеровать ненумерованные правила
        j = i-1
        while j > 0 and R[j-1].left == prev:
            j -= 1
        while j < i:
            R[j].nright = count
            count += len(R[j].right)
            j += 1

    def start_sets(self, R):
        # изначально все множества пусты
        S = [set() for i, _ in enumerate(R)]
        # были ли изменения множеств
        new = True
        while new:
            new = False
            # новый набор множеств
            curS = []
            # для каждого множества из старого набора
            # вычислить новое множество
            for i, s in enumerate(S):
                Sn = S_chain(self.nt, R, S, R[i].right)
                # если новое множество не является подмножеством старого,
                # значит, произошли изменения
                if not Sn <= s:
                    new = True
                # добавить объединение старого и нового множества
                curS.append(s | Sn)
            # обновить набор множеств
            S = curS
        return S

    def follow_sets(self, R, St):
        # изначально все множества пусты
        S = {n: set() for n in self.nt}
        # кроме множества стартового нетерминала:
        # у него есть символ конца цепочки (None)
        S[R[0].left].add(None)
        new = True
        while new:
            new = False
            # новый набор множеств
            curS = deepcopy(S)
            # для каждого нетерминала N
            for n in S:
                # для каждого правила r
                for r in R:
                    # для правой части правила
                    for i in range(len(r.right)):
                        # если правило вида
                        # X -: a N b
                        # то вычислить S(b)
                        # a, b -- подцепочки (возможно, пустые)
                        if n == r.right[i]:
                            chain = r.right[i+1:]
                            
                            s = S_chain(self.nt, R, St, chain)
                            # если цепочка b пуста или в S(b) есть пустая строка,
                            # то добавить к S(b) S(X)
                            if not chain or '' in s:
                                s |= S[r.left]
                            # удалить пустую цепочку, если она там есть
                            s -= {''}
                            # произошли изменения
                            if not s <= S[n]:
                                new = True
                            # объединить со старым множеством
                            curS[n] |= s
            S = curS
        return S

    def term_sets(self, R, St, Fo):
        # извлечь из каждого множества стартовых символов пустую строку
        S = [St[i]-{''} for i, _ in enumerate(R)]
        # а затем добавить F(X) если пустая строка в стартах была
        S = [S[i] | Fo[R[i].left] if '' in St[i] else S[i] for i, _ in enumerate(R)]
        return S

    def isLL(self, R, Te):
        # проверить пересечения разных множеств с одинаковыми левыми частями, вот и все
        for i, ti in enumerate(Te):
            for j, tj in enumerate(Te):
                if i != j and R[i].left == R[j].left and ti & tj:
                    return False
        return True

    def build_table(self, St, Fo, Te, R):
        # множество индексов левых частей
        Ml = set(r.nleft for r in R)
        # множество индексов крайних правых частей
        Mr = set(r.nright+len(r.right)-1 for r in R)
        # таблица
        table = [TableRow() for i in range(max(Mr)+1)]
        for i, r in enumerate(R):
            # заполняем левую часть таблицы
            n = r.nleft
            table[n].terminals = Te[i]
            table[n].action = r.laction
            # переход к правой части
            table[n].jump = r.nright
            # так как нетерминал
            table[n].accept = False
            # так как слева
            table[n].stack = False
            # если следующий символ -- не альтернатива слева, то ошибка генерируется
            table[n].error = n+1 not in Ml
            # заполняем правую часть таблицы
            n = r.nright
            for k, tk in enumerate(r.right):
                # terminals
                # пустая строка
                if not tk:
                    table[n+k].terminals = Te[i]
                # уже готовое множество символов
                elif tk[0] == '\1':
                    table[n+k].terminals = set(tk[1:])
                # одиночный терминал
                elif tk not in self.nt:
                    table[n+k].terminals = {tk}
                # нетерминал
                else:
                    chain = r.right[k:]
                    S = S_chain(self.nt, R, St, chain)
                    if '' in S:
                        S |= Fo[r.left]
                    S -= {''}
                    table[n+k].terminals = S
                table[n+k].action = r.raction[k]

                # jump
                # терминал, множество терминалов или пустая строка
                if tk not in self.nt:
                    table[n+k].jump = n+k+1 if n+k not in Mr else -1
                # нетерминал
                else:
                    # ищем первое правило с этим нетерминалом слева
                    for j, r2 in enumerate(R):
                        if r2.left == tk:
                            table[n+k].jump = r2.nleft
                            break
                
                # терминалы и множества терминалов
                table[n+k].accept = tk and tk not in self.nt
                # не крайние справа нетерминалы
                # то, что они не слева, уже и так понятно
                table[n+k].stack = tk in self.nt and n+k not in Mr
                # ошибка для правых частей генерируется всегда
                table[n+k].error = True
        return table

    # заменить None на '' в множествах направляющих символов
    def denonify(self):
        for t in self.table:
            if None in t.terminals:
                t.terminals -= {None}
                t.terminals.add('')

    # разбор потока лексем
    def parse(self, token_stream):
        self.dispatcher.reset()
        # стек с возвратами и действиями при возврате
        stk = []
        s = HaltIterable(token_stream)
        # начинаем с первой строки таблицы
        tab = 0
        
        it = iter(s)
        # начинаем с первой лексемы в потоке
        token = next(it)
        stk.append((-1, []))

        while True:
            # достаем строку таблицы
            t = self.table[tab]
            if token in t.terminals:
                if t.accept: # терминалы
                    # выполнить действие над терминалом
                    A = t.action
                    if A and not self.dispatcher(A, token):
                        return False
                    # перейти к следующему символу
                    token = next(it)
                # положить на стек номер строки и действие
                if t.stack:
                    stk.append((tab, [t.action]))
                # если не терминал/пустая строка в конце правила
                if t.jump >= 0:
                    # если терминал слева или в конце правила,
                    # добавить действие в стек действий для вершины стека
                    if not t.accept and not t.stack:
                        stk[-1][1].append(t.action)
                    tab = t.jump
                else: # t.jump == -1
                    # выполнить действие для пустой строки
                    if not t.accept:
                        A = t.action
                        if A and not self.dispatcher(A, token):
                            return False
                    # снять со стека номер строки и действия
                    tab, A = stk.pop()
                    # выполнить действия в порядке, обратном порядку размещения
                    while A:
                        a = A.pop()
                        if a and not self.dispatcher(a, token):
                            return False
                    if tab < 0:
                        break
                    tab += 1
                    continue

            elif not t.error:
                tab += 1
            else:
                break
        return not token and not stk
