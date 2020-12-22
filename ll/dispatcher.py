class Rule:
    def __init__(self, left):
        self.left = left
        self.right = []
        self.laction = ''
        self.raction = []
        self.nleft = 0
        self.nright = 0


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

    def add_left(self, s, t):
        S = ''.join(self.buffer)
        print(S)
        if S in self.nontermset:
            return False
        self.ruleset.append(Rule(S))
        self.buffer.clear()
        return True

    def add_right(self, s, t):
        r = self.ruleset[-1]
        if self.buffer:
            s = ''.join(self.buffer)
            r.right.append(s)
            self.buffer.clear()
        return True

    def start_right_token(self, s, t):
        r = self.ruleset[-1]
        if len(r.right) > len(r.raction):
            r.raction.append('')
        self.buffer.append(t)
        return True

    def add_rule(self, s, t):
        self.add_right(s, t)
        r = self.ruleset[-1]
        self.nontermset.add(r.left)
        if len(r.right) > len(r.raction):
            r.raction.append('')
        return True

    def add_action_left(self, s, t):
        A = ''.join(self.buffer)
        self.ruleset[-1].laction = A
        self.buffer.clear()
        return True

    def add_action(self, s, t):
        A = ''.join(self.buffer)
        self.ruleset[-1].raction.append(A)
        self.buffer.clear()
        return True

    def add_alt(self, s, t):
        self.add_right(s, t)
        r = self.ruleset[-1]
        newRule = Rule(r.left)

        if len(r.right) > len(r.raction):
            r.raction.append('')
        self.ruleset.append(newRule)
        return True

    def add_empty(self, s, t):
        r = self.ruleset[-1]
        if len(r.right) > len(r.raction):
            r.actions.append('')
        self.ruleset[-1].right.append('')
        return True

    def __call__(self, s, t, A):
        actions_map = {'add_char': self.add_char,
                       'add_right': self.add_right,
                       'add_rule': self.add_rule,
                       'add_alt': self.add_alt,
                       'add_action': self.add_action,
                       'add_action_left': self.add_action_left,
                       'add_empty': self.add_empty,
                       'add_left': self.add_left,
                       'start_right_token': self.start_right_token}
        return actions_map[A](s, t)

    def get_parse_results(self):
        return {'ruleset': self.ruleset,
                'nt_set': self.nontermset}


def load_actions():
    return Dispatcher()
