# export_utils.py
from flask import send_file, flash
from flask_mail import Message
from io import BytesIO
import pandas as pd
from .models import User, Document, Attendance, Leave, Holiday, Announcement
from . import mail

# USERS SHEET
def format_users():
    users = User.query.all()
    return pd.DataFrame([{
        "Employee Name": u.first_name,
        "Email": u.email,
        "Role": u.role.title() if u.role else "",
        "NAD ID": u.nad_id or "",
        "Earned Leaves": u.earned,
        "Medical Leaves": u.medic,
        "Pay Days": u.pay,
        "On Probation": "Yes" if u.probation else "No",
        "Joining Date": u.joining_date.strftime("%Y-%m-%d") if u.joining_date else ""
    } for u in users])


# ATTENDANCE SHEET
def format_attendance():
    records = Attendance.query.all()
    return pd.DataFrame([{
        "Date": a.date.strftime("%Y-%m-%d") if a.date else "",
        "Name": a.user.first_name if a.user else "",
        "Day": a.day or "",
        "Entry Time": a.entry_time.strftime("%H:%M") if a.entry_time else "",
        "Exit Time": a.exit_time.strftime("%H:%M") if a.exit_time else "",
        "Entry Location": a.entry_location or "",
        "Exit Location": a.exit_location or "",
        "Site (In)": a.site_name or "",
        "Site (Out)": a.site_name_e or "",
        "Total Hours": str(a.total_time_worked()) if a.total_time_worked() else "",
        "Exit Report Submitted": "Yes" if a.exit_report_submitted else "No",
        "Reason": a.reason or ""
    } for a in records])


# LEAVES SHEET
def format_leaves():
    leaves = Leave.query.all()
    return pd.DataFrame([{
        "Name": l.user.first_name if l.user else "",
        "Leave Type": l.ltype or "",
        "Start Date": l.start_date.strftime("%Y-%m-%d") if l.start_date else "",
        "End Date": l.end_date.strftime("%Y-%m-%d") if l.end_date else "",
        "Days": l.days,
        "Status": "Approved" if l.approved else "Rejected" if l.rejected else "Pending",
        "Approved By": l.approved_by or "",
        "Reason": l.reason or ""
    } for l in leaves])


# DOCUMENTS SHEET
def format_documents():
    docs = Document.query.all()
    return pd.DataFrame([{
        "Employee": d.user.first_name if d.user else "",
        "Document Type": d.document_type,
        "Filename": d.filename
    } for d in docs])


# HOLIDAYS SHEET
def format_holidays():
    holidays = Holiday.query.all()
    return pd.DataFrame([{
        "Holiday Name": h.name,
        "Date": h.date.strftime("%Y-%m-%d") if h.date else ""
    } for h in holidays])


# ANNOUNCEMENTS SHEET
def format_announcements():
    anns = Announcement.query.all()
    data = []
    for a in anns:
        recipients = ", ".join([u.first_name for u in a.recipients])
        acknowledged = ", ".join([ack.user.first_name for ack in a.acknowledgments])
        data.append({
            "Title": a.title,
            "Date Posted": a.date_posted.strftime("%Y-%m-%d") if a.date_posted else "",
            "Recipients": recipients,
            "Acknowledged By": acknowledged,
        })
    return pd.DataFrame(data)


# EXPORT REPORT TO EXCEL
def export_hr_report():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        format_users().to_excel(writer, sheet_name="Users", index=False)
        format_attendance().to_excel(writer, sheet_name="Attendance", index=False)
        format_leaves().to_excel(writer, sheet_name="Leaves", index=False)
        format_documents().to_excel(writer, sheet_name="Documents", index=False)
        format_holidays().to_excel(writer, sheet_name="Holidays", index=False)
        format_announcements().to_excel(writer, sheet_name="Announcements", index=False)
    output.seek(0)
    return output


# EMAIL THE REPORT
def send_hr_report_email(output):
    msg = Message(
        subject="HRMS System Report",
        recipients=["sumana@nadiya.in", "maneesh@nadiya.in", "support@nadiya.in"],
        body="Dear Team,\n\nPlease find attached the latest HRMS system report.\n\nRegards,\nHR Team"
    )
    msg.attach(
        "HRMS_Report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        output.read()
    )
    mail.send(msg)


# VIEW / ROUTE FUNCTION
def export_all_data():
    output = export_hr_report()
    try:
        send_hr_report_email(BytesIO(output.getvalue()))
        flash("Report generated and emailed successfully.", "success")
    except Exception as e:
        flash(f"Report generated but email failed: {e}", "warning")
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="HRMS_Report.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
