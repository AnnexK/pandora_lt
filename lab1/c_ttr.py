from automata import AutomatonActionDispatcher
from typing import List, Dict, Set, Optional, Callable, Any


class TTRDispatcher(AutomatonActionDispatcher):
    Inner = Callable[[str, str], bool]
    def reset(self) -> None:
        # счетчик разобранных лексем
        # когда внедренное действие начинает выполняться,
        # указывает на лексему, переданную действию
        # как аргумент
        self.tok_counter = 0
        # буфер символов
        self.buffer: List[str] = []
        # множество распознанных идентификаторов
        self.ids: Set[str] = set()
        # если возникает ошибка дублицирования идентификаторов,
        # здесь будет дублицированная лексема
        self._duplicate: str = ''
        # флаг разбора неключевого слова
        self.nkw: bool = False

    def __init__(self):
        self.reset()

    # продвинуть счетчик лексем на 1
    def advance(self, s: str, t: str) -> bool:
        self.tok_counter += 1
        # следующая лексема потенциально ключевое слово
        # снять флаг
        self.nkw = False
        return True

    # очистить буфер
    def wipe(self, s: str, t: str) -> bool:
        self.buffer.clear()
        return self.advance(s, t)

    # проверить идентификатор на присутствие
    # во множестве распознанных идентификаторов
    def check_id(self, s: str, t: str) -> bool:
        ident: str = ''.join(self.buffer)
        if ident in self.ids:
            self._duplicate = ident
            return False
        else:
            self.ids.add(ident)
            return self.wipe(s, t)

    # добавить символ в буфер
    # не продвигает счетчик лексем (идентификатор считается одной лексемой)
    def add_char(self, s: str, t: str) -> bool:
        self.buffer.append(t)
        return True

    # установить флаг неключевого слова
    def nkw_set(self, s: str, t: str) -> bool:
        self.nkw = True
        self.tok_counter += 1
        return True

    # выбросить ошибку и сбросить флаг
    # выполняется, когда встречается лексема "неключевое слово"
    # после символа идентификатора
    # и делает так, что err_tok указывает на второй (ошибочный)
    # идентификатор
    def nkw_err(self, s: str, t: str) -> bool:
        self.nkw = False
        return False

    def __call__(self, s: str, t: str, A: str) -> bool:
        actions_map: Dict[str, TTRDispatcher.Inner] = {
            'advance': self.advance,
            'add_char': self.add_char,
            'check_id': self.check_id,
            'nkw_set': self.nkw_set,
            'nkw_err': self.nkw_err,
            'wipe': self.wipe
        }
        return actions_map[A](s, t)

    # номер лексемы, которая вызвала ошибку
    @property
    def err_tok(self) -> int:
        # если ошибка возникла во время разбора неключевого слова,
        # указывает на начало неключевого слова
        # иначе указывает на ошибочную лексему
        return self.tok_counter-int(self.nkw)
    
    # дублицированный идентификатор
    @property
    def duplicate(self) -> str:
        return self._duplicate
