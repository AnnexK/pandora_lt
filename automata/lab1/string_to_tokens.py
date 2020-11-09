class Dispatcher:
    def reset(self):
        self.buffer = []
        self.stream = []
        self.line = 1
        self.column = 0
        self.current_token_pos = None
        self.token_pos = []

    def __init__(self):
        self.reset()

    def __append_and_nil(self, append_t):
        self.token_pos.append(self.current_token_pos)
        self.current_token_pos = None
        if append_t:
            self.token_pos.append((self.line, self.column))

    def advance_char(self, s, t):
        if t == '\n':
            self.line += 1
            self.column = 0
        else:
            self.column += 1
        return True

    def is_var(self, s, t):
        buf = ''.join(self.buffer).upper()
        self.buffer.clear()
        self.stream.append(buf)
        self.__append_and_nil(False)
        self.advance_char(s, t)
        return buf == 'VAR'

    def add_char(self, s, t):
        self.advance_char(s, t)
        if self.current_token_pos is None:
            self.current_token_pos = (self.line, self.column)
        self.buffer.append(t)
        return True

    def add_id_or_idx_to_stream(self, s, t):
        self.advance_char(s, t)
        self.buffer = [s.upper() for s in self.buffer]
        self.stream += self.buffer
        self.stream.append(t)
        self.buffer.clear()
        self.__append_and_nil(True)
        return True

    def add_type_part_to_stream(self, s, t):
        self.advance_char(s, t)
        buf = ''.join(self.buffer).upper()
        self.stream.append(buf)
        self.buffer.clear()
        self.__append_and_nil(False)

        return True

    def add_type_to_stream(self, s, t):
        self.advance_char(s, t)
        buf = ''.join(self.buffer).upper()
        self.stream.append(buf)
        self.buffer.clear()
        self.stream.append(t)
        self.__append_and_nil(True)

        return True

    def add_arr_to_stream(self, s, t):
        self.advance_char(s, t)
        self.stream += self.buffer
        self.buffer.clear()
        self.__append_and_nil(True)

        return True

    def add_dots_to_stream(self, s, t):
        self.advance_char(s, t)
        self.stream.append('..')

        return True

    def add_sc_to_stream(self, s, t):
        self.advance_char(s, t)
        self.stream.append(';')
        self.token_pos.append((self.line, self.column))

        return True

    def __call__(self, s, t, A):
        actions_map = {'advance_char': self.advance_char,
                       'add_char': self.add_char,
                       'is_var': self.is_var,
                       'add_id_or_idx_to_stream': self.add_id_or_idx_to_stream,
                       'add_type_to_stream': self.add_type_to_stream,
                       'add_arr_to_stream': self.add_arr_to_stream,
                       'add_dots_to_stream': self.add_dots_to_stream,
                       'add_sc_to_stream': self.add_sc_to_stream,
                       'add_type_part_to_stream': self.add_type_part_to_stream,}

        return actions_map[A](s, t)

    def get_parse_results(self):
        return {"token_stream": self.stream,
                'token_pos': self.token_pos}


def load_actions():
    return Dispatcher()
