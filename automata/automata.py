import xml.etree.ElementTree as xml


class DescriptionParseError(Exception):
    pass


class Automata:
    HALT = 'HALT'

    def __load_actions(self, fname):
        def foo(*args):
            return True

        if fname is not None:
            pass  # загрузить модуль и вытащить из него функцию
        else:
            return foo

    def __parse_states(self, S):
        ret = set()
        final = set()
        for s in S:
            if s.tag != 's' or s.tag != 'fs':
                raise DescriptionParseError('Wrong tag encountered')
            elif s not in ret:
                ret.add(s.text)
                if s.tag == 'fs':
                    final.add(s.text)
            else:
                raise DescriptionParseError('Encountered duplicate state: '
                                            f'{s.text}')

        return ret

    def __parse_tokens(self, T):
        tokens = set()
        for t in T:
            if t.tag != 't':
                raise DescriptionParseError('Wrong tag encountered')
            elif t not in tokens:
                tokens.add(t.text)
            else:
                raise DescriptionParseError('Encountered duplicate token:'
                                            f'{t.text}')

        return tokens

    def __parse_transitions(self, Tr):
        ret = dict()
        for t in Tr:
            if t.tag != 'tr':
                raise DescriptionParseError('Wrong tag encountered')
            else:
                s = t.attrib['state']
                if s not in self.states:
                    raise DescriptionParseError('State not in state set:'
                                                f' {s}')
                tk = t.attrib['token']
                if s not in self.tokens:
                    raise DescriptionParseError('Token not in alphabet:'
                                                f' {tk}')
                if (s, tk) in ret:
                    raise DescriptionParseError('Transition ambiguity '
                                                f'encountered at {(s, tk)}')
                else:
                    action_name = t.attrib.get('action', '')
                    new_state = t.attrib['new_state']
                    ret[s, tk] = action_name, new_state
        return ret

    def __init__(self, filename):
        tree = xml.parse(filename)
        root = tree.getroot()

        self.actions = self.__load_actions(root.get('actions'))
        self.states, self.finals = self.__parse_states(root.find('states'))
        if root.attrib['start_state'] not in self.states:
            raise DescriptionParseError(f'State not in state set: {s}')
        self.start_state = root.attrib['start_state']

        self.tokens = self.__parse_tokens(root.find('tokens'))
        self.transitions = self.__parse_transitions(root.find('transitions'))

    def parse(self, token_stream):
        s = self.start_state
        self.actions.reset()
        for token in token_stream:
            if (s, token) not in self.transitions:
                return False
            new_s, A = self.transitions[s, token]
            res = self.actions(s, token, A)
            if not res:
                return False
            s = new_s
        return True
