from packages.lr import GrammarParser, GrammarParserException
from packages.lab4 import LexDispatcher, SynDispatcher
from pathlib import Path


def print_tree(t):
    _print_tree(t, 0)

def _print_tree(t, lv):
    print(f'{"".join("- " for i in range(lv))}{t}')
    for c in t.children:
        _print_tree(c, lv+1)

with open('input.txt') as fp:
    s = fp.read()

with open('output.txt', 'w') as fp:
    L = LexDispatcher()
    try:
        A = GrammarParser('packages/lab4/lexg.txt', L)
        if A.parse(s):
            stream = L.stream
            streampos = L.token_pos
            streampos.append(L.last_char_pos)
            S = SynDispatcher()
            B = GrammarParser('lr_grammar.txt', S)
            if B.parse(stream):
                fp.write('CORRECT\n')
            else:
                err_tok = S.err_tok
                print(err_tok)
                err_pos = streampos[err_tok]
                print(S.buffer)                
                print_tree(S.ns_stack[0])
                if not S.duplicate:
                    fp.write(f'INCORRECT {err_pos[0]}:{err_pos[1]}\n')
                else:
                    fp.write(f'DUPLICATE {S.duplicate} {err_pos[0]}:{err_pos[1]}')
        else:
            err_pos = L.last_char_pos
            fp.write(f'INCORRECT {err_pos[0]}:{err_pos[1]}')
    except GrammarParserException as e:
        fp.write('NOT GRAMMAR\n')

