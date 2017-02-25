import redis
import time
from .task import Task

class RedisBroker():
    """ The broker manages most of the task management logic. """

    TIMESTAMP_PATTERN = 'task_timestamp_*'
    DONE_PATTERN = 'task_done_*'
    def __init__(self, transport, host='localhost', port=6379):
        self.redis = redis.StrictRedis(host=host, port=port, db=0, decode_responses=True)
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        self.pubsub.psubscribe([self.TIMESTAMP_PATTERN, self.DONE_PATTERN])
        self.transport = transport
        self.waiter = None

    def flush(self):
        """ Flush the redis store """
        self.redis.flushall()

    def add_to_scheduler(self, task):
        """ Register a task with the scheduler """
        with self.redis.pipeline() as pipe:
            pipe.set(task.key('name'), task.funcname)
            pipe.set(task.key('args'), self.transport.encode(task.args))
            pipe.set(task.key('kwargs'), self.transport.encode(task.kwargs))
            pipe.set(task.key('consumed'), False)
            pipe.execute()

    def schedule_at_time(self, task, time):
        """ Schedule a task at a time """
        task_time = time.timestamp()
        self.redis.set(task.key('timestamp'), task_time)
        self.redis.publish(task.key('timestamp'), task_time)        

    def schedule_after_seconds(self, task, seconds=0):
        """ Schedule a task to run after a certain number of seconds """
        task_time = time.time() + seconds
        self.redis.set(task.key('timestamp'), task_time)
        self.redis.publish(task.key('timestamp'), task_time)

    def set_dependency(self, task, depends_on):
        """ Schedule a task to run after another task which it depends_on """
        dep_key = task.key('dependencies')
        def do_schedule(pipe):
            num_deps = pipe.incr(dep_key)
            pipe.incr(task.key('dependencies_remaining'))
            pipe.set(depends_on.key('required_for', task.tid, 'task'), task.tid)
            pipe.set(depends_on.key('required_for', task.tid, 'fulfilled'), "False")
            pipe.set(task.key('depends_on', num_deps), depends_on.tid)

        self.redis.transaction(do_schedule, dep_key)

    def get_next_task(self):
        """ Get the ID and time of the next task """
        min_time = None
        next_task = None
        for key in self.redis.scan_iter('task_consumed_*'):
            is_consumed = self.redis.get(key)
            if is_consumed == "False":
                task_id = key.split('_')[-1]
                timestamp_key = Task.task_key(task_id, 'timestamp')
                task_time = self.redis.get(timestamp_key)
                if task_time is not None:
                    task_time = float(task_time)
                    if not min_time or task_time < min_time:
                        min_time = task_time
                        next_task = task_id

        return next_task, min_time

    def try_consume_task(self, task_id):
        """ Try to consume a task. Return True if we managed to secure the task """
        # Uses atomic getset to make sure that only one client can consume the task
        was_consumed = self.redis.getset(Task.task_key(task_id, 'consumed'), "True")
        return was_consumed == "False"

    def get_from_scheduler(self, task_id):
        """ Get all the details for a task, and return them as a Task object """
        funcname = self.redis.get(Task.task_key(task_id, 'name'))
        args = self.transport.decode(self.redis.get(Task.task_key(task_id, 'args')))
        kwargs = self.transport.decode(self.redis.get(Task.task_key(task_id, 'kwargs')))
        return Task(funcname, args, kwargs, task_id)

    def report_result(self, task, result):
        """ Set/report the return value of a task """
        self.redis.set(task.key('result'), self.transport.encode(result))
        self.redis.publish(task.key('done'), 'True')

    def fulfill_dependency(self, key):
        """ Given a 'required_for' key which represents a dependency relation, 
        this should be called when the parent task is complete. The child task's "dependencies_remaining"
        counter will be decremented. If that counter hits 0, this client should consume the child task and
        return it.
        s"""
        split = key.split('_')
        split[-2] = 'fulfilled'
        was_fulfilled = self.redis.getset('_'.join(split), "True")
        if was_fulfilled == "False":
            client_id = self.redis.get(key)
            remaining = self.redis.decr(Task.task_key(client_id, 'dependencies_remaining'))
            if remaining == 0:
                if self.try_consume_task(client_id):
                    return self.get_from_scheduler(client_id)


    def get_tasks(self):
        """ A generator which yields any tasks which this client manages to consume """
        next_task, next_time = self.get_next_task()
        while True:
            if not next_time:
                timeout = 1800
            else:
                timeout = max(next_time - time.time(), 0.01)
            # This is the key bit of logic. We know how long it will be until the next task is due,
            # but there is the possibility that another task will be scheduled before then, or that
            # we will need to consume a child task. Here, we wait until we expect the next task to
            # become available, but using the pubsub we can be interrupted by "task_timestamp" or "task_done"
            # messages which tell us that we might need to act earlier than expected.
            message = self.pubsub.get_message(timeout=timeout, ignore_subscribe_messages=True)

            if message:
                task_id = message['channel'].split('_')[-1]
                if message['pattern'] == self.TIMESTAMP_PATTERN:
                    # A new timed task was registered. If it's sooner than our current next-task, update 
                    # our next-task info.
                    task_time = float(message['data'])
                    if not next_time or task_time < next_time:
                        next_time = task_time
                        next_task = task_id
                elif message['pattern'] == self.DONE_PATTERN:
                    # A task finished running, so we need to check if it had any children which may need
                    # to be run now.
                    for key in self.redis.scan_iter(Task.task_key(task_id, 'required_for', '*', 'task')):
                        child = self.fulfill_dependency(key)
                        if child:
                            child_id = child.tid                        
                            results = []
                            for result_key in self.redis.scan_iter(Task.task_key(child_id, 'depends_on', '*')):
                                result_id = self.redis.get(result_key)
                                pos = int(result_key.split('_')[-2])
                                result = self.transport.decode(self.redis.get(Task.task_key(result_id, 'result')))
                                results.append((pos, result))
                            args = [x[1] for x in sorted(results, key=lambda x: x[0])]
                            child.args = list(child.args)+args
                            yield child

            # If the current task is ready now, try to consume it
            if next_task and next_time - time.time() < 1:
                if self.try_consume_task(next_task):
                    yield self.get_from_scheduler(next_task)
                next_task, next_time = self.get_next_task()