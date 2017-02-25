# Mini Celery!

Like Python's Celery, but way less functional, reliable, etc.

## Installation

Do this inside  virtualenv if you feel like it, or not, it's up to you

	$ pip install -r requirements.txt

You also need a Redis server running on localhost

## Execution

To run the test scripts, first run one or more instances of `client.py`. Then run `task_test.py`, and look at the output. Alternatively, run `task_test.py` before the clients. Or even run both of them multiple times in whichever order you like! Clients will pick up any tasks sitting in Redis when they start.

You should expect to see some calculations (things being squared, multipleid...) as well as an exception being printed every so often.
The more clients you run, the smoother this will be

## How to write tasks

Here some tasks:

	@app.task
	def hello(thing):
		print("Hello {}!".format(thing))
	
	@app.task
	def world():
		return "World!"

To schedule a task at a time

	hello("World!").start_at(datetime.datetime(2017, 1, 27, 13))

Set up dependencies simply by composing your task functions. Make sure you run the _parent_ task to start the chain

	hello(world().wait(5))

If a task throws an exception, any child tasks will simply get that exception as an argument.

In these examples, `app` is simply an instance of the `Client` class, which is instantiated with instances of broker and a transport.

	from orchestrator import Client, JSONTransport, RedisBroker
	transport = JSONTransport()
	broker = RedisBroker(transport)
	app = Client(broker)

The same `app` which is used to register tasks is also used to start a client to listen for and execute them: simply call `app.start()`.

That's basically everything!


## Relatively Detailed Descripton

- The first thing a MiniCelery application does is register tasks, storing them in a lookup by function name.
- When a task is scheduled, its details (time, function name, arguments) are added to the broker (the only one available being RedisBroker).
- Clients then subscribe to the broker to get new tasks to run. They simply run the named function with the given arguments and turn the return values over to the broker.
- The broker also manages task dependencies - if all of a task's parent tasks are completed, one of the clients will run the child task and receieve all the results from its parents.

### How RedisBroker works

When a task is scheduled, RedisBroker gives it a UUID and dumps it into redis with keys like `task_funcname_<uuid>` and `task_args_<uuid>` and `task_timestamp_<uuid>`. If the task was scheduled at a time, it also publishes a `timestamp` message, and when a task is completed, the client publishes a `done` message.

When a RedisBroker object starts listening for tasks, it first scans redis for the earliest task. Then it subscribes to `timestamp` and `done` messages and performs a **blocking** read waiting on them, with a timeout of `time until the next task is ready`. Thus, the client wakes up in three possible situations

1. The timeout ran out: the client should run the next task, if no other clients already claimed it, and then look for the next task.
2. A new task was scheduled: if that new task is closer than the current 'next task', set that task as the next task and go back to listening (for a shorter amount of time)
3. A task completed. If it was the parent of another task and it was that tasks's last parent, execute the child task.

This system of interruptible timeouts allows the clients to be completely single threaded. A client can't listen for tasks while it's running one, but that's OK - when it goes back to listening, it can just pick up from where it left off. Parallelism is achieved simply by running multiple clients. Yay!

## Things I would fix with a bit more time

- The redis broker never deletes any finished tasks (or any data at all!).
- The redis broker's logic for dependencies is somewhat a somewhat overly complicated, forcing all clients to wake up when any task is done when really they should only wake up when a task's final dependency is fulfilled.
- Scanning redis to find the soonest task is not terribly efficient. Redis itself could be used to keep track of the time of the next task, so that clients are _only_ woken up if an earlier task is scheduled.
