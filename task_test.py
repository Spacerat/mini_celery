from orchestrator import Client
from tasks import main_task
from app import app
from datetime import datetime, timedelta

def main():
    """ Start the main task at a 'set time' (which is actually one second from now) """
    app.flush()
    main_task(period=1).start_at(datetime.now()+timedelta(seconds=1))

if __name__ == '__main__':
    main()
