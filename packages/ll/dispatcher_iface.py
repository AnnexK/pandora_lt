from abc import ABCMeta, abstractmethod


# интерфейс диспетчера действий для LL(1)-анализатора
class LLActionDispatcher(metaclass=ABCMeta):
    # сбросить состояние диспетчера
    # выполняется до начала разбора анализатором
    @abstractmethod
    def reset(self):
        pass

    # выполнить действие с именем A
    # в качестве аргумента - текущая лексема из анализируемого потока
    # (если действие при терминале)
    # либо следующая лексема
    @abstractmethod
    def __call__(self, A: str, t: str) -> bool:
        pass