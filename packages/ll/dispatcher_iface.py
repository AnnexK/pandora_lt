from abc import ABCMeta, abstractmethod


class LLActionDispatcher(metaclass=ABCMeta):
    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def __call__(self, A: str, t: str) -> bool:
        pass