from orchestrator import Client
from tasks import main_task
from app import app

def main():
    app.flush()
    main_task().wait(1)

if __name__ == '__main__':
    main()


