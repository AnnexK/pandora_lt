from typing import List, Iterator, Set, Dict, Callable, Union
from functools import reduce
from operator import or_ as union
from ..automata import AutomatonActionDispatcher


class Rule:
    def __init__(self, left: str, laction: str):
        self.left = left
        self.laction = laction
        self.right: List[str] = []
        self.raction: List[str] = []
        self.start: Set[str] = set()


# интервал терминал-символ
# или одиночный терминал-символ
# в множествах терминалов-символов
# (квадратные скобки в грамматике)
class CharRange:
    def __init__(self, left: str, right: str):
        # left -- символ, если его длина равна 1
        ischar = len(left) == 1 and len(right) == 1
        # слева или справа не символ и это не одна и та же строка
        if not ischar:
            raise ValueError('strings must be of length 1')
        # символы не по порядку
        if ischar and ord(left) > ord(right):
            raise ValueError('chars are out of order')
        self.left = left
        self.right = right
    
    # проверка на вхождение s в множество
    def __contains__(self, s: str) -> bool:
        inrange = ord(self.left) <= ord(s) <= ord(self.right)
        return inrange

    # итерация по элементам множества
    def __iter__(self) -> Iterator[str]:
        for i in range(ord(self.left), ord(self.right)+1):
            yield chr(i)

    def __str__(self) -> str:
        return f'{self.left}-{self.right}'

    
# множество терминалов-символов,
# представленное в наборе правил одной частью правила
# состоит из нескольких интервалов
class CharSet:
    def __init__(self):
        self.rngs: List[CharRange] = []

    # добавить интервал от l до r включительно
    def append(self, l: str, r: str):
        self.rngs.append(CharRange(l, r))

    # символ есть во множестве
    # если он есть хотя бы в одном из интервалов
    def __contains__(self, s: str) -> bool:
        return any(s in r for r in self.rngs)

    # итерация
    def __iter__(self) -> Iterator[str]:
        s = reduce(union, (set(r) for r in self.rngs))
        for x in s:
            yield x
    
    # пусто ли множество?
    def __bool__(self) -> bool:
        return bool(self.rngs)

    def __str__(self) -> str:
        return f"\1{''.join(x for x in self)}"


# диспетчер действий для автомата, выполняющего разбор грамматики
class Dispatcher(AutomatonActionDispatcher):
    def reset(self) -> None:
        # принимает ли разбираемая грамматика пустую цепочку
        self.accepts_empty = False
        # множество распознанных нетерминалов
        # (левых частей правил)
        self.nontermset: Set[str] = set()
        # множество всех элементов грамматики
        self.elemset: Set[str] = set()
        # упорядоченный набор правил
        self._ruleset: List[Rule] = []
        # буфер символов
        self.buffer: List[str] = []
        # действие, выполняемое над левой частью по умолчанию
        # X <main_action> -: <specific_action_1> Y Z | R | <specific_action2> e d
        self.main_action: str = ''
        # левая часть предыдущего неальтернативного правила
        # для возможности описания альтернатив как отдельных правил
        # (не через |)
        self.prev_left = ''
        # множество символов-терминалов
        self.charset = CharSet()
        # (разбор интервалов) предыдущий символ в интервале
        self.prev_charset_char = ''
    
    def __init__(self):
        self.reset()

    # установить флаг приема пустых цепочек
    def set_empty(self, s: str, t: str) -> bool:
        self.accepts_empty = True
        return True
    
    # добавить символ в буфер
    def add_char(self, s: str, t: str) -> bool:
        self.buffer.append(t)
        return True

    # экранировать символ и добавить его в буфер
    # \n преобразуется в newline,
    # \t - в табуляцию
    # остальные символы добавляются как есть
    def escape(self, s: str, t: str) -> bool:
        r = self._ruleset[-1]
        # уравнять количество действий с количеством правил справа
        if len(r.right) > len(r.raction):
            r.raction.append('')
        escapees = {'n': '\n', 't': '\t'}
        return self.add_char(s, escapees.get(t, t))

    # добавить новое правило со сформированной левой частью
    def add_left(self, s: str, t: str) -> bool:
        S = ''.join(self.buffer)
        self.elemset.add(S)
        # разрыв в правилах с одинаковыми левыми частями:
        # X -: ...
        # X -: ...
        # Y -: ...
        # ...
        # Z -: ...
        # X -: ... -- ошибка
        if S != self.prev_left and S in self.nontermset:
            return False
        R = Rule(S, self.main_action)
        self._ruleset.append(R)
        self.buffer.clear()
        return True

    # добавить элемент правой части
    def add_right(self, s: str, t: str) -> bool:
        r = self._ruleset[-1]
        if self.buffer:
            s = ''.join(self.buffer)
            self.elemset.add(s)
            r.right.append(s)
            self.buffer.clear()
        return True

    # начать новый элемент правой части
    def __srtc(self, s: str, t: str, m: Callable[[str, str], bool]) -> bool:
        r = self._ruleset[-1]
        if len(r.right) > len(r.raction):
            r.raction.append('')
        return m(s, t)

    # альтернатива srtc без экранирования первого символа
    def start_right_token(self, s: str, t: str) -> bool:
        return self.__srtc(s, t, self.add_char)

    # альтернатива srtc c экранированием первого символа
    def start_right_token_esc(self, s: str, t: str) -> bool:
        return self.__srtc(s, t, self.escape)

    # окончательно добавить правило
    def add_rule(self, s: str, t: str) -> bool:
        # собрать буфер в последний элемент правой части
        self.add_right(s, t)
        r = self._ruleset[-1]
        # добавить левую часть во множество нетерминалов
        self.nontermset.add(r.left)
        self.prev_left = r.left
        # добавить действие для последнего элемента
        if len(r.right) > len(r.raction):
            r.raction.append('')
        # сбросить действие по умолчанию
        self.main_action = ''
        return True

    # добавить действие к левой части правила
    def add_action_left(self, s: str, t: str) -> bool:
        A = ''.join(self.buffer)
        self._ruleset[-1].laction = A
        self.buffer.clear()
        return True

    # добавить действие к последнему распознанному элементу правой части правила
    def add_action(self, s: str, t) -> bool:
        A = ''.join(self.buffer)
        self._ruleset[-1].raction.append(A)
        self.buffer.clear()
        return True

    # добавить альтернативное правило
    # (с уже сформированной левой частью)
    def add_alt(self, s: str, t: str) -> bool:
        self.add_right(s, t)
        r = self._ruleset[-1]
        newRule = Rule(r.left, self.main_action)

        if len(r.right) > len(r.raction):
            r.raction.append('')
        self._ruleset.append(newRule)
        return True

    # добавить действие по умолчанию к левой части правила
    def add_main_action(self, s: str, t: str) -> bool:
        self.main_action = ''.join(self.buffer)
        self.ruleset[-1].laction = self.main_action
        self.buffer.clear()
        return True

    # начать множество терминалов
    def start_charset(self, s: str, t: str) -> bool:
        # добавить к правой части недостающее действие
        self.__srtc(s, t, lambda s, t: True)  
        self.add_right(s, t)
        return True

    # установить левый символ интервала
    def set_left_char(self, s: str, t: str) -> bool:
        c = self.prev_charset_char
        # если символ установлен заранее,
        # добавить его в множество
        if self.prev_charset_char:
            self.charset.append(c, c)
        self.prev_charset_char = t
        return True
    
    # то же, что выше, только с экранированием
    def set_left_char_esc(self, s: str, t: str) -> bool:
        # добавить в буфер экранированный символ
        self.escape(s, t)
        # извлечь символ из буфера
        t = self.buffer[0]
        self.buffer.clear()
        return self.set_left_char(s, t)
    
    # создать новый интервал
    def set_charrange(self, s: str, t: str) -> bool:
        try:
            # добавить интервал от предыдущего символа до t
            self.charset.append(self.prev_charset_char, t)
            # сбросить предыдущий символ
            self.prev_charset_char = ''
            return True
        # символы в неверном порядке
        except ValueError as e:
            return False
    
    # см выше только с экранированием
    def set_charrange_esc(self, s: str, t: str) -> bool:
        self.escape(s, t)
        t = self.buffer[0]
        self.buffer.clear()
        return self.set_charrange(s, t)
    
    # добавить множество символов в правило
    def add_range(self, s: str, t: str) -> bool:
        # добавить недобавленный символ во множество
        c = self.prev_charset_char
        if c:
            self.charset.append(c, c)
            self.prev_charset_char = ''
        # если множество непусто
        if self.charset:
            # создать из него обычное множество строк
            cs = str(self.charset)
            self.elemset.add(cs)
            # и добавить его в правило
            r = self.ruleset[-1]
            r.right.append(cs)
            self.charset = CharSet()
            self.prev_left = ''
        return True

    def __call__(self, s: str, t: str, A: str) -> bool:
        actions_map = {'add_char': self.add_char,
                       'add_right': self.add_right,
                       'add_rule': self.add_rule,
                       'add_alt': self.add_alt,
                       'add_action': self.add_action,
                       'add_action_left': self.add_action_left,
                       'set_empty': self.set_empty,
                       'add_left': self.add_left,
                       'start_right_token': self.start_right_token,
                       'start_right_token_esc': self.start_right_token_esc,
                       'add_main_action': self.add_main_action,
                       'start_charset': self.start_charset,
                       'set_left_char': self.set_left_char,
                       'set_left_char_esc': self.set_left_char_esc,
                       'set_charrange': self.set_charrange,
                       'set_charrange_esc': self.set_charrange,
                       'add_range': self.add_range,
                       'escape': self.escape}
        return actions_map[A](s, t)

    @property
    def ruleset(self) -> List[Rule]:
        return self._ruleset
    
    @property
    def nt(self) -> Set[str]:
        return self.nontermset

    @property
    def empty(self) -> bool:
        return self.accepts_empty