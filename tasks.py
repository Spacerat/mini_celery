from app import app
import time

@app.task
def raise_an_exception():
    raise Exception("Error: hello world!")

@app.task
def check_for_exception(thing):
    if isinstance(thing, Exception):
        print("Oh no! The previous task failed with message: '{}'".format(str(thing)))

@app.task
def multiply_three_things(a, b, c):
    """ Just multiply three things together """
    print("{} * {} * {} = {}".format(a, b, c, a*b*c))

@app.task
def square_something(x):
    """ Square a number
    Sadly this is an expensive function. 
    It blocks the process and runs in O(x) time!
    """
    time.sleep(x)
    print("{} ^ 2 = {}".format(x, x**2))
    return x**2


@app.task
def main_task(period=1):
    """ This is a periodic task, with a period growing over time.
    We wan to find (period * (period+1)**2 * (period+2)**2)
    Unfortunately, squaring numbers takes a while!
    """

    # Compose the tasks
    b = square_something(period+1)
    c = square_something(period+2)
    d = multiply_three_things(period, b, c)

    # Trigger the root tasks
    b.wait(0)
    c.wait(0)

    exc_task = raise_an_exception()
    check_task = check_for_exception(exc_task)
    exc_task.wait(2)

    # Run everything again in period+1 seconds
    print("Running again in {} seconds!".format(period))
    main_task(period=period+1).wait(period)
