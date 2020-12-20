from ll import GrammarParser

G = GrammarParser('test-gram.txt')
if G.parse('a+a'):
    print('All ok')
