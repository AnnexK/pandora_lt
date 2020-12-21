class Rule:
    def __init__(self, left):
        self.left = left
        self.right = []
        self.actions = []
        self.nleft = 0
        self.nright = 0
        self.start = []
        self.follow = []
        self.terms = []


class Dispatcher:
    def reset(self):
        self.nontermset = set()
        self.ruleset = []
        self.buffer = []
        
    def __init__(self):
        self.reset()

    def add_char(self, s, t):
        self.buffer.append(t)
        return True

    def add_left(self):
        s = ''.join(self.buffer)
        if s in self.nontermset:
            return False
        self.ruleset.append(Rule(s))
        self.buffer.clear()
        return True

    def start_right(self, s, t):
        # Если буфер не пуст, значит, новое правило не было
        # добавлено, попробовать добавить новое правило
        if self.buffer and not self.add_left():
            return False
        if not self.ruleset[-1].actions:
            self.ruleset[-1].actions.append('')
        print(self.ruleset[-1].actions)
        return True

    def append_nt(self, s, t):
        return self.add_left()

    def add_right(self, s, t):
        r = self.ruleset[-1]
        if self.buffer:
            s = ''.join(self.buffer)
            r.right.append(s)
            self.buffer.clear()
        if len(r.right) == len(r.actions):
            r.actions.append('')
        return True

    def add_rule(self, s, t):
        self.add_right(s, t)
        r = self.ruleset[-1]
        if len(r.right) == len(r.actions):
            r.actions.append('')
        self.nontermset.add(r.left)
        return True

    def add_action(self, s, t):
        A = ''.join(self.buffer)
        self.ruleset[-1].actions.append(A)
        self.buffer.clear()
        return True

    def add_alt(self, s, t):
        self.add_right(s, t)
        newRule = Rule(self.ruleset[-1].left)
        newRule.actions.append(self.ruleset[-1].actions[0])
        self.ruleset.append(newRule)
        return True

    def add_empty(self, s, t):
        r = self.ruleset[-1]
        if len(r.right) > len(r.actions):
            r.actions.append('')
        self.ruleset[-1].right.append('')
        return True

    def __call__(self, s, t, A):
        actions_map = {'add_char': self.add_char,
                       'append_nt': self.append_nt,
                       'add_right': self.add_right,
                       'add_rule': self.add_rule,
                       'add_alt': self.add_alt,
                       'add_action': self.add_action,
                       'add_empty': self.add_empty,
                       'start_right': self.start_right}
        return actions_map[A](s, t)

    def get_parse_results(self):
        return {'ruleset': self.ruleset,
                'nt_set': self.nontermset}


def load_actions():
    return Dispatcher()
