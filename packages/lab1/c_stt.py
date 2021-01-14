from ..automata import AutomatonActionDispatcher
from typing import List, Tuple, Dict, Callable, Any

class STTDispatcher(AutomatonActionDispatcher):
    # список ключевых слов языка
    keywords = ['long', 'short', 'int', 'double',
                'float', 'bool', 'char']
    # аннотации типов
    FilePos = Tuple[int, int]
    Inner = Callable[[str, str], bool]

    def reset(self) -> None:
        self._stream: List[str] = []
        self.buffer: List[str] = []
        self.line = 1
        self.column = 1
        self.current_token_pos: STTDispatcher.FilePos = (self.line, self.column)
        self._token_pos: List[STTDispatcher.FilePos] = []

    def __init__(self):
        self.reset()

    def __call__(self, s: str, t: str, A: str) -> bool:
        # создаем словарь связанных методов
        actions_map: Dict[str, STTDispatcher.Inner] = {
            'add_char': self.add_char,
            'append': self.append,
            'delim_char': self.delim_char
        }
        # и вызываем нужный
        return actions_map[A](s, t)

    # продвинуть позицию в файле вперед
    def _advance_char(self, t: str) -> None:
        if t == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    # добавить лексему или набор символов в поток
    def _append_to_stream(self) -> None:
        if self.buffer:
            str = ''.join(self.buffer)
            if str in STTDispatcher.keywords:
                self._stream.append(str)
            else:
                # перед идентификаторами и размерностями
                # вставить спец. лексему
                # иначе идущие подряд идентификаторы будут сливаться в один
                self._stream.append('nkw')
                self._stream += self.buffer
            self.token_pos.append(self.current_token_pos)
            self.buffer.clear()

    # при встрече разделителя
    def delim_char(self, s: str, t: str) -> bool:
        self._append_to_stream()
        self._advance_char(t)
        return True

    # при встрече знака пунктуации (скобки, запятые...)
    def append(self, s: str, t: str) -> bool:
        # добавить лексему
        self._append_to_stream()
        # добавить позицию знака
        self.token_pos.append((self.line, self.column))
        # добавить знак в поток
        self._stream.append(t)
        self._advance_char(t)
        return True

    # добавить символ в буфер
    def add_char(self, s: str, t: str) -> bool:
        # если буфер пуст, позиция текущего (первого) символа
        # будет позицией лексемы
        if not self.buffer:
            self.current_token_pos = (self.line, self.column)
        self.buffer.append(t)
        self._advance_char(t)
        return True

    # поток лексем
    @property
    def token_stream(self) -> List[str]:
        return self._stream

    # позиции лексем из потока
    @property
    def token_pos(self) -> List[FilePos]:
        return self._token_pos

    # позиция символа, на котором завершился разбор
    # EOF в случае успешного разбора
    # символ не из алфавита в случае неуспешного разбора
    @property
    def last_char_pos(self) -> FilePos:
        return (self.line, self.column)
