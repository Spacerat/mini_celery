import uuid
import time

class Task():
    """ Tasks represent functions which can be scheduled to run at certain times or after other functions """
    def __init__(self, funcname, args=None, kwargs=None, tid=None, app=None):
        self.funcname = funcname
        args = args if args else []
        self.args = []
        self.kwargs = kwargs if kwargs else {}
        self.tid = str(uuid.uuid4()) if tid is None else tid
        self.app = app
        includes_deps = False
        for arg in args:
            if isinstance(arg, Task):
                includes_deps = True
                self.depends_on(arg)
            elif includes_deps:
                raise Exception("Arguments from parent tasks must come after fixed arguments.")
            else:
                self.args.append(arg)

    @staticmethod
    def task_key(tid, *args):
        """ Convenience function for creating a redis key for a task """
        return "task_{}_{}".format("_".join(str(x) for x in args), tid)
    def key(self, *args):
        """ Convenience function for creating a redis key for this task """
        return Task.task_key(self.tid, *args)

    def __repr__(self):
        args = [str(x) for x in self.args] + ["{} = {}".format(str(k), str(v)) for k, v in self.kwargs.items()]
        return "Task<{}: {}({})>".format(self.tid, self.funcname, ",".join(args))

    def start_at(self, datetime):
        """ Run this task at a time """
        self.app.broker.add_to_scheduler(self)
        self.app.broker.schedule_at_time(self, datetime)

    def wait(self, time):
        """ Run this task after a number of seconds """
        self.app.broker.add_to_scheduler(self)
        self.app.broker.schedule_after_seconds(self, time)
        return self

    def depends_on(self, other):
        """ Run this task after another one"""
        self.app.broker.add_to_scheduler(self)
        self.app.broker.set_dependency(self, other)
