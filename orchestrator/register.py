from .task import Task
import functools

class TaskRegister():
    def __init__(self):
        self.functions = {}

    def task(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return Task(f.__name__, args, kwargs)
        wrapper.func = f
        self.functions[f.__name__] = f
        return wrapper

    def run(self, task):
        return self.functions[task.funcname](*task.args, **task.kwargs)