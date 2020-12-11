#!/usr/bin/env python

import automata

with open('lab1/input.txt', 'r') as fp:
    s = fp.read()

with open('lab1/output.txt', 'w') as fp:
    A = automata.Automaton('lab1/c_stt.xml')

    if A.parse(s):
        token_stream = A.get_parse_results()['token_stream']
        token_pos = A.get_parse_results()['token_pos']
        token_pos.append(A.get_parse_results()['file_pos'])
        B = automata.Automaton('lab1/c_ttr.xml')
        if B.parse(token_stream):
            fp.write('CORRECT\n')
        else:
            res = B.get_parse_results()
            err_tok = res['tok_counter']
            err_pos = token_pos[err_tok]
            if not res['duplicate']:
                fp.write(f'INCORRECT {err_pos[0]}:{err_pos[1]}\n')
            else:
                fp.write('DUPLICATE '
                         f'{res["duplicate"]} '
                         f'{err_pos[0]}:{err_pos[1]}\n')
    else:
        err_pos = A.get_parse_results()['file_pos']
        fp.write(f'INCORRECT {err_pos[0]}:{err_pos[1]}\n')
