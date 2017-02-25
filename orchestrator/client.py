import functools
import logging
from traceback import print_exc

from .broker import RedisBroker
from .task import Task



class Client():
    """ Client is the main 'user' interface to the orchestrator, allowing users to register
    tasks and connect to a broker to manage them """
    def __init__(self, broker):
        self.broker = broker
        self.functions = {}

    def task(self, f):
        """ This decorator turns a function into a task. When the function is called, instead
        of being run, a Task object representing that function is returned """
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            return Task(f.__name__, args, kwargs, app=self)
        wrapper.func = f
        self.functions[f.__name__] = f
        return wrapper

    def run_task(self, task):
        try:
            return self.functions[task.funcname](*task.args, **task.kwargs)
        except Exception as e:
            logging.exception("Error in task {}".format(task))
            # print_exc()
            return e

    def add(self, task):
        self.broker.add_to_scheduler(task)

    def flush(self):
        self.broker.flush()

    def run(self):
        for task in self.broker.get_tasks():
            # print("Running task {}".format(task))
            result = self.run_task(task)
            self.broker.report_result(task, result)
