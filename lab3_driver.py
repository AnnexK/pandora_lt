from packages.ll import GrammarParser
from packages.lab3 import RPNDispatcher
from pathlib import Path


class Printer:
    def __init__(self):
        pass

    def __call__(self, A, t):
        print(t)
        return True

    def reset(self):
        pass


# p = Path('lab3/test-gram.txt').absolute()
D = RPNDispatcher()
S = '255+70*2'
G = GrammarParser('rpn.txt', D)
if (G.parse(S)):
    print(D.rpn)
