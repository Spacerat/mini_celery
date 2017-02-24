from app import app
import time

@app.task
def depends_on_both(a, b):
    print("{} * {} = {}".format(a, b, a*b))

@app.task
def the_task(x):
    time.sleep(x)
    print("{} ^ 2 = {}".format(x, x**2))
    return x**2


@app.task
def main_task():
    print("Running a periodic task!")
    a = the_task(4)
    b = the_task(7)
    c = depends_on_both()
    c.depends_on(a)
    c.depends_on(b)
    a.wait(0.02)
    b.wait(0.02)
    main_task().wait(0.01)