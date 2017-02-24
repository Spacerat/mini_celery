import redis
import json
import time
from .task import Task

class JSONTransport():
    def encode(self, value):
        return json.dumps(value)
    def decode(self, encoded):
        return json.loads(encoded)

class RedisBroker():
    TIMESTAMP_PATTERN = 'task_timestamp_*'
    DONE_PATTERN = 'task_done_*'
    def __init__(self):
        self.transport = JSONTransport()
        self.redis = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
        # self.redis.flushall()
        self.pubsub = self.redis.pubsub(ignore_subscribe_messages=True)
        self.pubsub.psubscribe([self.TIMESTAMP_PATTERN, self.DONE_PATTERN])
        # self.pubsub.psubscribe('task_timestamp_*')
        
        self.waiter = None

    def add_to_scheduler(self, task):
        with self.redis.pipeline() as pipe:
            pipe.set(task.key('name'), task.funcname)
            pipe.set(task.key('args'), self.transport.encode(task.args))
            pipe.set(task.key('kwargs'), self.transport.encode(task.kwargs))
            pipe.set(task.key('consumed'), False)
            pipe.execute()

    def schedule_after_seconds(self, task, seconds=0):
        task_time = time.time() + seconds
        self.redis.set(task.key('timestamp'), task_time)
        self.redis.publish(task.key('timestamp'), task_time)

    def schedule_after_task(self, before, after):
        b_key = before.key('dependencies')
        def do_schedule(pipe):
            num_deps = pipe.incr(b_key)
            pipe.set(before.key('dependency', num_deps), after.tid)

        self.redis.transaction(do_schedule, b_key)

    def get_next_task(self):
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
        was_consumed = self.redis.getset(Task.task_key(task_id, 'consumed'), "True")
        return was_consumed == "False"

    def get_from_scheduler(self, task_id):
        funcname = self.redis.get(Task.task_key(task_id, 'name'))
        args = self.transport.decode(self.redis.get(Task.task_key(task_id, 'args')))
        kwargs = self.transport.decode(self.redis.get(Task.task_key(task_id, 'kwargs')))
        return Task(funcname, args, kwargs, task_id)

    def report_result(self, task, result):
        self.redis.set(task.key('result'), self.transport.encode(result))
        self.redis.publish(task.key('done'), 'True')

    def get_tasks(self):
        next_task, next_time = self.get_next_task()
        while True:
            if not next_time:
                timeout = 1800
            else:
                timeout = next_time - time.time()
            message = self.pubsub.get_message(timeout=timeout, ignore_subscribe_messages=True)
            if message:
                print(message)
                task_id = message['channel'].split('_')[-1]
                if message['pattern'] == self.TIMESTAMP_PATTERN:
                    task_time = float(message['data'])
                    if not next_time or task_time < next_time:
                        next_time = task_time
                        next_task = task_id
                elif message['pattern'] == self.DONE_PATTERN:
                    
                    num_deps = self.redis.get(Task.task_key(task_id, 'dependencies'))
                    if num_deps:
                        fetched_result = False
                        result = None
                        for n in range(1, int(num_deps)+1):
                            dep_id = self.redis.get(Task.task_key(task_id, 'dependency', n))
                            if self.try_consume_task(dep_id):
                                print("DEP %s" % dep_id)
                                if not fetched_result:
                                    result = self.transport.decode(self.redis.get(Task.task_key(task_id, 'result')))
                                    fetched_result = True
                                task = self.get_from_scheduler(dep_id)
                                task.args = task.args + (result,)

                                yield task


            if next_task and next_time - time.time() < 1:
                if self.try_consume_task(next_task):
                    yield self.get_from_scheduler(next_task)
                next_task, next_time = self.get_next_task()