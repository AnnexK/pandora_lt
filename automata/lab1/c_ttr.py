class Dispatcher:
    def reset(self):
        self.tok_counter = 0
        self.buffer = []
        self.ids = set()
        self.duplicate = None

    def __init__(self):
        self.reset()

    def advance(self, s, t):
        self.tok_counter += 1
        if t == ']':
            self.tok_counter += 1
        return True

    def wipe(self, s, t):
        self.buffer.clear()
        return self.advance(s, t)

    def check_id(self, s, t):
        ident = ''.join(self.buffer)
        if ident in self.ids:
            self.duplicate = ident
            return False
        else:
            self.ids.add(ident)
            self.tok_counter += 1
            return self.wipe(s, t)

    def add_char(self, s, t):
        self.buffer.append(t)
        return True

    def __call__(self, s, t, A):
        actions_map = {'advance': self.advance,
                       'add_char': self.add_char,
                       'check_id': self.check_id}
        return actions_map[A](s, t)

    def get_parse_results(self):
        return {'tok_counter': self.tok_counter,
                'duplicate': self.duplicate}


def load_actions():
    return Dispatcher()
