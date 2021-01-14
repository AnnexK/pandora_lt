from ..ll import LLActionDispatcher


class Dispatcher(LLActionDispatcher):
    def reset(self):
        self.res = []
        self.ops = []

    def __init__(self):
        self.reset()

    def a1(self, t: str) -> bool:
        self.res.append(t)
        return True

    def prio(self, x: str):
        return 1 if x == '+' else 2

    def a2(self, t: str) -> bool:
        print('called a2')
        while self.ops and self.prio(self.ops[-1]) >= self.prio(t):
            self.res.append(self.ops.pop())
            self.res.append(' ')
        self.ops.append(t)
        return True

    def a3(self, t: str) -> bool:
        print('called a3')
        while self.ops:
            self.res.append(self.ops.pop())
            self.res.append(' ')
        return True
    
    def __call__(self, A: str, t: str) -> bool:
        actions_map = {'A1': self.a1,
                       'A2': self.a2,
                       'A3': self.a3}
        return actions_map[A](t)

    @property
    def rpn(self) -> str:
        return ''.join(self.res if self.res[-1] != ' ' else self.res[:-1])
    