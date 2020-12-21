from ll import GrammarParser


class Printer:
    def __init__(self):
        pass

    def __call__(self, A, t):
        print(t)
        return True

    def get_parse_results(self):
        return dict()


G = GrammarParser('test-gram.txt')
S = '       namespace    kek       {         namespace lol{     char foo   (int _a[20][30],    char b[72],  int c)    ;   int bar(char c)   {    }}}'
if G.parse(S):
    print('All ok')
