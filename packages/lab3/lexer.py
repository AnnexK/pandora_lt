from ..ll import LLActionDispatcher
from typing import List, Dict, Tuple


class Dispatcher(LLActionDispatcher):
    keywords = ['long', 'short', 'int', 'double',
                'float', 'bool', 'char', 'namespace',
                'signed', 'unsigned', 'void']
    FilePos = Tuple[int, int]
    def reset(self):
        # поток лексем
        self.stream: List[str] = []
        # буфер символов
        self.buffer: List[str] = []
        # текущая строка и столбец
        self.line: int = 1
        self.column: int = 1
        # положение разбираемой лексемы
        self.current_token_pos: Dispatcher.FilePos = (self.line, self.column)
        # список положений лексем из потока
        self.token_pos: List[Dispatcher.FilePos] = []

    def __init__(self):
        self.reset()

    def __call__(self, A: str, t: str) -> bool:
        actions_map = {'add_char': self.add_char,
                       'append': self.append,
                       'delim_char': self.delim_char,
                       'add_ellipsis': self.add_ellipsis}
        return actions_map[A](t)

    # изменить текущие строку и столбец по символу
    def _advance_char(self, t: str):
        if t == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    # добавить лексему в поток
    def _append_to_stream(self):
        # если буфер не пуст
        if self.buffer:
            # собрать лексему в строку
            str = ''.join(self.buffer)
            # добавить положение лексемы в список положений
            self.token_pos.append(self.current_token_pos)
            # если в буфере ключевое слово, добавить его как есть
            if str in Dispatcher.keywords:
                self.stream.append(str)
            # иначе добавить спецлексему, а затем добавить лексему посимвольно
            else:
                self.stream.append('nkw')
                ln, cl = self.current_token_pos
                for c in self.buffer:
                    self.stream.append(c)
                    self.token_pos.append((ln, cl))
                    cl += 1
            self.buffer.clear()

    # при встрече разделяющего символа
    def delim_char(self, t: str) -> bool:
        self._append_to_stream()
        self._advance_char(t)
        return True

    # при встрече пунктуации
    def append(self, t: str) -> bool:
        self._append_to_stream()
        # добавить знак пунктуации
        self.token_pos.append((self.line, self.column))
        self.stream.append(t)
        self._advance_char(t)
        return True

    # добавить символ в буфер
    def add_char(self, t: str) -> bool:
        # если буфер пуст, установить положение текущего символа как положение лексемы
        if not self.buffer:
            self.current_token_pos = (self.line, self.column)
        self.buffer.append(t)
        self._advance_char(t)
        return True

    # добавить многоточие как одну лексему
    def add_ellipsis(self, t: str) -> bool:
        # начало многоточия на два символа отстаёт от его конца
        self.token_pos.append((self.line, self.column-2))
        self.stream.append('...')
        self.column += 1
        return True

    # позиция символа, на котором разбор остановился
    @property
    def last_char_pos(self):
        return (self.line, self.column)
