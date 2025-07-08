# run_scheduler.py
from .scheduler import start_scheduler
from time import sleep

if __name__ == "__main__":
    print("Starting scheduler...")
    start_scheduler()
    while True:
        sleep(3600)  # keep the process alive
