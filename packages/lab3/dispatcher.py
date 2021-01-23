from __future__ import annotations
from ..ll import LLActionDispatcher
from typing import Dict, Tuple, List, Set


class NSTreeElement:
    def __init__(self, T: str, name: str):
        self.type: str = T
        self.name: str = name
        # self.children: Dict[Tuple[str,str], NSTreeElement] = dict()
        self.children: List[NSTreeElement] = []

    def append(self, E):
        # self.children[E.name, E.type] = E
        self.children.append(E)

    def __str__(self):
        n = self.name if self.name else '~'
        return f'<{n} {self.type}>'

    def __repr__(self):
        return str(self)


class Dispatcher(LLActionDispatcher):
    def __init__(self):
        self.reset()

    def reset(self):
        # буфер символов
        self.buffer: List[str] = []
        # счётчик лексем
        self.token_counter: int = 0
        # позиция первого символа неключевого слова
        self.nkw_pos: int = -1
        # стек элементов описания
        # изначально содержит объект "глобальное пространство имён"
        self.ns_stack: List[NSTreeElement] = [NSTreeElement('ns', '')]
        # зарегистрированный модификатор знака
        self.sign: str = ''
        # зарегистрированный модификатор знака
        self.prim: str = ''
        # зарегистрированный модификатор знака
        self.size: str = ''
        # зарегистрированный тип данных
        self.elem_type: str = ''
        # положение лексемы "идентификатор разбираемой функции"
        self.foo_tok = -1
        # количество аргументов у разбираемой функции
        # включает также возвращаемое значение под номером 0
        self.foo_arg_number: int = 0
        # множество имён параметров разбираемой функции
        self.foo_param_names: Set[str] = set()
        # лексема-дубликат
        self.duplicate = ''
        # список размерностей массива
        self.array_dims = []

    # увеличить счетчик лексем на 1
    def count(self, t: str) -> bool:
        self.token_counter += 1
        return True
    
    # добавить символ в буфер
    def add_char(self, t: str) -> bool:
        self.buffer.append(t)
        return self.count(t)
    
    def set_nkw(self, t: str) -> bool:
        self.nkw_pos = self.token_counter
        return self.count(t)
    
    # создать новый НС если такого нет
    # перейти к НС
    def set_current_ns(self, t: str) -> bool:
        ns_name = ''.join(self.buffer)
        ns = self.ns_stack[-1]
        new_ns = None
        # если что-то с этим именем есть в текущем НС
        for n in ns.children:
            if n.name == ns_name:
                # если под именем в текущем НС находится не НС, выдать ошибку
                if n.type != 'ns':
                    self.duplicate = ns_name
                    self.token_counter = self.nkw
                    return False
                else:
                    new_ns = n
                    break
            # иначе перейти к НС под этим именем
        if not new_ns:
            new_ns = NSTreeElement('ns', ns_name)
            self.ns_stack[-1].append(new_ns)
        self.ns_stack.append(new_ns)
        self.nkw_pos = -1
        self.buffer.clear()
        return True

    # перейти на один уровень ниже
    def goto_parent(self, t: str) -> bool:
        self.ns_stack.pop()
        # посчитать лексему, если лексема - закрывающая скобка
        if t == '}':
            self.count(t)
        return True

    def register_prim(self, t: str) -> bool:
        self.prim = t
        return self.count(t)

    def register_size(self, t: str) -> bool:
        self.size = t
        return self.count(t)

    def register_sign(self, t: str) -> bool:
        self.sign = t
        return self.count(t)
    
    # составить тип из частей и зарегистрировать его
    def register_type(self, t: str) -> bool:
        if not self.prim:
            self.prim = 'int'
        if self.prim == 'int' and not self.sign:
            self.sign = 'signed'
        self.elem_type = f'{self.prim} {self.size} {self.sign}'
        self.prim = self.sign = self.size = ''
        return True

    def create_foo(self, t: str) -> bool:
        s = ''.join(self.buffer)
        F = NSTreeElement('foo', s)
        self.foo_tok = self.nkw_pos
        ret = NSTreeElement(self.elem_type, '0')
        self.foo_arg_number = 1
        F.append(ret)
        self.ns_stack.append(F)
        self.elem_type = ''
        self.buffer.clear()
        self.nkw = -1
        return True

    def _check_sigs(self, f: NSTreeElement, el: NSTreeElement):
        if len(f.children) != len(el.children):
            return False
        Z = zip(f.children, el.children)
        return all(x.name == y.name and (x.type == y.type or x.name == '0') for x, y in Z)

    def make_impl(self, t: str) -> bool:
        self.ns_stack[-1].type = 'impl'
        return self.count(t)

    def make_prot(self, t: str) -> bool:
        self.ns_stack[-1].type = 'prot'
        return self.count(t)

    def commit_foo(self, t: str) -> bool:
        f = self.ns_stack.pop()
        N = self.ns_stack[-1]
        # Просматриваем НС-родитель функции
        for x in N.children:
            if x.name == f.name:
                # в родителе есть одноименный НС - ошибка
                # в родителе есть одноименная реализация - проверить сигнатуры
                isns = x.type == 'ns'
                isimpl = f.type == 'impl' and x.type == 'impl'
                if isns or isimpl and self._check_sigs(f, x):
                    self.duplicate = f.name
                    self.token_counter = self.foo_tok
                    return False
        N.append(f)
        self.foo_arg_number = 0
        self.foo_tok = -1
        self.foo_param_names.clear()
        return True

    def create_param(self, t: str) -> bool:
        s = ''.join(self.buffer)
        # встречены параметры с одинаковыми именами - ошибка
        if s and s in self.foo_param_names:
            self.duplicate = s
            self.token_counter = self.nkw_pos
            return False
        self.foo_param_names.add(s)
        p = NSTreeElement(self.elem_type, str(self.foo_arg_number))
        self.foo_arg_number += 1
        self.elem_type = ''
        self.ns_stack[-1].append(p)
        self.ns_stack.append(p)
        self.buffer.clear()
        self.nkw_pos = -1
        return True

    def register_ellipsis(self, t: str) -> bool:
        ell = NSTreeElement('...', str(self.foo_arg_number))
        self.ns_stack[-1].append(ell)
        return self.count(t)

    def add_dim(self, t: str) -> bool:
        s = ''.join(self.buffer)
        # все размерности кроме первой должны быть определены
        if self.array_dims and not s:
            return False
        self.array_dims.append(s)
        self.buffer.clear()
        self.nkw_pos = -1
        return self.count(t)

    def append_arr_spec(self, t: str) -> bool:
        if self.array_dims:
            # заменяем первый элемент списка размерностей на указатель
            p = '*'+''.join(f'[{x}]' for x in self.array_dims[1:])
            self.ns_stack[-1].type += p
            self.array_dims.clear()
        return True

    def __call__(self, A: str, t: str) -> bool:
        action_map = {'count' : self.count,
                      'add_char': self.add_char,
                      'set_current_ns': self.set_current_ns,
                      'goto_parent': self.goto_parent,
                      'register_prim': self.register_prim,
                      'register_size': self.register_size,
                      'register_sign': self.register_sign,
                      'register_type': self.register_type,
                      'create_foo': self.create_foo,
                      'make_impl': self.make_impl,
                      'make_prot': self.make_prot,
                      'commit_foo': self.commit_foo,
                      'create_param': self.create_param,
                      'register_ellipsis': self.register_ellipsis,
                      'add_dim': self.add_dim,
                      'append_arr_spec': self.append_arr_spec,
                      'set_nkw': self.set_nkw}
        return action_map[A](t)
    
    @property
    def err_tok(self):
        return self.token_counter

    @property
    def tree(self):
        return self.ns_stack[0]
    