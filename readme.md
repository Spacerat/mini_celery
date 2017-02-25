# Mini Celery!

Like Python's Celery, but way less functional, reliable, etc.

## Installation

Do this inside  virtualenv if you feel like it, or not, it's up to you

	$ pip install -r requirements.txt

You also need a Redis server running on localhost

## Execution

To run the test scripts, first run one or more instances of `client.py`. Then run `task_test.py`, and look at the output. 

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

That's basically everything!


## Omissions

The redis broker never deletes any finished tasks (or any data at all!). Maybe I'll add that some time.
