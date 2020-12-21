import xml.etree.ElementTree as xml
import importlib.util as implib
import pathlib


class DescriptionParseError(Exception):
    pass


class Automaton:
    HALT = ''

    class HaltIterable:
        def __init__(self, iterable):
            self.iterable = iterable

        def __iter__(self):
            for x in self.iterable:
                yield x
            yield Automaton.HALT

    class NilFunction:
        def __init__(self):
            pass

        def __call__(self, state, tg, action):
            return True

        def reset(self):
            pass

        def get_parse_results(self):
            return dict()

    def __load_actions(self, descfname, actfname):
        def load_from_module(path):
            spec = implib.spec_from_file_location('mod', path)
            mod = implib.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod

        if actfname is not None:
            actp = pathlib.Path(actfname)
            if actp.is_absolute():
                mod = load_from_module(actfname)
            else:
                descp = pathlib.Path(descfname).absolute().parent
                mod = load_from_module(descp / actp)
            return mod.load_actions()
        else:
            return Automaton.NilFunction()

    def __parse_states(self, S):
        ret = set()
        for s in S:
            if s.tag != 's':
                raise DescriptionParseError('Wrong tag encountered')
            elif s not in ret:
                ret.add(s.text)
            else:
                raise DescriptionParseError('Encountered duplicate state: '
                                            f'{s.text}')

        return ret

    def __parse_tokens(self, T):
        token_groups = set()
        token_groups.add(Automaton.HALT)
        token_map = dict()
        token_map[Automaton.HALT] = Automaton.HALT
        for group in T:
            if group.tag != 'tg':
                raise DescriptionParseError('Wrong tag encountered, '
                                            'expected tg')
            groupname = group.attrib['name']
            token_groups.add(groupname)
            for t in group:
                if t.tag != 't':
                    raise DescriptionParseError('Wrong tag encountered, '
                                                'expected t')
                if t.text not in token_map:
                    token_map[t.text] = groupname
                else:
                    raise DescriptionParseError('Token duplicate encountered: '
                                                f'{t.text}')
            if not group:
                if groupname not in token_map:
                    token_map[groupname] = groupname
                else:
                    raise DescriptionParseError(f'Group {groupname} cannot '
                                                'be empty: '
                                                f'token {groupname} exists')
        return token_groups, token_map

    def __parse_transitions(self, Tr):
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
                if tg not in self.token_groups:
                    raise DescriptionParseError('Token group not in token map:'
                                                f' {tg}'
                                                f'Token map: {self.token_groups}')
                if (s, tg) in ret:
                    raise DescriptionParseError('Transition ambiguity '
                                                f'encountered at {(s, tg)}')
                else:
                    action_name = t.attrib.get('action', '')
                    end = t.attrib['end']
                    if end not in self.states and tg != self.HALT and end != self.HALT:
                        raise DescriptionParseError('State not in state set: '
                                                    f'{s} (and is not HALT)')
                    ret[s, tg] = end, action_name

        if all((s, self.HALT) not in ret for s in self.states):
            raise DescriptionParseError('HALT transition missing')
        return ret

    def __init__(self, filename):
        tree = xml.parse(filename)
        root = tree.getroot()

        self.actions = self.__load_actions(filename, root.get('actions'))
        self.states = self.__parse_states(root.find('states'))
        self.start_state = root.attrib['start_state']
        if self.start_state not in self.states:
            raise DescriptionParseError('State not in state set: '
                                        f'{self.start_state}')

        self.token_groups, self.token_map = self.__parse_tokens(root.find('tokens'))
        self.transitions = self.__parse_transitions(root.find('transitions'))

    def parse(self, token_stream):
        s = self.start_state
        print(s)
        self.actions.reset()
        TS = Automaton.HaltIterable(token_stream)
        for token in TS:
            if token not in self.token_map:
                return False
            tg = self.token_map[token]
            if (s, tg) not in self.transitions:
                return False
            new_s, A = self.transitions[s, tg]
            if A:
                if not self.actions(s, token, A):
                    return False
            s = new_s
            print(f"{token.encode()}, {s}")
        return True

    def get_parse_results(self):
        return self.actions.get_parse_results()
