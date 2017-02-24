import uuid
class Task():
    def __init__(self, funcname, args=None, kwargs=None, tid=None, app=None):
        self.funcname = funcname
        self.args = args if args else ()
        self.kwargs = kwargs if kwargs else {}
        self.tid = str(uuid.uuid4()) if tid is None else tid
        self.app = app

    @staticmethod
    def task_key(tid, *args):
        return "task_{}_{}".format("_".join(str(x) for x in args), tid)

    def key(self, *args):
        return Task.task_key(self.tid, *args)

    def __repr__(self):
        args = [str(x) for x in self.args] + ["{} = {}".format(str(k), str(v)) for k, v in self.kwargs.items()]
        return "Task<{}: {}({})>".format(self.tid, self.funcname, ",".join(args))

    def wait(self, time):
        self.app.broker.add_to_scheduler(self)
        self.app.broker.schedule_after_seconds(self, time)
        return self

    def depends_on(self, other):
        self.app.broker.add_to_scheduler(self)
        self.app.broker.set_dependency(self, other)