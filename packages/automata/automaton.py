import xml.etree.ElementTree as xml
from typing import Any, Dict, Set, Iterable, Iterator, Tuple
from .dispatcher import AutomatonActionDispatcher



class DescriptionParseError(Exception):
    pass


class Automaton:
    # символ конца последовательности лексем/символов
    # используется пустая строка, так как пустая строка
    # заведомо не может быть лексемой
    HALT = ''
    # тип данных "таблица переходов" для хинтов
    # описание см. комментарий к Automaton.__parse_transitions
    TransitionTable = Dict[Tuple[str, str], Tuple[str, str]]

    # обёртка, добавляющая в конец iterable символ конца последовательности
    class HaltIterable:
        def __init__(self, iterable: Iterable[str]):
            self.iterable = iterable

        # возвращает генератор,
        # при итерации по которому сначала возвращаются
        # элементы iterable по порядку,
        # а затем возвращается конец последовательности
        def __iter__(self) -> Iterator[str]:
            for x in self.iterable:
                yield x
            yield Automaton.HALT

    # ничего не делающий диспетчер действий
    # применяется по умолчанию, если у автомата нет действий
    # не возвращает результаты разбора
    class NilFunction(AutomatonActionDispatcher):
        def __init__(self):
            pass

        # всегда возвращать true и ничего не делать
        def __call__(self, state: str, token: str, action: str) -> bool:
            return True

        # нет состояния -- нечего сбрасывать
        def reset(self) -> None:
            pass

    # разобрать состояния в xml файле
    # S -- кусок дерева xml, содержащий описания состояний:
    # <states>
    #   <s>q1</s>
    #   ...
    #   <s>qn</s>
    # </states>
    # точный тип S неизвестен
    # возвращает множество состояний
    def __parse_states(self, S) -> Set[str]:
        ret = set()
        # s представляет кусок дерева, содержащий имя состояния:
        # <s>state_name</s>
        for s in S:
            if s.tag != 's':
                raise DescriptionParseError('Wrong tag encountered')
            elif s not in ret:
                ret.add(s.text)
            else:
                raise DescriptionParseError('Encountered duplicate state: '
                                            f'{s.text}')

        return ret

    # разобрать лексемы и группы, в которые лексемы входят
    # T -- кусок дерева xml, содержащий группы лексем и 
    # входящие в них лексемы:
    # <tokens>
    #   <tg name="tokengroup1">
    #     <t>t1</t>
    #     ...
    #     <t>tn</t>
    #   </tg>
    #   ...
    # </tokens>
    # группа лексем может быть пустой, т.е. не содержать
    # записей о лексемах
    # подразумевается, что такая группа содержит только одну
    # лексему, совпадающую с именем группы
    # группы лексем не должны пересекаться
    # точный тип T неизвестен
    # возвращает отображение лексем в группы лексем
    def __parse_tokens(self, T) -> Dict[str, str]:
        # отображение
        token_map = dict()
        # конец потока лексем отображается в одноименную группу
        token_map[Automaton.HALT] = Automaton.HALT
        for group in T:
            if group.tag != 'tg':
                raise DescriptionParseError('Wrong tag encountered, '
                                            'expected tg')
            groupname = group.attrib['name']
            for t in group:
                if t.tag != 't':
                    raise DescriptionParseError('Wrong tag encountered, '
                                                'expected t')
                if t.text not in token_map:
                    token_map[t.text] = groupname
                else:
                    raise DescriptionParseError('Token duplicate encountered: '
                                                f'{t.text}')
            # если группа пуста, попробовать добавить в нее лексему с тем же содержимым
            if not group:
                if groupname not in token_map:
                    token_map[groupname] = groupname
                else:
                    raise DescriptionParseError(f'Group {groupname} cannot '
                                                'be empty: '
                                                f'token {groupname} exists')
        return token_map

    # разобрать переходы
    # Tr -- кусок дерева, содержащий переходы:
    # <transitions>
    #   <tr start="qx" token="t" end="qy" action="a1"/>
    #   ...
    # </transitions>
    # start и end должны быть во множестве состояний
    # token (имя группы) должна существовать
    # (должна быть хотя бы одна лексема, отображающаяся в имя группы)
    # action необязателен (если он отсутствует, предполагается, что
    # никакое действие не выполняется)
    # переход по концу последовательности обозначается пустой строкой в tg
    # end в таком случае может быть любым
    # точный тип Tr неизвестен
    # возвращает отображение пар (состояние, группа_лексем) в пары
    # (состояние, действие) TransitionTable
    def __parse_transitions(self, Tr) -> TransitionTable:
        token_groups = set(self.token_map[tg] for tg in self.token_map)
        ret = dict()
        for t in Tr:
            if t.tag != 'tr':
                raise DescriptionParseError('Wrong tag encountered')
            else:
                s = t.attrib['start']
                if s not in self.states:
                    raise DescriptionParseError('State not in state set:'
                                                f' {s}')
                tg = t.attrib['token']
                if tg not in token_groups:
                    raise DescriptionParseError('Token group not in token map:'
                                                f' {tg}'
                                                f'Token groups found: {token_groups}')
                # уже есть переход из s по tg -- ошибка
                if (s, tg) in ret:
                    raise DescriptionParseError('Transition ambiguity '
                                                f'encountered at {(s, tg)}')
                else:
                    # получить из attrib имя действия (по ключу action)
                    # если ключа action в attrib нет, то вернуть пустую строку
                    # (отсутствие действия)
                    action_name = t.attrib.get('action', '')
                    end = t.attrib['end']
                    # end нет во множестве состояний и tg не конец последовательности -- ошибка
                    if end not in self.states and tg != self.HALT and end != self.HALT:
                        raise DescriptionParseError('State not in state set: '
                                                    f'{end} (and is not HALT)')
                    ret[s, tg] = end, action_name

        # отсутствует переход по концу последовательности -- ошибка
        if all((s, self.HALT) not in ret for s in self.states):
            raise DescriptionParseError('HALT transition missing')
        return ret

    # инициализатор объекта
    # filename -- имя файла с описанием автомата (xml)
    # actions -- диспетчер действий
    def __init__(self, filename: str, actions: AutomatonActionDispatcher=NilFunction()):
        tree = xml.parse(filename)
        root = tree.getroot()

        self.actions: AutomatonActionDispatcher = actions
        self.states: Set[str] = self.__parse_states(root.find('states'))
        self.start_state = root.attrib['start_state']
        if self.start_state not in self.states:
            raise DescriptionParseError('State not in state set: '
                                        f'{self.start_state}')

        self.token_map: Dict[str, str] = self.__parse_tokens(root.find('tokens'))
        self.transitions: Automaton.TransitionTable = self.__parse_transitions(root.find('transitions'))

    # разобрать поток лексем/символов с помощью автомата
    # token_stream -- поток лексем/символов
    def parse(self, token_stream: Iterable[str]) -> bool:
        # текущее состояние автомата
        s = self.start_state
        # сбросить состояние диспетчера
        self.actions.reset()
        # обернуть поток в HaltIterable
        TS = Automaton.HaltIterable(token_stream)
        for token in TS:
            # встречена лексема не из алфавита            
            if token not in self.token_map:
                return False
            tg = self.token_map[token]
            # нет перехода
            if (s, tg) not in self.transitions:
                return False
            new_s, A = self.transitions[s, tg]
            # действие существует и его результат - false
            if A and not self.actions(s, token, A):
                return False
            # перейти к новому состоянию
            s = new_s
        return True
