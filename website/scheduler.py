from apscheduler.schedulers.background import BackgroundScheduler
from .tasks import send_announcement_reminders
from .export_utils import export_hr_report, send_hr_report_email 
from datetime import datetime, timedelta

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
   
    def weekly_report():
        with app.app_context():
            try:
                output = export_hr_report()
                send_hr_report_email(output)
                print("✅ Weekly HR report emailed successfully.")
            except Exception as e:
                print(f"⚠️ Error sending HR report: {e}")

    scheduler.add_job(
        func=weekly_report,
        trigger='cron',
        day_of_week='mon',
        hour=9,
        minute=0,
        id='weekly_hr_report',
        replace_existing=True
    )


    scheduler.start()
