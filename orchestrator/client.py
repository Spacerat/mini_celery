from .broker import RedisBroker

from .task import Task
import functools


class Client():
    def __init__(self):
        self.broker = RedisBroker()
        # self.register = TaskRegister()
        self.functions = {}

    def task(self, f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return Task(f.__name__, args, kwargs, app=self)
        wrapper.func = f
        self.functions[f.__name__] = f
        return wrapper

    def run_task(self, task):
        return self.functions[task.funcname](*task.args, **task.kwargs)

    def add(self, task):
        self.broker.add_to_scheduler(task)

    def flush(self):
        self.broker.flush()

    def run(self):
        for task in self.broker.get_tasks():
            # print("Running task {}".format(task))
            result = self.run_task(task)
            self.broker.report_result(task, result)
