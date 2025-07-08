from flask import current_app
from .models import Announcement, AnnouncementAcknowledgment, User
from . import db, mail
from flask_mail import Message

def send_email(to, subject, body):
    msg = Message(subject=subject, recipients=[to], body=body)
    mail.send(msg)

def send_announcement_reminders(app):
    with app.app_context():
        unacknowledged = {}

        announcements = Announcement.query.all()
        for announcement in announcements:
            recipients = announcement.recipients
            acknowledged_ids = {ack.user_id for ack in announcement.acknowledgments}

            for user in recipients:
                if user.id not in acknowledged_ids:
                    # Group for summary reporting later
                    unacknowledged.setdefault(user.id, []).append(announcement)

                    # Notify user
                    if user.email:
                        subject = f"Reminder: Please acknowledge '{announcement.title}'"
                        body = (
                            f"Dear {user.first_name},\n\n"
                            f"You have not yet acknowledged the announcement titled:\n"
                            f"\"{announcement.title}\"\n\n"
                            f"Please review and acknowledge it at your earliest convenience.\n\n"
                            f"Regards,\nHR Team"
                        )
                        send_email(user.email, subject, body)

        # Notify admins (director, operations_head)
        if unacknowledged:
            summary_lines = []
            for user_id, pending_list in unacknowledged.items():
                user = User.query.get(user_id)
                if user:
                    titles = ", ".join(f"'{a.title}'" for a in pending_list)
                    summary_lines.append(f"{user.first_name} has not acknowledged: {titles}")

            if summary_lines:
                admin_subject = "Daily Report: Users Yet to Acknowledge Announcements"
                admin_body = (
                    "Dear Admin,\n\n"
                    "The following users have not acknowledged their assigned announcements:\n\n"
                    + "\n".join(summary_lines) +
                    "\n\nRegards,\nHR System"
                )

                directors = User.query.filter(User.role.in_(["director", "operations_head"])).all()
                for admin in directors:
                    if admin.email:
                        send_email(admin.email, admin_subject, admin_body)
