""" This file simply runs a client which will connect to the broker, and process and run tasks """

from orchestrator import Client
from app import app
import tasks

def main():
    app.run()

if __name__ == '__main__':
    main()


