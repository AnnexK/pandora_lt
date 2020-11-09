class Dispatcher:
    def reset(self):
        self.token_counter = 0
        self.buffer = []
        self.id_set = set()
        self.number = 0
        self.first = 0
        self.second = 0
        self.sign = 1

    def __init__(self):
        self.reset()

    def advance_token(self, s, t):
        self.token_counter += 1
        return True

    def add_char(self, s, t):
        self.buffer.append(t)
        return True

    def put_id(self, s, t):
        ident = ''.join(self.buffer)
        if ident in self.id_set:
            return False
        self.id_set.add(ident)
        self.buffer.clear()
        self.token_counter += 2
        return True

    def add_digit(self, s, t):
        self.number = self.number*10 + int(t)
        return True

    def fix_string(self, s, t):
        if self.number > 255:
            return False
        self.number = 0
        self.token_counter += 2
        return True

    def change_multiplier(self, s, t):
        if t == '-':
            self.multiplier = -self.multiplier
        return True

    def fix_first(self, s, t):
        self.first = self.sign*self.number
        self.sign = 1
        self.number = 0
        self.token_counter += 2
        return True

    def fix_second(self, s, t):
        self.second = self.sign*self.number
        self.sign = 1
        self.number = 0
        if self.second < self.first:
            print(self.second, ' ', self.first)
            return False
        self.first = self.second = 0
        self.token_counter += 2
        return True

    def __call__(self, s, t, A):
        actions_map = { 'advance_token': self.advance_token,
                        'add_char': self.add_char,
                        'put_id': self.put_id,
                        'add_digit': self.add_digit,
                        'fix_string': self.fix_string,
                        'change_multiplier': self.change_multiplier,
                        'fix_first': self.fix_first,
                        'fix_second': self.fix_second }
        return actions_map[A](s,t)

    def get_parse_results(self):
        return { 'tokens': self.token_counter }


def load_actions():
    return Dispatcher()
