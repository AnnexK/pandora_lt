from ..automata import AutomatonActionDispatcher
from typing import List, Set, Callable, Iterator
from operator import or_ as union
from functools import reduce


class Rule:
    def __init__(self, left, laction):
        self.left = left
        self.right = []
        self.laction = laction
        self.raction = []
        self.nleft = 0
        self.nright = 0


class CharRange:
    def __init__(self, left: str, right: str):
        ischar = len(left) == 1
        if not ischar and left != right:
            raise ValueError('strings must be of length 1 (or be equal)')
        if ischar and ord(left) > ord(right):
            raise ValueError('chars are out of order')
        self.left = left
        self.right = right
    
    def __contains__(self, s: str) -> bool:
        iseq = self.left == self.right == s
        inrange = not iseq and ord(self.left) <= ord(s) <= ord(self.right)
        return iseq or inrange

    def __iter__(self) -> Iterator[str]:
        if self.left == self.right:
            yield self.left
        else:
            for i in range(ord(self.left), ord(self.right)+1):
                yield chr(i)

    def __str__(self) -> str:
        return self.left if self.left==self.right else f'{self.left}-{self.right}'

    
class CharSet:
    def __init__(self):
        self.rngs: List[CharRange] = []

    def append(self, l: str, r: str):
        self.rngs.append(CharRange(l, r))

    def __contains__(self, s: str) -> bool:
        return any(s in r for r in self.rngs)

    def __iter__(self) -> Iterator[str]:
        s = reduce(union, (set(r) for r in self.rngs))
        for x in s:
            yield x
    
    def __bool__(self) -> bool:
        return bool(self.rngs)

    def __str__(self) -> str:
        return f"[{''.join(str(x) for x in self.rngs)}]"


class Dispatcher(AutomatonActionDispatcher):
    def reset(self) -> None:
        self.nontermset: Set[str] = set()
        self._ruleset: List[Rule] = []
        self.buffer: List[str] = []
        self.main_action: str = ''
        self.prev_left = ''
        self.charset = CharSet()
        self.prev_charset_char = ''
    
    def __init__(self):
        self.reset()

    def add_char(self, s: str, t: str) -> bool:
        self.buffer.append(t)
        return True

    def escape(self, s: str, t: str) -> bool:
        escapees = {'n': '\n', 't': '\t'}
        return self.add_char(s, escapees.get(t, t))

    def add_left(self, s: str, t: str) -> bool:
        S = ''.join(self.buffer)
        print(S)
        if S != self.prev_left and S in self.nontermset:
            return False
        R = Rule(S, self.main_action)
        self._ruleset.append(R)
        self.buffer.clear()
        return True

    def add_right(self, s: str, t: str) -> bool:
        r = self._ruleset[-1]
        if self.buffer:
            s = ''.join(self.buffer)
            r.right.append(s)
            self.buffer.clear()
        return True

    def __srtc(self, s: str, t: str, m: Callable[[str, str], bool]) -> bool:
        r = self._ruleset[-1]
        if len(r.right) > len(r.raction):
            r.raction.append('')
        return m(s, t)

    def start_right_token(self, s: str, t: str) -> bool:
        return self.__srtc(s, t, self.add_char)

    def start_right_token_esc(self, s: str, t: str) -> bool:
        return self.__srtc(s, t, self.escape)

    def add_rule(self, s: str, t: str) -> bool:
        self.add_right(s, t)
        self.add_range(s, t)
        r = self._ruleset[-1]
        self.nontermset.add(r.left)
        self.prev_left = r.left
        if len(r.right) > len(r.raction):
            r.raction.append('')
        self.main_action = ''
        return True

    def add_action_left(self, s: str, t: str) -> bool:
        A = ''.join(self.buffer)
        self._ruleset[-1].laction = A
        self.buffer.clear()
        return True

    def add_action(self, s: str, t) -> bool:
        A = ''.join(self.buffer)
        self._ruleset[-1].raction.append(A)
        self.buffer.clear()
        return True

    def add_alt(self, s: str, t: str) -> bool:
        self.add_right(s, t)
        r = self._ruleset[-1]
        newRule = Rule(r.left, self.main_action)

        if len(r.right) > len(r.raction):
            r.raction.append('')
        self._ruleset.append(newRule)
        return True

    def add_main_action(self, s: str, t: str) -> bool:
        self.main_action = ''.join(self.buffer)
        self.ruleset[-1].laction = self.main_action
        self.buffer.clear()
        return True

    def add_empty(self, s: str, t: str) -> bool:
        r = self._ruleset[-1]
        if len(r.right) > len(r.raction):
            r.raction.append('')
        self._ruleset[-1].right.append('')
        return True

    def start_charset(self, s: str, t: str) -> bool:
        self.__srtc(s, t, lambda s, t: True)  
        self.add_right(s, t)
        return True     

    def set_left_char(self, s: str, t: str) -> bool:
        c = self.prev_charset_char
        if self.prev_charset_char:
            self.charset.append(c, c)
        self.prev_charset_char = t
        return True
    
    def set_left_char_esc(self, s: str, t: str) -> bool:
        self.escape(s, t)
        t = self.buffer[0]
        self.buffer.clear()
        return self.set_left_char(s, t)
    
    def set_charrange(self, s: str, t: str) -> bool:
        try:
            self.charset.append(self.prev_charset_char, t)
            self.prev_charset_char = ''
            return True
        except ValueError as e:
            print(e)
            return False
    
    def set_charrange_esc(self, s: str, t: str) -> bool:
        self.escape(s, t)
        t = self.buffer[0]
        self.buffer.clear()
        return self.set_charrange(s, t)
    
    def add_range(self, s: str, t: str) -> bool:
        if self.charset:
            cs = set(self.charset)
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
                       'add_empty': self.add_empty,
                       'add_left': self.add_left,
                       'start_right_token': self.start_right_token,
                       'start_right_token_esc': self.start_right_token_esc,
                       'add_main_action': self.add_main_action,
                       'start_charset': self.start_charset,
                       'set_left_char': self.set_left_char,
                       'set_left_char_esc': self.set_left_char_esc,
                       'set_charrange': self.set_charrange,
                       'set_charrange_esc': self.set_charrange,
                       'add_range': self.add_range}
        return actions_map[A](s, t)

    @property
    def ruleset(self) -> List[Rule]:
        return self._ruleset
    
    @property
    def nt(self) -> Set[str]:
        return self.nontermset
