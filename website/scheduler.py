from apscheduler.schedulers.background import BackgroundScheduler
from .tasks import send_announcement_reminders

def start_scheduler(app):
    print("Scheduler started... (runs daily at 9:00 AM)")
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: send_announcement_reminders(app),
        trigger="cron",
        hour=9,
        minute=0,
        id='announcement_reminder',
        replace_existing=True
    )
    scheduler.start()
