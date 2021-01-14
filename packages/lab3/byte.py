from ..ll import LLActionDispatcher

class Dispatcher(LLActionDispatcher):
    def reset(self):
        self.number = 0

    def __init__(self):
        self.reset()

    def __call__(self, A: str, t: str) -> bool:
        if A == 'A1':
            self.number = self.number * 10 + int(t)
            return self.number < 256

        return False