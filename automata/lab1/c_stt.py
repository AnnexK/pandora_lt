class Dispatcher:
    keywords = ['long', 'short', 'int', 'double',
                'float', 'bool', 'char']

    def reset(self):
        self.stream = []
        self.buffer = []
        self.line = 1
        self.column = 1
        self.current_token_pos = None
        self.token_pos = []
        self.nkw = False

    def __init__(self):
        self.reset()

    def _advance_char(self, t):
        if t == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def _append_to_stream(self):
        if self.buffer:
            str = ''.join(self.buffer)
            if str in Dispatcher.keywords:
                self.stream.append(str)
            else:
                self.nkw = True
                self.stream += self.buffer
            self.token_pos.append(self.current_token_pos)
            self.current_token_pos = None
            self.buffer.clear()

    def delim_char(self, s, t):
        self._append_to_stream()
        self._advance_char(t)
        return True

    def append(self, s, t):
        self._append_to_stream()
        self.nkw = False
        self.token_pos.append((self.line, self.column))
        self.stream.append(t)
        self._advance_char(t)
        return True

    def add_char(self, s, t):
        if self.nkw:
            return False
        if not self.buffer:
            self.current_token_pos = (self.line, self.column)
        self.buffer.append(t)
        self._advance_char(t)
        return True

    def __call__(self, s, t, A):
        actions_map = {'add_char': self.add_char,
                       'append': self.append,
                       'delim_char': self.delim_char}
        return actions_map[A](s, t)

    def get_parse_results(self):
        return {'token_stream': self.stream,
                'token_pos': self.token_pos,
                'file_pos': (self.line, self.column)}


def load_actions():
    return Dispatcher()

