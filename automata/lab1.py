#!/usr/bin/env python

import automata

with open('lab1/input.txt', 'r') as fp:
    s = fp.read()

A = automata.Automaton('lab1/string_to_tokens.xml')

print(A.parse(s))
token_stream = A.get_parse_results()['token_stream']
token_pos = A.get_parse_results()['token_pos']
print(token_stream)
print(token_pos)
B = automata.Automaton('lab1/tokens_to_result.xml')
res = B.parse(token_stream)
if res:
    print('No errors')
else:
    err_num = B.get_parse_results()['tokens']
    err_token = token_stream[err_num]
    err_token_pos = token_pos[err_num]
    print(f'Error @ {err_token_pos}')
