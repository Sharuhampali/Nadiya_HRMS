#########################################################################################################################################################
#Imports
#########################################################################################################################################################

# Standard Library
import json
import os
import secrets
import uuid
from datetime import datetime, date, timedelta, time
from io import BytesIO

# Third-Party Libraries
import pandas as pd
import pytz
from dateutil.relativedelta import relativedelta
from geopy.geocoders import Nominatim
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

# Flask Core
from flask import (
    Blueprint, Flask, render_template, request, flash, jsonify,
    redirect, url_for, send_file, send_from_directory, abort, current_app
)
from flask_login import login_required, current_user
from flask_mail import Message
from flask_uploads import UploadSet, IMAGES, UploadNotAllowed

# Application Imports
from . import db, mail
from .models import (
    User, Attendance, Leave, Document, Holiday, Announcement,
    IntermediateLog, AnnouncementAcknowledgment, EditRequest,
    announcement_user, ExitReport, CompOffRequest
)
from leave_calculator import calculate_initial_leaves
from sqlalchemy import and_


#########################################################################################################################################################

views = Blueprint('views', __name__)
india_tz = pytz.timezone('Asia/Kolkata')

#########################################################################################################################################################
# Roles Hierarchy
ROLES_HIERARCHY = {
    # Lowest tier → respective manager(s)
    'design_member': ['design_head','operations_head', 'director'],
    'service_member': ['service_manager', 'operations_head', 'director'],
    'accounts_member': ['accounts_manager','operations_head','director'],
    
    # Mid-tier managers → higher-level director(s)
    'design_head': ['service-manager','director','operations_head'],
    'service_manager': ['director','operations_head'],
    'business_development_manager': ['director','operations_head'],
    'accounts_manager': ['director','operations_head'],

    # Director reports to operational head and vice versa 
    'director': ['operations_head'],
    'operations_head': ['director']
}

#########################################################################################################################################################

#Home Route - admin and user home views
# @views.route('/', methods=['GET', 'POST'])
# @login_required 
# def home():
#     current_date = datetime.now(india_tz).date().strftime("%d-%m-%y")
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in' and current_user.email!='support@nadiya.in' :
#         today = date.today()
#         people_on_leave_today = Leave.query.filter(
#         and_(
#             Leave.approved == True,
#             Leave.rejected != True,
#             Leave.from_date <= today,
#             Leave.to_date >= today
#         )
#         ).all()

    
    
#         return render_template(
#             "home.html",
#             user=current_user,
#             current_date=current_date,
#             people_on_leave_today=people_on_leave_today,
#         leave_count=len(people_on_leave_today)
            
#         )
#     users_count = User.query.count()
#     pending_leaves = Leave.query.filter(
#                         (Leave.approved == False) | (Leave.approved == None),
#                         (Leave.rejected == False) | (Leave.rejected == None)
#                                             ).count()

#     today_attendance = Attendance.query.filter_by(date=date.today()).count()
#     announcements_count = Announcement.query.count()
    
#     today = date.today()
#     people_on_leave_today = Leave.query.filter(
#         and_(
#             Leave.approved == True,
#             Leave.rejected != True,
#             Leave.start_date <= today,
#             Leave.end_date >= today
#         )
#     ).all()


    
 
#     return render_template("admin_home.html", user=current_user, current_date= current_date, users_count=users_count,
#             pending_leaves=pending_leaves,
#             today_attendance=today_attendance,
#             announcements_count=announcements_count,
#             people_on_leave_today=people_on_leave_today,
#         leave_count=len(people_on_leave_today))

# @views.route('/', methods=['GET', 'POST'])
# @login_required 
# def home():
#     current_date = datetime.now(india_tz).date().strftime("%d-%m-%y")
#     today = date.today()

#     # For regular users
#     if current_user.email not in ["sumana@nadiya.in", "maneesh@nadiya.in", "support@nadiya.in"]:
#         # Simple from_date / to_date logic
#         people_on_leave_today = Leave.query.filter(
#             and_(
#                 Leave.approved == True,
#                 Leave.rejected != True,
#                 Leave.start_date <= today,
#                 Leave.end_date >= today
#             )
#         ).all()
#         approved_leaves = Leave.query.filter(
#         Leave.approved == True
#     ).all()

#     # Now build a list of users who have any entry on today's date
#     people_on_leave_today = set()
#     for leave in approved_leaves:
#         try:
#             leave_data = json.loads(leave.leaves_data)
#             for entry in leave_data:
#                 if entry.get('date') == today.strftime('%Y-%m-%d'):
#                     people_on_leave_today.add(leave.user)  # leave.user is the actual User object
#         except Exception as e:
#             print(f"Error parsing leave data: {e}")
#             continue

#         return render_template(
#             "home.html",
#             user=current_user,
#             current_date=current_date,
#             people_on_leave_today=people_on_leave_today,
#             leave_count=len(people_on_leave_today)
#         )

#     # For Admins
#     users_count = User.query.count()
#     pending_leaves = Leave.query.filter(
#         (Leave.approved == False) | (Leave.approved == None),
#         (Leave.rejected == False) | (Leave.rejected == None)
#     ).count()

#     today_attendance = Attendance.query.filter_by(date=today).count()
#     announcements_count = Announcement.query.count()

#     approved_leaves = Leave.query.filter(
#         Leave.approved == True
#     ).all()

#     # Now build a list of users who have any entry on today's date
#     people_on_leave_today = set()
#     for leave in approved_leaves:
#         try:
#             leave_data = json.loads(leave.leaves_data)
#             for entry in leave_data:
#                 if entry.get('date') == today.strftime('%Y-%m-%d'):
#                     people_on_leave_today.add(leave.user)  # leave.user is the actual User object
#         except Exception as e:
#             print(f"Error parsing leave data: {e}")
#             continue

#     return render_template(
#         "admin_home.html",
#         user=current_user,
#         current_date=current_date,
#         users_count=users_count,
#         pending_leaves=pending_leaves,
#         today_attendance=today_attendance,
#         announcements_count=announcements_count,
#         people_on_leave_today=list(people_on_leave_today),
#         leave_count=len(people_on_leave_today)
#     )
@views.route('/', methods=['GET', 'POST'])
@login_required 
def home():
    current_date = datetime.now(india_tz).date().strftime("%d-%m-%y")
    today = datetime.now(india_tz).date()

    # Common function to get people on leave today
    def get_people_on_leave():
        approved_leaves = Leave.query.filter(Leave.approved == True).all()
        people_on_leave_today = set()
        for leave in approved_leaves:
            try:
                leave_data = json.loads(leave.leaves_data)
                for entry in leave_data:
                    if entry.get('date') == today.strftime('%Y-%m-%d'):
                        people_on_leave_today.add(leave.user)
            except Exception as e:
                print(f"Error parsing leave data: {e}")
                continue
        return approved_leaves, people_on_leave_today

    # For regular users
    if current_user.email not in ["sumana@nadiya.in", "maneesh@nadiya.in", "support@nadiya.in", "accounts@nadiya.in"]:
        approved_leaves, people_on_leave_today = get_people_on_leave()
        return render_template(
            "home.html",
            user=current_user,
            current_date=current_date,
            people_on_leave_today=people_on_leave_today,
            leave_count=len(people_on_leave_today)
        )

    # For Admins
    users_count = User.query.count()
    pending_leaves = Leave.query.filter(
        (Leave.approved == False) | (Leave.approved == None),
        (Leave.rejected == False) | (Leave.rejected == None)
    ).count()
    today_attendance = Attendance.query.filter_by(date=today).count()
    announcements_count = Announcement.query.count()

    approved_leaves, people_on_leave_today = get_people_on_leave()

    return render_template(
        "admin_home.html",
        user=current_user,
        current_date=current_date,
        users_count=users_count,
        pending_leaves=pending_leaves,
        today_attendance=today_attendance,
        announcements_count=announcements_count,
        people_on_leave_today=list(people_on_leave_today),
        leave_count=len(people_on_leave_today)
    )

#########################################################################################################################################################
#Attendance Routes
#########################################################################################################################################################

# Initialize geolocator for address lookup
geoLoc = Nominatim(user_agent="hrms-app")

# Attendance home route
@views.route('/attendance-category')
@login_required
def attendance_category():
    return render_template('attendance_category.html', user=current_user)

# @views.route('/attendance')
# @login_required
# def attendance_form():
#     from datetime import datetime
#     from pytz import timezone

#     india_tz = timezone('Asia/Kolkata')
#     today = datetime.now(india_tz).date()
#     user_id = current_user.id
#     name = current_user.first_name

#     # Get all today's attendance records for the user
#     attendances = Attendance.query.filter_by(user_id=user_id, date=today).all()
#     attendance_ids = [a.id for a in attendances]

#     # Check if any exit report exists for these attendance IDs
#     has_exit_report = False
#     attendance_id = None

#     if attendance_ids:
#         attendance_id = attendance_ids[-1]  # any valid one will do for the link
#         has_exit_report = ExitReport.query.filter(ExitReport.attendance_id.in_(attendance_ids)).first() is not None

#     return render_template(
#         'attendance.html',
#         name=name,
#         has_exit_report=has_exit_report,
#         attendance_id=attendance_id
#     )
@views.route('/attendance')
@login_required
def attendance_form():
    from datetime import datetime
    from pytz import timezone

    india_tz = timezone('Asia/Kolkata')
    today = datetime.now(india_tz).date()
    user_id = current_user.id
    name = current_user.first_name

    attendances = Attendance.query.filter_by(user_id=user_id, date=today).all()
    attendance_id = attendances[-1].id if attendances else None
    attendance = attendances[-1] if attendances else None


    return render_template(
        'attendance.html',
        name=name,
        attendance_id=attendance_id,
            attendance=attendance

    )



# attendance submission route
@views.route('/submit', methods=['POST'])
@login_required
def submit_attendance():
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    entry_exit = request.form.get('entry_exit')  # 'entry', 'exit', etc.
    site_name = request.form.get('site_name')    # For exit or intermediate
    reason = request.form.get('reason', None)

    user_id = current_user.id
    india_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(india_tz)
    now_time = now.time()

    # user_attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.id.desc()).first()
    today = now.date()
    user_attendance = Attendance.query.filter_by(user_id=user_id, date=today).first()


    # Handle stale entries with no exit for > 20 hours
    if user_attendance and user_attendance.exit_time is None:
        time_diff = datetime.combine(now.date(), now_time) - datetime.combine(now.date(), user_attendance.entry_time)
        if time_diff > timedelta(hours=20):
            user_attendance.exit_time = (datetime.combine(now.date(), user_attendance.entry_time) + timedelta(hours=5)).time()
            user_attendance.calculate_comp_off()
            try:
                db.session.commit()
            except Exception as e:
                print(e)
                flash('There was an issue updating your attendance record.', 'error')
                return redirect(url_for('views.home'))
            # user_attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.id.desc()).first()
            today = now.date()
            user_attendance = Attendance.query.filter_by(user_id=user_id, date=today).first()


    # Determine last known state
    today = now.date()
    last_main = None
    if user_attendance and user_attendance.exit_time is None:
        last_main = 'entry'
    elif user_attendance and user_attendance.exit_time:
        last_main = 'exit'

    last_log = IntermediateLog.query.filter_by(
        user_id=user_id,
        date=today
    ).order_by(IntermediateLog.id.desc()).first()

    last_inter = last_log.entry_type if last_log else None

    if last_main == 'exit':
        last_state = 'exit'
    else:
        last_state = last_inter if last_inter else last_main


    # Allowed transitions
    valid_next = {
        None: ['entry'],
        'entry': ['intermediate_exit', 'exit'],
        'intermediate_exit': ['intermediate_entry', 'exit'],
        'intermediate_entry': ['intermediate_exit', 'exit'],
        'exit': ['entry'],
    }

    if entry_exit not in valid_next.get(last_state, []):
        readable = last_state.replace('_', ' ') if last_state else 'None'
        flash(f"Invalid attendance sequence. After '{readable}', you may only do: {', '.join(valid_next.get(last_state, []))}.", 'warning')
        return redirect(url_for('views.home'))

    # Handle intermediate entries
    if entry_exit in ['intermediate_entry', 'intermediate_exit']:
        try:
            location_obj = geoLoc.reverse(f"{latitude}, {longitude}")
            location = location_obj.address if location_obj else "Unknown"
        except Exception as e:
            print(f"Intermediate geo error: {e}")
            location = "Unknown"

        new_log = IntermediateLog(
            user_id=current_user.id,
            date=today,
            time=now_time.replace(microsecond=0),
            entry_type=entry_exit,
            latitude=latitude,
            longitude=longitude,
            location=location,
            site=site_name
        )
        db.session.add(new_log)
        db.session.commit()
        flash(f"{entry_exit.replace('_', ' ').capitalize()} recorded.", "success")
        return redirect(url_for('views.home'))

    # Entry logic
    elif entry_exit == 'entry':
        site_name = request.form.get('site_name')
        try:
            entry_location = geoLoc.reverse(f"{latitude}, {longitude}")
            entry_address = entry_location.address if entry_location else "Unknown"
        except Exception as e:
            print(f"Error fetching entry location: {str(e)}")
            entry_address = "Unknown"

        new_attendance = Attendance(
            name=current_user.first_name,
            latitude=latitude,
            longitude=longitude,
            entry_location=entry_address,
            user_id=user_id,
            entry_time=now_time.replace(microsecond=0),
            date=today,
            day=now.strftime('%A'),
            reason=reason,
            site_name_e=site_name
        )
        db.session.add(new_attendance)

    # Exit logic
    elif entry_exit == 'exit' and user_attendance:
        if user_attendance and not user_attendance.exit_report_submitted:
                flash("You must complete the exit report before submitting exit attendance.", "warning")
                return redirect(url_for('views.attendance_form'))

        site_name = request.form.get('site_name')
        try:
            exit_location = geoLoc.reverse(f"{latitude}, {longitude}")
            exit_address = exit_location.address if exit_location else "Unknown"
        except Exception as e:
            print(f"Error fetching exit location: {str(e)}")
            exit_address = "Unknown"

        def is_second_or_fourth_saturday(date):
            first = date.replace(day=1)
            first_weekday = first.weekday()
            first_sat = first + timedelta(days=(5 - first_weekday) % 7)
            second_sat = first_sat + timedelta(days=7)
            fourth_sat = first_sat + timedelta(days=21)
            return date == second_sat or date == fourth_sat

        def is_holiday(date):
            if(current_user.email == 'support@nadiya.in'):
                return date.weekday() == 6 or date.weekday() == 5 
            return date.weekday() == 6 or is_second_or_fourth_saturday(date)

        if request.form.get('holiday'):
            user_attendance.hol = 10000

        if Holiday.query.filter_by(date=today).first() or is_holiday(today):
            user_attendance.hol = 10000

        user_attendance.exit_time = now_time.replace(microsecond=0)
        user_attendance.exit_location = exit_address
        user_attendance.site_name = site_name
        user_attendance.calculate_comp_off()
      
       
        

    # Final DB commit
    # try:
    #     db.session.commit()
    #     if( entry_exit == 'exit'):
    #         return redirect(url_for('views.exit_report_form', attendance_id=user_attendance.id))
    #     else:
    #         flash('Attendance entry recorded successfully.', 'success')
    #         db.session.commit()
    try:
        db.session.commit()
        flash("Attendance marked successfully", "success")

        # if( entry_exit == 'exit'):
        #      return redirect(url_for('views.exit_report_form', attendance_id=user_attendance.id))
        return redirect(url_for('views.home'))
    except Exception as e:
        print(e)
        flash('There was an issue submitting your attendance.', 'error')
        return redirect(url_for('views.home'))
        
   
    

# Attendance table route
# @views.route('/attendance_table')
# @login_required
# def attendance_table():
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
#         flash("You do not have permission to view this page.", category='error')
#         return redirect(url_for('views.home'))

#     attendances = Attendance.query.all()


#     return render_template('attendance_table.html', attendances=attendances)

from sqlalchemy import desc
from datetime import timedelta

@views.route('/attendance_table')
@login_required
def attendance_table():
    if current_user.email not in ['sumana@nadiya.in', 'maneesh@nadiya.in', 'support@nadiya.in', "accounts@nadiya.in"]:
        flash("You do not have permission to view this page.", category='error')
        return redirect(url_for('views.home'))

    date_str = request.args.get('date')
    india_tz = pytz.timezone('Asia/Kolkata')
    today = datetime.now(india_tz).date()

    # If no date provided, default to latest available date
    if not date_str:
        latest_entry = Attendance.query.order_by(Attendance.date.desc()).first()
        target_date = latest_entry.date if latest_entry else today
    else:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    attendances = Attendance.query.filter_by(date=target_date).order_by(desc(Attendance.entry_time)).all()

    # Get next and previous dates available in the DB
    next_date = (
        Attendance.query
        .filter(Attendance.date > target_date)
        .order_by(Attendance.date.asc())
        .first()
    )

    prev_date = (
        Attendance.query
        .filter(Attendance.date < target_date)
        .order_by(Attendance.date.desc())
        .first()
    )

    return render_template(
        'attendance_table.html',
        attendances=attendances,
        target_date=target_date,
        prev_date=prev_date.date if prev_date else None,
        next_date=next_date.date if next_date else None
    )



def convert_to_str(time_obj):
        if isinstance(time_obj, time):
            return time_obj.strftime("%H:%M")
        elif time_obj is None:
            return None
        return time_obj

def is_late(entry_time, ideal_entry="09:30"):
        entry_time = convert_to_str(entry_time)
        entry = datetime.strptime(entry_time, "%H:%M")
        ideal = datetime.strptime(ideal_entry, "%H:%M")
        return entry > ideal

# #search attendance user route
# @views.route('/who', methods=['GET','POST'])
# @login_required
# def who():
#     return render_template('who.html')

# def send_email(recipient, subject, body, html=False):
#     msg = Message(subject, recipients=[recipient])
#     if html:
#         msg.html = body
#     else:
#         msg.body = body
#     mail.send(msg)

#user attendance table
@views.route('/who_output', methods=['GET','POST'])
@login_required
def who_output():
    name = current_user.first_name

    user_attendances = Attendance.query.filter_by(name=name).all()
    totes = sum(attendance.totes for attendance in user_attendances)
    late_entries = sum(1 for attendance in user_attendances if is_late(attendance.entry_time))

    return render_template('who_output.html', attendances=user_attendances, name=name,totes = totes, late_entries = late_entries)

#intermediate logs display route
@views.route('/detailed_view/<int:user_id>/<date>')
@login_required
def detailed_view(user_id, date):
    from datetime import datetime
    user = User.query.get_or_404(user_id)
    parsed_date = datetime.strptime(date, '%Y-%m-%d').date()
    logs = IntermediateLog.query.filter_by(
        user_id=user_id,
        date=parsed_date
    ).order_by(IntermediateLog.time).all()
    attendance = Attendance.query.filter_by(user_id=user_id, date=date).first()


    return render_template('detailed_view.html', logs=logs, user=user, date=parsed_date, attendance=attendance)

#request edit attendance time route
@views.route('/request_edit', methods=['POST'])
@login_required
def request_edit():
    if current_user.email != 'sumana@nadiya.in':
        flash("You do not have permission to request edits.", 'error')
        return redirect(url_for('views.home'))

    attendance_id = request.form.get('attendance_id')
    new_entry = request.form.get('entry_time')  # format: HH:MM
    new_exit = request.form.get('exit_time')
    reason = request.form.get('reason')

    # Fetch the attendance record to get user_id
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        flash("Invalid attendance record.", 'error')
        return redirect(url_for('views.home'))

    token = secrets.token_hex(32)
    req = EditRequest(
        attendance_id=attendance_id,
        user_id=attendance.user_id,  # <-- Add this line to fix NotNullViolation
        requested_by=current_user.email,
        entry_time=datetime.strptime(new_entry, "%H:%M").time() if new_entry else None,
        exit_time=datetime.strptime(new_exit, "%H:%M").time() if new_exit else None,
        reason=reason,
        token=token,
        status='pending'
    )
    db.session.add(req)
    db.session.commit()

    # Send approval email 
    approval_link = url_for('views.edit_requests', _external=True)
    send_email(
        recipient="maneesh@nadiya.in",
        subject="Attendance Edit Request Approval",
        body=(
            f"{current_user.email} has requested to edit attendance record ID {attendance_id}.\n\n"
            f"Reason: {reason}\n\n"
            f"Review & Approve Here: {approval_link}"
        )
    )
    flash("Edit request sent for approval.", "info")
    return redirect(url_for('views.home'))

# Approve edit request via token
@views.route('/approve_edit/<token>')
def approve_edit(token):
    req = EditRequest.query.filter_by(token=token, status='pending').first()
    if not req:
        return "Invalid or expired token.", 400

    attendance = Attendance.query.get(req.attendance_id)

    if not attendance:
        return f"""
        Attendance record not found for ID {req.attendance_id}.<br><br>
        Requested Edit:<br>
        Name: {req.user.first_name if req.user else 'Unknown'}<br>
        Entry: {req.entry_time}<br>
        Exit: {req.exit_time}<br>
        Reason: {req.reason}<br>
        (Request ID: {req.id})
        """, 404

    if req.entry_time:
        attendance.entry_time = req.entry_time
    if req.exit_time:
        attendance.exit_time = req.exit_time

    req.status = 'approved'
    db.session.commit()

    return f"""
    ✅ Edit approved and applied for {req.user.first_name}Attendance ID {req.attendance_id}.<br><br>
    New Entry Time: {attendance.entry_time}<br>
    New Exit Time: {attendance.exit_time}<br>
    Request ID: {req.id}
    """

# Edit requests management route
@views.route('/edit_requests')
@login_required
def edit_requests():
    if current_user.email not in ['maneesh@nadiya.in', 'hampalisharu@gmail.com']:
        flash("Unauthorized access.", "error")
        return redirect(url_for('views.home'))


    pending_requests = EditRequest.query.filter_by(status='pending').order_by(EditRequest.created_at.desc()).all()
    return render_template('edit_requests.html', requests=pending_requests)


# Approve or reject edit requests
@views.route('/edit_requests/approve/<int:request_id>', methods=['POST'])
@login_required
def approve_edit_request(request_id):
    req = EditRequest.query.get_or_404(request_id)

    if req.status != 'pending':
        flash("Request already processed.", "warning")
        return redirect(url_for('views.edit_requests'))

    attendance = Attendance.query.get(req.attendance_id)

    if not attendance:
        flash(f"No attendance record found for ID {req.attendance_id}.", "error")
        return redirect(url_for('views.edit_requests'))

    if req.entry_time:
        attendance.entry_time = req.entry_time
    if req.exit_time:
        attendance.exit_time = req.exit_time

    req.status = 'approved'
    db.session.commit()

    # ✅ Send approval email
    send_email(
        recipient=req.requested_by,
        subject="Attendance Edit Request Approved",
        body=(
            f"Hello,\n\n"
            f"Your request to edit {req.user.first_name}'s attendance has been approved.\n\n"
            f"New Entry Time: {attendance.entry_time.strftime('%H:%M') if attendance.entry_time else '—'}\n"
            f"New Exit Time: {attendance.exit_time.strftime('%H:%M') if attendance.exit_time else '—'}\n\n"
            f"Best regards,\nHR Team"
        )
    )

    flash(f"Approved request {request_id}.", "success")
    return redirect(url_for('views.edit_requests'))


@views.route('/edit_requests/reject/<int:request_id>', methods=['POST'])
@login_required
def reject_edit_request(request_id):
    req = EditRequest.query.get_or_404(request_id)

    if req.status != 'pending':
        flash("Request already processed.", "warning")
        return redirect(url_for('views.edit_requests'))

    remarks = request.form.get('remarks')

    req.status = 'rejected'
    db.session.commit()

    # ❌ Send rejection email with remarks
    send_email(
        recipient=req.requested_by,
        subject="Attendance Edit Request Rejected",
        body=(
            f"Hello,\n\n"
            f"Your request to edit {req.user.first_name}'s attendance has been rejected.\n\n"
            f"Remarks: {remarks}\n\n"
            f"Best regards,\nHR Team"
        )
    )

    flash(f"Rejected request {request_id}.", "info")
    return redirect(url_for('views.edit_requests'))

#########################################################################################################################################################
#Leave Routes
#########################################################################################################################################################

#leave home route
@views.route('/leaves-category')
@login_required
def leaves_category():
    return render_template('leaves_category.html', user=current_user)

# # Apply leave route
# @views.route('/approve_leave/<int:leave_id>', methods=['POST'])
# @login_required
# def approve_leave(leave_id):
#     leave = Leave.query.get(leave_id)
#     if not leave:
#         flash("Leave request not found.", category='error')c
#         return redirect(url_for('views.home'))

#     if leave.approved or leave.rejected:
#         flash("This leave has already been processed.", category='warning')
#         return redirect(url_for('views.leave_requests'))

#     leave.approved = True
#     leave.approved_by = current_user.email
#     db.session.commit()

#     user = User.query.get(leave.user_id)

#     # Compose detailed approval message
#     leave_summary = json.loads(leave.leaves_data or "[]")
#     details = '\n'.join(
#         f"- {entry['date']}: {entry['duration']} day(s) - {entry['type']}" 
#         for entry in leave_summary
#     )

#     send_email(
#         'Leave Approved',
#         user.email,
#         f"Your leave request has been approved.\n\n"
#         f"Total Days: {leave.days}\n"
#         f"Types: {leave.ltype}\n"
#         f"Details:\n{details}\n\n"
#         f"Approved by: {current_user.email}"
#     )

#     return redirect(url_for('views.leave_requests'))

# # Reject leave route
# @views.route('/reject/<int:leave_id>', methods=['POST'])
# @login_required
# def reject(leave_id):
#     leave = Leave.query.get(leave_id)
#     if not leave:
#         flash("Leave request not found.", category='error')
#         return redirect(url_for('views.leave_requests'))

#     user = User.query.get(leave.user_id)
#     if not user:
#         flash("User not found.", category='error')
#         return redirect(url_for('views.leave_requests'))

#     remarks = request.form.get('remarks') or "No remarks provided."
#     leave.approved_by = current_user.email
#     leave.rejected = True
#     leave.remarks = remarks  # Optional: only if you have a 'remarks' field in Leave model

#     # Reverse leave balances using leaves_data breakdown
#     import json
#     entries = json.loads(leave.leaves_data)

#     for entry in entries:
#         date = entry['date']
#         duration = float(entry['duration'])
#         ltype = entry['type']

#         if ltype == 'Compoff':
#             for att in user.attendances:
#                 if att.date.strftime('%Y-%m-%d') == date:
#                     att.compoff += duration
#                     break
#             else:
#                 if user.attendances:
#                     user.attendances[0].compoff += duration

#         elif ltype == 'Earned':
#             user.earned -= duration

#         elif ltype == 'Leave w/o Pay':
#             user.pay -= duration

#         elif ltype == 'Medical/Sick':
#             user.medic -= duration

#     db.session.commit()
#     flash("Leave request rejected and leave balances restored.", "info")

#     # Construct email summary
#     leave_summary = json.loads(leave.leaves_data or "[]")
#     details = '\n'.join(
#         f"- {entry['date']}: {entry['duration']} day(s) - {entry['type']}"
#         for entry in leave_summary
#     )

#     send_email(
#         subject='Leave Rejected',
#         recipient=user.email,
#         body=(
#             f"Your leave request has been rejected.\n\n"
#             f"Dates: {leave.start_date} to {leave.end_date}\n"
#             f"Total Days: {leave.days}\n"
#             f"Types: {leave.ltype}\n"
#             f"Details:\n{details}\n\n"
#             f"Rejected by: {current_user.email}\n"
#             f"Remarks: {remarks}"
#         )
#     )

#     return redirect(url_for('views.leave_requests'))
@views.route('/approve_leave/<int:leave_id>', methods=['POST'])
@login_required
def approve_leave(leave_id):
    leave = Leave.query.get(leave_id)
    if not leave:
        flash("Leave request not found.", category='error')
        return redirect(url_for('views.home'))

    if leave.approved or leave.rejected:
        flash("This leave has already been processed.", category='warning')
        return redirect(url_for('views.leave_requests'))

    leave.approved = True
    leave.approved_by = current_user.email

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("DB commit failed on approve:", e)
        flash("Something went wrong. Please try again.", "error")
        return redirect(url_for('views.leave_requests'))

    user = User.query.get(leave.user_id)

    try:
        leave_summary = json.loads(leave.leaves_data or "[]")
    except json.JSONDecodeError:
        leave_summary = []

    details = '\n'.join(
        f"- {entry.get('date', '?')}: {entry.get('duration', '?')} day(s) - {entry.get('type', '?')}"
        for entry in leave_summary
    )

    try:
        send_email(
            'Leave Approved',
            user.email,
            f"Your leave request has been approved.\n\n"
            f"Total Days: {leave.days}\n"
            f"Types: {leave.ltype}\n"
            f"Details:\n{details}\n\n"
            f"Approved by: {current_user.email}"
        )
    except Exception as e:
        print("Email failed:", e)
        flash("Leave approved, but email could not be sent.", "warning")

    return redirect(url_for('views.leave_requests'))

@views.route('/reject/<int:leave_id>', methods=['POST'])
@login_required
def reject(leave_id):
    leave = Leave.query.get(leave_id)
    if not leave:
        flash("Leave request not found.", category='error')
        return redirect(url_for('views.leave_requests'))

    user = User.query.get(leave.user_id)
    if not user:
        flash("User not found.", category='error')
        return redirect(url_for('views.leave_requests'))

    remarks = request.form.get('remarks') or "No remarks provided."
    leave.approved_by = current_user.email
    leave.rejected = True
    leave.remarks = remarks

    try:
        entries = json.loads(leave.leaves_data or "[]")
    except json.JSONDecodeError:
        entries = []

    for entry in entries:
        try:
            date = entry['date']
            duration = float(entry['duration'])
            ltype = entry['type']
        except (KeyError, ValueError, TypeError) as e:
            print(f"Skipping malformed entry: {entry} – Error: {e}")
            continue

        if ltype == 'Compoff':
            rollback = duration
            used_requests = CompOffRequest.query.filter_by(user_id=user.id, status='approved', used=True).order_by(CompOffRequest.requested_on.desc()).all()

            for req in used_requests:
                if rollback <= 0:
                    break
                req.used = False
                rollback -= req.value

            else:
                if user.attendances:
                    user.attendances[0].compoff += duration

        elif ltype == 'Earned':
            user.earned -= duration

        elif ltype == 'Leave w/o Pay':
            user.pay -= duration

        elif ltype == 'Medical/Sick':
            user.medic -= duration

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("DB commit failed on reject:", e)
        flash("Something went wrong while rejecting leave.", "error")
        return redirect(url_for('views.leave_requests'))

    # Compose summary
    details = '\n'.join(
        f"- {entry.get('date', '?')}: {entry.get('duration', '?')} day(s) - {entry.get('type', '?')}"
        for entry in entries
    )

    try:
        send_email(
            subject='Leave Rejected',
            recipient=user.email,
            body=(
                f"Your leave request has been rejected.\n\n"
                f"Dates: {leave.start_date} to {leave.end_date}\n"
                f"Total Days: {leave.days}\n"
                f"Types: {leave.ltype}\n"
                f"Details:\n{details}\n\n"
                f"Rejected by: {current_user.email}\n"
                f"Remarks: {remarks}"
            )
        )
    except Exception as e:
        print("Email failed:", e)
        flash("Leave rejected, but email could not be sent.", "warning")

    flash("Leave request rejected and leave balances restored.", "info")
    return redirect(url_for('views.leave_requests'))



#display approved leaves 
import json

@views.route('/approved_leaves')
@login_required
def approved_leaves():
    leaves = Leave.query.filter_by(user_id=current_user.id).order_by(Leave.start_date.desc()).all()
    structured_leaves = []

    for leave in leaves:
        try:
            entries = json.loads(leave.leaves_data or "[]")
        except Exception:
            entries = []

        structured_leaves.append({
            "leave": leave,
            "entries": entries
        })

    return render_template("approved_leaves.html", leaves=structured_leaves)

# @views.route('/reset_leaves', methods=['GET', 'POST'])
# @login_required
# def reset_leaves():
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in' and current_user.email!='support@nadiya.in':
#         flash("You do not have permission to reset leaves.", category='error')
#         return redirect(url_for('views.home'))

#     users = User.query.all()
#     for user in users:
#         attendances = Attendance.query.filter_by(user_id=user.id).all()

#         # Reset compoff for each attendance record
#         for attendance in attendances:
#             attendance.compoff = 0

#     for user in users:
#         e = min(10, 15 - user.earned)

#     for user in users:
#         user.medic = 0
#         user.pay = 0
#         user.earned = 0 - e
#         # Add other leave types if applicable

#     # Delete all contents of the Holiday table
#     holidays = Holiday.query.all()
#     for holiday in holidays:
#         db.session.delete(holiday)

#     db.session.commit()
#     flash("All users' leave counts have been reset to zero, and all holidays have been deleted.", category='success')
#     return redirect(url_for('views.home'))
@views.route('/reset_leaves', methods=['GET', 'POST'])
@login_required
def reset_leaves():
    # Only allow extremely specific users
    if current_user.email not in ["sumana@nadiya.in", "maneesh@nadiya.in"]:
        flash("You do not have permission to reset leaves.", category='error')
        return redirect(url_for('views.home'))

    # Require POST confirmation via a form
    if request.method == 'POST':
        confirm = request.form.get('confirm_reset')
        if confirm != 'RESET':
            flash("Reset not confirmed. Type 'RESET' to confirm.", category='warning')
            return redirect(url_for('views.reset_leaves'))

        # Proceed with irreversible actions
        users = User.query.all()

        # Reset compoff in attendance
        for user in users:
            # Mark all approved comp offs as used
            all_requests = CompOffRequest.query.filter_by(status='approved', used=False).all()
            for req in all_requests:
                req.used = True


        # Reset other leave counters
        for user in users:
            e = min(10, 15 - user.earned)
            user.medic = 0
            user.pay = 0
            user.earned = 0 - e

        # Delete holidays
        for holiday in Holiday.query.all():
            db.session.delete(holiday)

        db.session.commit()
        flash("Leave counts reset and holidays deleted successfully.", category='success')
        return redirect(url_for('views.home'))

    return render_template('confirm_reset.html')


#display user leave summary
@views.route('/who1', methods=['GET','POST'])
@login_required
def who1():
    users =  User.query.all()
    return render_template('who1.html', users=users)

from datetime import date

@views.route('/who1_output', methods=['POST'])
@login_required
def who1_output():
    name = request.form.get('name')

    # Get the user based on the name
    user = User.query.filter_by(first_name=name).first()
    if not user:
        flash("User not found.", category='error')
        return redirect(url_for('views.home'))

    # Determine the current financial year
    today = date.today()
    if today.month >= 4:
        start_of_fy = date(today.year, 4, 1)
        end_of_fy = date(today.year + 1, 3, 31)
    else:
        start_of_fy = date(today.year - 1, 4, 1)
        end_of_fy = date(today.year, 3, 31)

    # Get approved leaves for the user within the current financial year
    approved_leaves = Leave.query.filter(
        Leave.user_id == user.id,
        Leave.approved == True,
        Leave.start_date >= start_of_fy,
        Leave.end_date <= end_of_fy
    ).all()

    earned_sum = 0
    medic_sum = 0
    pay_sum = 0

    # for leave in approved_leaves:
    #     leave_data = json.loads(leave.leaves_data)
    #     for entry in leave_data:
    #         ltype = entry.get('type')
    #         duration = float(entry.get('duration', 0))
    #         if ltype == 'Earned':
    #             earned_sum += duration
    #         elif ltype == 'Medical/Sick':
    #             medic_sum += duration
    #         elif ltype == 'Leave w/o Pay':
    #             pay_sum += duration
    detailed_entries = []

    for leave in approved_leaves:
        leave_data = json.loads(leave.leaves_data)
        for entry in leave_data:
            detailed_entries.append({
                'type': entry.get('type'),
                'date': entry.get('date'),
                'duration': entry.get('duration'),
                'reason': leave.reason,
                'approved_by': leave.approved_by,
            })
            ltype = entry.get('type')
            duration = float(entry.get('duration', 0))
            if ltype == 'Earned':
                earned_sum += duration
            elif ltype == 'Medical/Sick':
                medic_sum += duration
            elif ltype == 'Leave w/o Pay':
                pay_sum += duration


    return render_template(
    'who1_output.html',
    user=user,
    approved_leaves=approved_leaves,
    earned_sum=earned_sum,
    medic_sum=medic_sum,
    pay_sum=pay_sum,
    detailed_entries=detailed_entries
)
# return render_template('who1_output.html', user=user, approved_leaves=approved_leaves, earned_sum=earned_sum, medic_sum=medic_sum, pay_sum=pay_sum)

#manager view for leave requests
@views.route('/leave_requests')
@login_required
def leave_requests():
    user_role = current_user.role
    print(f"Current user's role: {user_role}")
    # Get all roles where current user is a manager (i.e., in the value list of ROLES_HIERARCHY)
    subordinate_roles = [role for role, managers in ROLES_HIERARCHY.items() if user_role in managers]

    if not subordinate_roles:
        flash("You do not have permission to view leave requests.", category='error')
        return redirect(url_for('views.home'))
    
    # Fetch leave requests for users with subordinate roles
    leave_requests = Leave.query.join(User).filter(User.role.in_(subordinate_roles)).all()
    for leave in leave_requests:
        try:
            leave.leave_entries = json.loads(leave.leaves_data)
        except Exception as e:
            print(f"Error parsing leave data for Leave ID {leave.id}: {e}")
            leave.leave_entries = []

    return render_template('leave_requests.html', leave_requests=leave_requests)




#apply leaves
@views.route('/apply_leave', methods=['GET', 'POST'])
@login_required
def apply_leave():
    if request.method == 'POST':
        dates = request.form.getlist('leave_dates')
        durations = request.form.getlist('leave_durations')
        types = request.form.getlist('leave_types')
        reason = request.form.get('reason', None)

        leave_entries = []
        total_days = 0.0
        summary = {'Earned': 0.0, 'Medical/Sick': 0.0, 'Compoff': 0.0, 'Leave w/o Pay': 0.0}

        # Available leave balances
        available_balances = {
            'Earned': 15 - current_user.earned,
            'Medical/Sick': 6 - current_user.medic,
            'Leave w/o Pay': 10 - current_user.pay,
            'Compoff': current_user.total_compoff
        }

        # Row-by-row validation and leave entry collection
        for date_str, dur_str, ltype in zip(dates, durations, types):
            if not date_str or not ltype:
                continue  # Skip incomplete rows

            duration = float(dur_str)

            # Check availability per row
            if ltype not in available_balances:
                flash(f"Invalid leave type: {ltype}", 'error')
                return redirect(url_for('views.apply_leave'))

            if available_balances[ltype] < duration:
                flash(f"Not enough {ltype} leave available. You tried to use {duration}, but only {available_balances[ltype]:.1f} left.", 'error')
                return redirect(url_for('views.apply_leave'))

            available_balances[ltype] -= duration
            summary[ltype] += duration
            total_days += duration

            leave_entries.append({
                'date': date_str,
                'duration': duration,
                'type': ltype
            })

        # Deduct compoff from approved requests
        if summary['Compoff'] > 0:
            remaining = summary['Compoff']
            requests = CompOffRequest.query.filter_by(user_id=current_user.id, status='approved', used=False).order_by(CompOffRequest.requested_on).all()
            
            for req in requests:
                if remaining <= 0:
                    break
                if req.value <= remaining:
                    req.used = True
                    remaining -= req.value
                else:
                    # If comp off request is larger than needed, skip for now (or implement split logic)
                    continue


        # Apply to user leave counts
        current_user.medic += summary['Medical/Sick']
        current_user.earned += summary['Earned']
        current_user.pay += summary['Leave w/o Pay']

        start_date = min(datetime.strptime(entry['date'], '%Y-%m-%d').date() for entry in leave_entries)
        end_date = max(datetime.strptime(entry['date'], '%Y-%m-%d').date() for entry in leave_entries)

        new_leave = Leave(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            days=total_days,
            ltype=', '.join(sorted({entry['type'] for entry in leave_entries})),
            leaves_data=json.dumps(leave_entries)
        )

        db.session.add(new_leave)
        db.session.commit()

        # Manager notification
        manager_roles = ROLES_HIERARCHY.get(current_user.role)
        if not manager_roles:
            flash("No manager assigned for your role.", 'error')
            return redirect(url_for('views.apply_leave'))
        if isinstance(manager_roles, str):
            manager_roles = [manager_roles]

        managers = User.query.filter(User.role.in_(manager_roles)).all()
        recipient_emails = [m.email for m in managers if m.email]

        STATIC_MANAGER_EMAIL = "sumana@nadiya.in"
        if STATIC_MANAGER_EMAIL not in recipient_emails:
            recipient_emails.append(STATIC_MANAGER_EMAIL)

        approval_url = url_for('views.leave_requests', _external=True)

        msg = Message('New Leave Application', recipients=recipient_emails)
        msg.body = (
            f"Dear Approver,\n\n"
            f"{current_user.first_name} has submitted a leave application.\n\n"
            f"📅 Total Days: {total_days}\n"
            f"🗂️ Breakdown:\n" +
            '\n'.join([f"  • {k}: {v} day(s)" for k, v in summary.items() if v > 0]) +
            f"\n\n📝 Reason: {reason or 'Not specified'}\n\n"
            f"You can review and approve the request at the following link:\n{approval_url}\n\n"
            f"Kind regards,\n"
            f"HRMS System"
        )


        try:
            mail.send(msg)
            flash('Leave application submitted successfully.', 'success')
        except Exception as e:
            print(f"Email error: {e}")
            flash('Leave application sent, but failed to notify manager.', 'warning')

        return redirect(url_for('views.apply_leave'))

    return render_template('apply_leave.html', user=current_user, today=datetime.today().date().strftime("%d-%m-%y"))

@views.route('/all_leaves')
@login_required
def all_leaves():
    leaves = Leave.query.filter_by(approved=True).order_by(Leave.start_date.desc()).all()
    structured_leaves = []

    for leave in leaves:
        try:
            entries = json.loads(leave.leaves_data or "[]")
        except Exception:
            entries = []

        structured_leaves.append({
            "leave": leave,
            "entries": entries
        })

    return render_template("all_leaves.html", leaves=structured_leaves)

@views.route('/add_compoff', methods=['GET', 'POST'])
@login_required
def add_compoff():
    users = User.query.all()  # Retrieve all users from the database

    if request.method == 'POST':
        user_id = request.form['user_id']
        compoff_amount = float(request.form['compoff_amount'])

        # Find the user by ID
        user = User.query.get(user_id)
        if not user:
            flash("User not found.", category='error')
            return redirect(url_for('views.add_compoff'))

        # Find the user's attendance records
        user_attendances = Attendance.query.filter_by(user_id=user.id).all()

        if not user_attendances:
            flash("No attendance records found for the user.", category='error')
            return redirect(url_for('views.add_compoff'))

        # Add compoff to the first attendance record
        updated = False
        for attendance in user_attendances:
            attendance.compoff += compoff_amount
            db.session.commit()
            updated = True
            break

        if not updated:
            flash("No eligible attendance records found to add compoff.", category='error')
        else:
            flash(f'Compoff added successfully to attendance record for {user.email}.', category='success')

        return redirect(url_for('views.home'))

    return render_template('add_compoff.html', users=users)
@views.route('/approve_compoff/<int:request_id>', methods=['POST'])
@login_required
def approve_compoff(request_id):
    request_obj = CompOffRequest.query.get_or_404(request_id)
    submitter = request_obj.user

    if not has_approval_authority(current_user.role, submitter.role):
        flash("Not authorized to approve this request.", "error")
        return redirect(url_for('views.home'))

    request_obj.status = 'approved'
    request_obj.approved_by = current_user.email
    db.session.commit()

    send_email(
        subject="✅ Comp Off Approved",
        recipient=submitter.email,
        body=(
            f"Dear {submitter.first_name},\n\n"
            f"Your Comp Off request for {request_obj.attendance.date.strftime('%d-%m-%Y')} "
            f"({request_obj.value} day) has been approved.\n\n"
            f"Approved by: {current_user.first_name} ({current_user.email})\n\n"
            f"Regards,\nHR Team"
        )
    )

    flash("Comp Off approved and user notified.", "success")
    return redirect(url_for('views.pending_compoffs'))

@views.route('/reject_compoff/<int:request_id>', methods=['POST'])
@login_required
def reject_compoff(request_id):
    request_obj = CompOffRequest.query.get_or_404(request_id)
    submitter = request_obj.user

    if not has_approval_authority(current_user.role, submitter.role):
        flash("Not authorized to reject this request.", "error")
        return redirect(url_for('views.home'))

    remarks = request.form.get("remarks", "").strip()
    request_obj.status = 'rejected'
    request_obj.reason = remarks
    request_obj.approved_by = current_user.email
    db.session.commit()

    send_email(
        subject="❌ Comp Off Request Rejected",
        recipient=submitter.email,
        body=(
            f"Dear {submitter.first_name},\n\n"
            f"Your Comp Off request for the date {request_obj.attendance.date.strftime('%d-%m-%Y')} "
            f"({request_obj.value} day) has been rejected.\n\n"
            f"Remarks:\n{remarks or 'None'}\n\n"
            f"Rejected by: {current_user.first_name} ({current_user.email})\n"
            f"If you have questions, please contact your manager or HR.\n\n"
            f"Regards,\nHR Team"
        )
    )

    flash("Comp Off rejected and user notified.", "info")
    return redirect(url_for('views.pending_compoffs'))
@views.route('/pending_compoffs')
@login_required
def pending_compoffs():
    # Get all comp off requests (not just pending)
    all_requests = CompOffRequest.query.order_by(CompOffRequest.requested_on.desc()).all()

    approvable = []
    for req in all_requests:
        submitter = req.user
        if submitter and has_approval_authority(current_user.role, submitter.role):
            req.user = submitter
            req.compoff_status = req.status  # could be 'pending', 'approved', 'rejected'
            approvable.append(req)

    return render_template('pending_compoffs.html', records=approvable)


#########################################################################################################################################################
#Holiday Routes
#########################################################################################################################################################

@views.route('/holidays-category')
@login_required
def holidays_category():
    return render_template('holidays_category.html', user=current_user)



@views.route('/set_holidays', methods=['GET', 'POST'])
@login_required
def set_holidays():
    if request.method == 'POST':
        for i in range(20):
            name = request.form.get(f'holiday_name_{i}')
            date_str = request.form.get(f'holiday_date_{i}')

            if name and date_str:
                try:
                    # Convert string to date object
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    new_holiday = Holiday(name=name, date=date)
                    db.session.add(new_holiday)
                except ValueError:
                    # Handle invalid date formats if necessary
                    pass

        db.session.commit()
        return redirect(url_for('views.display_holidays'))

    return render_template('set_holidays.html')

@views.route('/display_holidays')
@login_required
def display_holidays():
    holidays = Holiday.query.all()
    return render_template('display_holidays.html', holidays=holidays)


@views.route('/delete_holiday/<int:holiday_id>', methods=['POST'])
@login_required
def delete_holiday(holiday_id):

    confirmation_id = request.form.get('confirmation_id')
    if confirmation_id != '24':
        flash('Incorrect confirmation ID', 'error')
        return redirect(url_for('views.list_holidays'))

    holiday = Holiday.query.get(holiday_id)
    if holiday:
        db.session.delete(holiday)
        db.session.commit()
        flash('Holiday deleted successfully', 'success')
    else:
        flash('Holiday not found', 'error')

    return redirect(url_for('views.display_holidays'))

@views.route('/subtract-holidays', methods=['GET'])
def show_subtract_holidays_form():
    users = User.query.all()  # Fetch all users
    user = current_user
    return render_template('subtract_holidays.html', users=users, user = user)

@views.route('/subtract-holidays', methods=['POST'])
def subtract_holidays():
    username = request.form.get('username')
    leave_type = request.form.get('leave_type')
    num_days = int(request.form.get('num_days'))

    user = User.query.get(username)  # Get the user by ID

    if leave_type == 'earned':
        if user.earned >= num_days:
            user.earned -= num_days
        else:
            flash('Not enough earned leave days.', category='error')
    elif leave_type == 'medic':
        if user.medic >= num_days:
            user.medic -= num_days
        else:
            flash('Not enough medic leave days.', category='error')
    elif leave_type == 'pay':
        if user.pay >= num_days:
            user.pay -= num_days
        else:
            flash('Not enough pay leave days.', category='error')
    else:
        flash('Invalid leave type.', category='error')
        return redirect(url_for('views.show_subtract_holidays_form'))

    db.session.commit()
    flash('Leave days edited successfully.', category='success')
    return redirect(url_for('views.show_subtract_holidays_form'))

@views.route('/hol')
@login_required
def holiday_saturdays():

    india_tz = pytz.timezone('Asia/Kolkata')
    today = datetime.now(india_tz).date()
    
    # Determine financial year range
    if today.month >= 4:
        start_year = today.year
        end_year = today.year + 1
    else:
        start_year = today.year - 1
        end_year = today.year

    start_date = date(start_year, 4, 1)
    end_date = date(end_year, 3, 31)

    # Helper to find 2nd and 4th Saturdays in a given month
    def second_and_fourth_saturdays(year, month):
        saturdays = []
        for day in range(1, 32):
            try:
                dt = date(year, month, day)
            except ValueError:
                break
            if dt.weekday() == 5:  # Saturday
                saturdays.append(dt)
        return [saturdays[1], saturdays[3]] if len(saturdays) >= 4 else []

    # Loop through each month and collect dates
    holiday_saturdays = []
    for year in [start_year, end_year] if start_date.year != end_date.year else [start_year]:
        for month in range(1, 13):
            current = date(year, month, 1)
            if start_date <= current <= end_date:
                holiday_saturdays.extend(second_and_fourth_saturdays(year, month))

    holiday_saturdays = [d for d in holiday_saturdays if start_date <= d <= end_date]
    holiday_saturdays.sort()

    return render_template('holiday_saturdays.html', saturdays=holiday_saturdays, start=start_date, end=end_date)

#########################################################################################################################################################
#Announcement Routes
#########################################################################################################################################################
@views.route('/announcements-category')
@login_required
def announcements_category():
    return render_template('announcements_category.html', user=current_user)

@views.route('/announcements')
@login_required
def announcements():
    # Only show announcements sent to the current user
    announcements = Announcement.query\
        .join(announcement_user)\
        .filter(announcement_user.c.user_id == current_user.id)\
        .order_by(Announcement.date_posted.desc())\
        .all()

    return render_template('announcements.html', announcements=announcements)


# @views.route('/post_announcement', methods=['GET', 'POST'])
# @login_required
# def post_announcement():
#     if request.method == 'POST':
#         title = request.form.get('title')
#         content = request.form.get('content')
#         file = request.files.get('attachments')   # Image
#         file1 = request.files.get('attachments1') # Document
#         recipient_ids = request.form.getlist('recipients')  # List of selected user IDs
#         # recipient_ids.append(current_user.id)
#         # Save image file
#         image_url = None
#         if file and file.filename != '':
#             filename = secure_filename(file.filename)
#             file_path = os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename)
#             os.makedirs(os.path.dirname(file_path), exist_ok=True)
#             file.save(file_path)
#             image_url = f'website/uploads/photos/{filename}'

#         # Save document file
#         file = request.files.get('document')
#         if file and file.filename != '':
#             filename = secure_filename(file.filename)
#             public_url = upload_file_to_gcs(file, filename)
#             announcement.doc_url = public_url  # save this to DB


#         # Create the announcement object once
#         announcement = Announcement(title=title, content=content, image_url=image_url)
#         db.session.add(announcement)

#         # Associate selected users and send emails
#         for user_id in recipient_ids:
#             user = User.query.get(int(user_id))
#             if user:
#                 announcement.recipients.append(user)  # Associate recipient
#                 if user.email:
#                     msg = Message(
#                         subject='New Announcement Posted',
#                         sender=current_app.config['MAIL_DEFAULT_SENDER'],
#                         recipients=[user.email]
#                     )
#                     announcement_link = url_for('views.announcements', _external=True)
#                     msg.body = (
#                         f"Dear {user.first_name},\n\n"
#                         f"A new announcement has been posted on the portal.\n"
#                         f"Please log in to view the details.\n\n"
#                         f"View Announcements: {announcement_link}\n\n"
#                         f"Regards,\n"
#                         f"HR Team"
#                     )

#                     mail.send(msg)

#         # Commit after all changes
#         db.session.commit()

#         flash('Announcement posted successfully and notifications sent to selected users!', 'success')
#         return redirect(url_for('views.announcements'))

#     # GET request
#     users = User.query.order_by(User.first_name.asc()).all()
#     return render_template('post_announcement.html', users=users)


from google.cloud import storage

def upload_file_to_gcs(file, filename, subfolder=None, bucket_name='hrms-bucket'):
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    blob_path = f'{subfolder}/{filename}' if subfolder else filename
    blob = bucket.blob(blob_path)

    blob.upload_from_file(file, content_type=file.content_type)

    # Do NOT call blob.make_public() when using Uniform Bucket-Level Access
    return f"https://storage.googleapis.com/{bucket_name}/{blob_path}"


# @views.route('/post_announcement', methods=['GET', 'POST'])
# @login_required
# def post_announcement():
#     if request.method == 'POST':
#         title = request.form.get('title')
#         content = request.form.get('content')
#         recipient_ids = request.form.getlist('recipients')

#         image_url = None
#         doc_url = None

#         # Handle image upload to GCS
#         image_file = request.files.get('attachments')
#         if image_file and image_file.filename != '':
#             image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
#             image_url = upload_file_to_gcs(image_file, image_filename, subfolder='uploads/photos')

#         # Handle document upload to GCS
#         doc_file = request.files.get('attachments1') or request.files.get('document')
#         if doc_file and doc_file.filename != '':
#             doc_filename = f"{uuid.uuid4().hex}_{secure_filename(doc_file.filename)}"
#             doc_url = upload_file_to_gcs(doc_file, doc_filename, subfolder='uploads/docs')

#         # Create the announcement
#         announcement = Announcement(
#             title=title,
#             content=content,
#             image_url=image_url,
#             doc_url=doc_url
#         )
#         db.session.add(announcement)

#         # Associate recipients and send emails
#         for user_id in recipient_ids:
#             user = User.query.get(int(user_id))
#             if user:
#                 announcement.recipients.append(user)
#                 if user.email:
#                     try:
#                         msg = Message(
#                             subject='New Announcement Posted',
#                             sender=current_app.config['MAIL_DEFAULT_SENDER'],
#                             recipients=[user.email]
#                         )
#                         announcement_link = url_for('views.announcements', _external=True)
#                         msg.body = (
#                             f"Dear {user.first_name},\n\n"
#                             f"A new announcement has been posted on the portal.\n"
#                             f"Please log in to view the details.\n\n"
#                             f"View Announcements: {announcement_link}\n\n"
#                             f"Regards,\n"
#                             f"HR Team"
#                         )
#                         mail.send(msg)
#                     except Exception as e:
#                         # You can log the problematic email or store it for admin review
#                         print(f"[!] Failed to send to {user.email}: {str(e)}")


#         db.session.commit()

#         flash('Announcement posted successfully and notifications sent to selected users!', 'success')
#         return redirect(url_for('views.announcements'))

#     # GET request
#     users = User.query.order_by(User.first_name.asc()).all()
#     return render_template('post_announcement.html', users=users)
# @views.route('/post_announcement', methods=['GET', 'POST'])
# @login_required
# def post_announcement():
#     if request.method == 'POST':
#         title = request.form.get('title')
#         content = request.form.get('content')
#         recipient_ids = request.form.getlist('recipients')

#         image_url = None
#         doc_url = None

#         # Handle image upload to GCS
#         image_file = request.files.get('attachments')
#         if image_file and image_file.filename != '':
#             image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
#             image_url = upload_file_to_gcs(image_file, image_filename, subfolder='uploads/photos')

#         # Handle document upload to GCS
#         doc_file = request.files.get('attachments1') or request.files.get('document')
#         if doc_file and doc_file.filename != '':
#             doc_filename = f"{uuid.uuid4().hex}_{secure_filename(doc_file.filename)}"
#             doc_url = upload_file_to_gcs(doc_file, doc_filename, subfolder='uploads/docs')

#         # Create the announcement
#         announcement = Announcement(
#             title=title,
#             content=content,
#             image_url=image_url,
#             doc_url=doc_url
#         )
#         db.session.add(announcement)
#         db.session.flush()  # Flush to get announcement.id if needed before sending mail

#         # Email batching
#         import time
#         batch_size = 3
#         failed_emails = []

#         for i in range(0, len(recipient_ids), batch_size):
#             batch = recipient_ids[i:i + batch_size]
#             for user_id in batch:
#                 user = User.query.get(int(user_id))
#                 if user:
#                     announcement.recipients.append(user)
#                     if user.email:
#                         try:
#                             msg = Message(
#                                 subject='New Announcement Posted',
#                                 sender=current_app.config['MAIL_DEFAULT_SENDER'],
#                                 recipients=[user.email]
#                             )
#                             announcement_link = url_for('views.announcements', _external=True)
#                             msg.body = (
#                                 f"Dear {user.first_name},\n\n"
#                                 f"A new announcement has been posted on the portal.\n"
#                                 f"Please log in to view the details.\n\n"
#                                 f"View Announcements: {announcement_link}\n\n"
#                                 f"Regards,\n"
#                                 f"HR Team"
#                             )
#                             mail.send(msg)
#                         except Exception as e:
#                             failed_emails.append((user.email, str(e)))
#                             print(f"[!] Failed to send to {user.email}: {e}")
#             time.sleep(1)  # Sleep after each batch

#         db.session.commit()

#         if failed_emails:
#             flash(f"Announcement posted, but failed to send email to {len(failed_emails)} users. Check logs.", 'warning')
#         else:
#             flash('Announcement posted successfully and notifications sent to selected users!', 'success')

#         return redirect(url_for('views.announcements'))

#     # GET request
#     users = User.query.order_by(User.first_name.asc()).all()
#     return render_template('post_announcement.html', users=users)

@views.route('/post_announcement', methods=['GET', 'POST'])
@login_required
def post_announcement():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        recipient_ids = request.form.getlist('recipients')

        image_url = None
        doc_url = None

        # Handle image upload to GCS
        image_file = request.files.get('attachments')
        if image_file and image_file.filename != '':
            image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_url = upload_file_to_gcs(image_file, image_filename, subfolder='uploads/photos')

        # Handle document upload to GCS
        doc_file = request.files.get('attachments1') or request.files.get('document')
        if doc_file and doc_file.filename != '':
            doc_filename = f"{uuid.uuid4().hex}_{secure_filename(doc_file.filename)}"
            doc_url = upload_file_to_gcs(doc_file, doc_filename, subfolder='uploads/docs')

        # Create the announcement
        announcement = Announcement(
            title=title,
            content=content,
            image_url=image_url,
            doc_url=doc_url
        )
        db.session.add(announcement)

        # Collect valid emails and associate recipients
        valid_emails = []
        for user_id in recipient_ids:
            user = User.query.get(int(user_id))
            if user:
                announcement.recipients.append(user)
                if user.email:
                    valid_emails.append(user.email)

        # Send one BCC email if there are valid emails
        if valid_emails:
            try:
                msg = Message(
                    subject='New Announcement Posted',
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[current_app.config['MAIL_DEFAULT_SENDER']],  # main recipient to satisfy SMTP
                    bcc=valid_emails
                )
                announcement_link = url_for('views.announcements', _external=True)
                msg.body = (
                    f"Dear All,\n\n"
                    f"A new announcement has been posted on the portal.\n\n"
                    f"Title: {title}\n\n"
                    f"{content}\n\n"
                    f"View Announcements: {announcement_link}\n\n"
                    f"Regards,\n"
                    f"HR Team"
                )
                mail.send(msg)
            except Exception as e:
                print(f"[!] Failed to send announcement email: {str(e)}")

        db.session.commit()
        flash('Announcement posted successfully and notifications sent to selected users!', 'success')
        return redirect(url_for('views.announcements'))

    # GET request
    users = User.query.order_by(User.first_name.asc()).all()
    return render_template('post_announcement.html', users=users)



@views.route('/delete_announcement/<int:announcement_id>', methods=['POST'])
@login_required
def delete_announcement(announcement_id):
    confirmation_id = request.form.get('confirmation_id')
    if (current_user.email == "sumana@nadiya.in" or current_user.email == "maneesh@nadiya.in") and confirmation_id == '24':


        announcement = Announcement.query.get(announcement_id)
        if announcement:
            db.session.delete(announcement)
            db.session.commit()
            flash('Announcement deleted successfully', 'success')
        else:
            flash('Announcement not found', 'danger')
    else:
        flash('Invalid confirmation ID or insufficient permissions', 'danger')
    return redirect(url_for('views.announcements'))

@views.route('/acknowledge/<int:announcement_id>', methods=['POST'])
@login_required
def acknowledge_announcement(announcement_id):
    existing = AnnouncementAcknowledgment.query.filter_by(
        user_id=current_user.id,
        announcement_id=announcement_id
    ).first()
    if not existing:
        ack = AnnouncementAcknowledgment(
            user_id=current_user.id,
            announcement_id=announcement_id
        )
        db.session.add(ack)
        db.session.commit()
        flash('Acknowledged successfully.', 'success')
    else:
        flash('You have already acknowledged this announcement.', 'info')
    return redirect(url_for('views.announcements'))

@views.route('/announcement-read-status/<int:announcement_id>')
@login_required
def read_status(announcement_id):
    if current_user.email not in ["sumana@nadiya.in", "maneesh@nadiya.in", "support@nadiya.in"]:
        flash("Access denied.", "danger")
        return redirect(url_for('views.announcements'))

    announcement = Announcement.query.get_or_404(announcement_id)
    recipients = announcement.recipients  # Only users the announcement was sent to
    acknowledgments = {ack.user_id for ack in announcement.acknowledgments}

    read_users = [user for user in recipients if user.id in acknowledgments]
    unread_users = [user for user in recipients if user.id not in acknowledgments]

    return render_template("acknowledgment_status.html",
                           announcement=announcement,
                           read_users=read_users,
                           unread_users=unread_users)

#########################################################################################################################################################
#Profile Routes
#########################################################################################################################################################

photos = UploadSet('photos', IMAGES)
docs = UploadSet('docs', ('pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'))

# @views.route('/profile/<int:user_id>', methods=['GET', 'POST'])
# @login_required
# def profile(user_id):
#     user = User.query.get(user_id)
#     if not user:
#         flash("User not found.", category='error')
#         return redirect(url_for('index'))

#     if request.method == 'POST':
#         if 'photo' in request.files and request.files['photo']:
#             filename = photos.save(request.files['photo'])
#             user.photo = filename

#         if 'document' in request.files and request.files['document']:
#             file = request.files['document']
#             if file:
#                 filename = docs.save(file)
#                 document_type = request.form.get('document_type')  # Assuming document type is selected in form
#                 if user.documents:
#                     # Delete the old document file if it exists
#                     for doc in user.documents:
#                         if doc.document_type == document_type:
#                             doc.filename = filename
#                             break
#                     else:
#                         new_document = Document(user_id=user.id, filename=filename, document_type=document_type)
#                         user.documents.append(new_document)
#                         db.session.add(new_document)
#                 else:
#                     new_document = Document(user_id=user.id, filename=filename, document_type=document_type)
#                     user.documents.append(new_document)
#                     db.session.add(new_document)

#         db.session.commit()
#         flash('Profile updated successfully')
#         return redirect(url_for('views.profile', user_id=user_id))

#     return render_template('profile.html', user=user)

# @views.route('/upload', methods=['POST', 'GET'])
# @login_required

# def upload():
#     if request.method == 'POST':
#         user_id = request.form.get('user_id')
#         try:
#             if 'document' in request.files:
#                 filename = docs.save(request.files['document'])
#                 flash('Document uploaded successfully.', 'success')
#             else:
#                 flash('No document selected for upload.', 'warning')
#         except UploadNotAllowed:
#             flash('Upload not allowed. Please check the file type.', 'error')

#         return redirect(url_for('views.profile', user_id=user_id))

#     elif request.method == 'GET':
#         setname = request.args.get('setname')
#         filename = request.args.get('filename')
#         if setname and filename:
#             return redirect(url_for('uploaded_file', setname=setname, filename=filename))
#         else:
#             return "Bad Request", 400

#     return "Method not allowed", 405

@views.route('/create_user', methods=['GET', 'POST'])
@login_required

def create_user():
    if current_user.email in ["sumana@nadiya.in", "maneesh@nadiya.in"]:
        users = User.query.all()
        return render_template('create_user.html', users=users)
    return redirect(url_for('views.home'))

# @views.route('/uploaded_file/<setname>/<filename>')
# @login_required
# def uploaded_file(setname, filename):
#     if setname == 'photos':
#         file_path = os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename)
#         print(f"Serving photo from: {file_path}")
#         if not os.path.exists(file_path):
#             print("File not found:", file_path)
#             return abort(404)  # Return 404 Not Found if the file does not exist
#         return send_from_directory(current_app.config['UPLOADED_PHOTOS_DEST'], filename)
#     elif setname == 'docs':
#         file_path = os.path.join(current_app.config['UPLOADED_DOCS_DEST'], filename)
#         print(f"Serving doc from: {file_path}")
#         if not os.path.exists(file_path):
#             print("File not found:", file_path)
#             return abort(404)  # Return 404 Not Found if the file does not exist
#         return send_from_directory(current_app.config['UPLOADED_DOCS_DEST'], filename)
#     else:
#         return "File type not supported", 400
# @views.route('/profile/<int:user_id>', methods=['GET', 'POST'])
# @login_required
# def profile(user_id):
#     user = User.query.get(user_id)
#     if not user:
#         flash("User not found.", category='error')
#         return redirect(url_for('index'))

#     if request.method == 'POST':
#         if 'photo' in request.files and request.files['photo']:
#             file = request.files['photo']
#             filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
#             photo_url = upload_file_to_gcs(file, filename, subfolder='uploads/photos')
#             user.photo = photo_url

#         if 'document' in request.files and request.files['document']:
#             file = request.files['document']
#             document_type = request.form.get('document_type')
#             if not document_type:
#                 flash('Please select a document type when uploading a document.', category='error')
#                 return redirect(url_for('views.profile', user_id=user_id))
#             filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
#             doc_url = upload_file_to_gcs(file,filename, subfolder='uploads/docs')

#             if user.documents:
#                 for doc in user.documents:
#                     if doc.document_type == document_type:
#                         doc.filename = doc_url
#                         break
#                 else:
#                     new_document = Document(user_id=user.id, filename=doc_url, document_type=document_type)
#                     user.documents.append(new_document)
#                     db.session.add(new_document)
#             else:
#                 new_document = Document(user_id=user.id, filename=doc_url, document_type=document_type)
#                 user.documents.append(new_document)
#                 db.session.add(new_document)
#             # Determine immediate reporting managers
#         role = user.role
#         manager_roles = ROLES_HIERARCHY.get(role, [])
#         reporting_managers = User.query.filter(User.role.in_(manager_roles)).all()


#         db.session.commit()
#         flash('Profile updated successfully')
#         return redirect(url_for('views.profile', user_id=user_id, reporting_managers=reporting_managers))

#     return render_template('profile.html', user=user)
@views.route('/profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def profile(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", category='error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'photo' in request.files and request.files['photo']:
            file = request.files['photo']
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            photo_url = upload_file_to_gcs(file, filename, subfolder='uploads/photos')
            user.photo = photo_url

        if 'document' in request.files and request.files['document']:
            file = request.files['document']
            document_type = request.form.get('document_type')
            if not document_type:
                flash('Please select a document type when uploading a document.', category='error')
                return redirect(url_for('views.profile', user_id=user_id))
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            doc_url = upload_file_to_gcs(file, filename, subfolder='uploads/docs')

            if user.documents:
                for doc in user.documents:
                    if doc.document_type == document_type:
                        doc.filename = doc_url
                        break
                else:
                    new_document = Document(user_id=user.id, filename=doc_url, document_type=document_type)
                    user.documents.append(new_document)
                    db.session.add(new_document)
            else:
                new_document = Document(user_id=user.id, filename=doc_url, document_type=document_type)
                user.documents.append(new_document)
                db.session.add(new_document)

        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('views.profile', user_id=user_id))

    # This happens on both GET and after redirect
    # role = user.role
    # manager_roles = ROLES_HIERARCHY.get(role, [])
    # reporting_managers = User.query.filter(User.role.in_(manager_roles)).all()

    role = user.role
    manager_roles = ROLES_HIERARCHY.get(role, [])
    reporting_manager = None

    for mgr_role in manager_roles:
        manager = User.query.filter_by(role=mgr_role).first()
        if manager:
            reporting_manager = manager
            break

    return render_template('profile.html', user=user, reporting_manager=reporting_manager)


@views.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        try:
            if 'document' in request.files:
                file = request.files['document']
                doc_url = upload_file_to_gcs(file, subfolder='upload/docs')
                flash('Document uploaded successfully.', 'success')
            else:
                flash('No document selected for upload.', 'warning')
        except UploadNotAllowed:
            flash('Upload not allowed. Please check the file type.', 'error')

        return redirect(url_for('views.profile', user_id=user_id))

    elif request.method == 'GET':
        return "This endpoint is for uploading only.", 405

    return "Method not allowed", 405

    
#########################################################################################################################################################
#Miscellaneous Routes
#########################################################################################################################################################
@views.route('/misc-category')
@login_required
def misc_category():
    if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
        flash("You do not have permission to view this page.", category='error')
        return redirect(url_for('views.home'))
    return render_template('misc_category.html', user=current_user)


@views.route('/all', methods=['GET'])
def all():
    try:
        user = User.query.all()
        role = [user.role for user in User.query.all()]
        emails = [user.email for user in User.query.all()]  # Fetch all emails from the database
        return render_template('all.html', emails=emails, user = user, role = role)
    except Exception as e:
        return str(e)

# @views.route('/display_compoff', methods=['GET'])
# @login_required
# def display_compoff():
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in'and current_user.email!='support@nadiya.in' and current_user.email!="accounts@nadiya.in":
#         flash("You do not have permission to view this page.", category='error')
#         return redirect(url_for('views.home'))

#     # Fetch all users with their total_compoff
#     users = User.query.all()
#     user_compoffs = [{'name': f'{user.first_name}', 'total_compoff': user.total_compoff} for user in users]

#     return render_template('display_compoff.html', user_compoffs=user_compoffs)
from sqlalchemy import func

@views.route('/display_compoff', methods=['GET'])
@login_required
def display_compoff():
    if current_user.email not in [
        "sumana@nadiya.in",
        "maneesh@nadiya.in",
        "support@nadiya.in",
        "accounts@nadiya.in"
    ]:
        flash("You do not have permission to view this page.", category='error')
        return redirect(url_for('views.home'))

    # Fetch total comp offs from approved and unused requests, grouped by user
    from .models import db, CompOffRequest, User

    compoff_totals = (
        db.session.query(
            CompOffRequest.user_id,
            func.sum(CompOffRequest.value).label('total')
        )
        .filter(CompOffRequest.status == 'approved', CompOffRequest.used == False)
        .group_by(CompOffRequest.user_id)
        .all()
    )

    # Convert to dict for easier lookup
    totals_dict = {user_id: total for user_id, total in compoff_totals}

    # Fetch all users and build the list
    users = User.query.all()
    user_compoffs = [
        {
            'name': user.first_name,
            'total': round(totals_dict.get(user.id, 0), 2)
        }
        for user in users
    ]

    return render_template('display_compoff.html', user_compoffs=user_compoffs)

@views.route('/assign_roles', methods=['GET', 'POST'])
@login_required
def assign_roles():
    if current_user.email not in ['sumana@nadiya.in', 'maneesh@nadiya.in']:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('views.home'))

    if request.method == 'POST':
        user_id = request.form['user_id']
        role = request.form['role']
        is_probation = request.form.get('probation') == 'on'
        nad_id = request.form.get('nad_id') or None

        user = User.query.get(user_id)
        if user:
            previously_probation = user.probation
            user.role = role
            user.nad_id = nad_id
            user.set_probation_status(is_probation)

            if previously_probation and not is_probation:
                # Probation just ended, check if 6 months have passed
                if user.joining_date and datetime.today() >= user.joining_date + relativedelta(months=6):
                    
                    user.earned = 0
                    user.medic = 0
                    user.pay = 0
            db.session.commit()
            flash(f'Role {role} assigned to {user.first_name}.', 'success')
        else:
            flash('User not found.', 'error')
        return redirect(url_for('views.assign_roles'))

    users = User.query.all()
    return render_template('assign_roles.html', users=users)

@views.route('/delete/<email>', methods=['DELETE'])
def delete_email(email):
    user = User.query.filter_by(email=email).first()

    if user:
        # Delete related records in other tables
        try:
            User.query.filter_by(user_id=user.id).delete()
            Document.query.filter_by(user_id=user.id).delete()
            Attendance.query.filter_by(user_id=user.id).delete()
            Leave.query.filter_by(user_id=user.id).delete()
            Holiday.query.filter_by(user_id=user.id).delete()

            # Delete the user itself

            db.session.commit()

            return jsonify({'message': f'User {email} and related records deleted successfully'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': f'User with email {email} not found'}), 404

@views.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    print(f"Attempting to delete user with ID: {user_id}")

    user = User.query.get_or_404(user_id)
    print(f"Found user: {user}")

    Document.query.filter_by(user_id=user_id).delete()
    Attendance.query.filter_by(user_id=user_id).delete()
    Leave.query.filter_by(user_id=user_id).delete()


    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('views.all'))

@views.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

            # Generate a password reset token
        if user:
            # Generate a password reset token
            reset_token = str(uuid.uuid4())
            user.reset_token = reset_token
            db.session.commit()

       
            # Send reset email
            reset_link = url_for('views.reset_password', token=reset_token, _external=True)
            msg = Message('Password Reset Request', recipients=[email])
            msg.body = (
                        f"Dear {user.first_name},\n\n"
                        f"We received a request to reset your password. Please use the link below to proceed:\n\n"
                        f"{reset_link}\n\n"
                        f"Note: This link will expire in 1 hour for security purposes.\n\n"
                        f"If you did not request this, please ignore this email or contact support.\n\n"
                        f"Best regards,\n"
                        f"HR Team"
                    )

            try:
                mail.send(msg)
                flash('Password reset link sent to your email.', 'success')
            except Exception as e:
                flash('Failed to send reset email. Please try again.', 'error')
        else:
            flash('No account found with that email address.', 'error')

        return redirect(url_for('views.forgot_password'))

    return render_template('forgot_password.html')

@views.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
            
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('reset_password.html', token=token)
            
        user.password = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash('Your password has been updated successfully!', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)

# @views.route('/export', methods=['POST', 'GET'])
# @login_required
# def export_all_data():
#     output = BytesIO()

#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         tables = {
#             'Users': User,
#             'Documents': Document,
#             'Attendance': Attendance,
#             'Leaves': Leave,
#             'Holidays': Holiday,
#             'Announcements': Announcement
#         }

#         for sheet_name, model in tables.items():
#             query = model.query.all()
#             data = [item.__dict__.copy() for item in query]
#             for row in data:
#                 row.pop('_sa_instance_state', None)
#             df = pd.DataFrame(data)
#             df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

#     output.seek(0)

#     # Send the email
#     msg = Message(subject="HRMS System Backup",
#                   recipients=["sumana@nadiya.in", "maneesh@nadiya.in","support@nadiya.in"])  
#     msg.body = (
#             f"Hello,\n\n"
#             f"Attached is the latest backup of all system tables taken prior to the reset.\n"
#             f"Please retain this copy for your reference or restoration if required.\n\n"
#             f"Best regards,\n"
#             f"HR Team"
#         )

#     msg.attach("all_data_export.xlsx", 
#                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                output.read())

#     try:
#         mail.send(msg)
#         flash("Exported data and emailed backup successfully.", "success")
#     except Exception as e:
#         flash(f"Exported data, but failed to send email: {str(e)}", "warning")

#     # Reset pointer to allow browser download too (optional)
#     output.seek(0)
#     return send_file(
#         output,
#         as_attachment=True,
#         download_name="all_data_export.xlsx",
#         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
from .export_utils import export_all_data  # if you renamed it
@views.route('/export', methods=['GET', 'POST'])
@login_required
def export_route():
    return export_all_data()

#########################################################################################################################################################
#functions
#########################################################################################################################################################

def calculate_leaves_for_user(user):
   
    if user.probation:
        user.earned = 0
        user.medic = 0
        user.pay = 10 
    else:
        user.earned = 15 
        user.medic = 6 
        user.pay = 10 

    db.session.commit()

def has_approval_authority(approver_role, submitter_role):
    allowed_roles = ROLES_HIERARCHY.get(submitter_role, [])
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    return approver_role in allowed_roles

def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)
    
@views.route('/attendance_table_mgr')
@login_required
def attendance_table_mgr():
    if current_user.role not in ROLES_HIERARCHY:  # assuming 'role' is a field on your User model
        flash("You do not have managerial access.", category='error')
        return redirect(url_for('views.home'))

    date_str = request.args.get('date')
    india_tz = pytz.timezone('Asia/Kolkata')
    today = datetime.now(india_tz).date()

    # Determine the date to fetch
    if not date_str:
        latest_entry = Attendance.query.order_by(Attendance.date.desc()).first()
        target_date = latest_entry.date if latest_entry else today
    else:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    # Filter users who are reportees
    reportee_users = [
        user.id for user in User.query.all()
        if has_approval_authority(current_user.role, user.role)
    ]

    # Get attendance records for those users
    attendances = (
        Attendance.query
        .filter(Attendance.date == target_date, Attendance.user_id.in_(reportee_users))
        .order_by(desc(Attendance.entry_time))
        .all()
    )

    # Next and previous dates with entries for reportees
    next_date = (
        Attendance.query
        .filter(Attendance.date > target_date, Attendance.user_id.in_(reportee_users))
        .order_by(Attendance.date.asc())
        .first()
    )

    prev_date = (
        Attendance.query
        .filter(Attendance.date < target_date, Attendance.user_id.in_(reportee_users))
        .order_by(Attendance.date.desc())
        .first()
    )

    return render_template(
        'attendance_table_mgr.html',
        attendances=attendances,
        target_date=target_date,
        prev_date=prev_date.date if prev_date else None,
        next_date=next_date.date if next_date else None
    )

@views.route('/exit_report/<int:attendance_id>', methods=['GET', 'POST'])
@login_required
def exit_report_form(attendance_id):
    attendance = Attendance.query.get_or_404(attendance_id)

    if attendance.user_id != current_user.id:
        flash("You are not authorized to access this exit report.", "error")
        return redirect(url_for('views.home'))
    if request.method == 'POST':
        start_times = request.form.getlist('start_time')
        end_times = request.form.getlist('end_time')
        activities = request.form.getlist('activities_completed')
        plans = request.form.getlist('tomorrow_plan')

        # Optional fields
        site_names = request.form.getlist('site_name') or []
        customer_names = request.form.getlist('customer_name') or []
        remarks_list = request.form.getlist('remarks') or []

        if not any(start_times):
            flash("You must submit at least one completed row.", "warning")
            return redirect(request.url)

        saved_any = False
        row_count = len(start_times)

        for i in range(row_count):
            start = start_times[i].strip()
            end = end_times[i].strip()
            activity = activities[i].strip()
            plan = plans[i].strip()

            # Optional fields
            site = site_names[i].strip() if i < len(site_names) else ''
            customer = customer_names[i].strip() if i < len(customer_names) else ''
            remarks = remarks_list[i].strip() if i < len(remarks_list) else ''

            if i == 0:
                # Row 1: all required fields must be filled
                if not start or not end or not activity or not plan:
                    flash("Row 1 must be completely filled.", "warning")
                    return redirect(request.url)
            else:
                # Row 2+: skip if ALL fields are empty
                if not start and not end and not activity and not plan and not site and not customer and not remarks:
                    continue  # skip empty row

            # Try parsing time only if provided
            try:
                start_time = datetime.strptime(start, "%H:%M").time() if start else None
                end_time = datetime.strptime(end, "%H:%M").time() if end else None
            except ValueError:
                continue  # skip this row if time is invalid

            report = ExitReport(
                user_id=current_user.id,
                attendance_id=attendance.id,
                site_name=site,
                customer_name=customer,
                start_time=start_time,
                end_time=end_time,
                activities_completed=activity,
                tomorrow_plan=plan,
                remarks=remarks
            )
            db.session.add(report)
            saved_any = True


        if not saved_any:
            flash("Please submit at least one valid row.", "warning")
            return redirect(request.url)

        # ✅ Mark Exit in Attendance now
        # now = datetime.now(pytz.timezone('Asia/Kolkata'))
        # latitude = request.form.get('latitude')
        # longitude = request.form.get('longitude')

        # try:
        #     location_obj = geoLoc.reverse(f"{latitude}, {longitude}")
        #     exit_location = location_obj.address if location_obj else "Unknown"
        # except Exception as e:
        #     print(f"Geo error on exit: {e}")
        #     exit_location = "Unknown"

        # attendance.exit_time = now.time().replace(microsecond=0)
        # attendance.exit_location = exit_location
        # attendance.calculate_comp_off()
        attendance.exit_report_submitted = True

        try:
            db.session.commit()
            flash("Exit report saved. But attendance is still active — make sure to do a proper exit to complete it.", "warning")
        except Exception as e:
            db.session.rollback()
            print("Exit report error:", e)
            flash("Error saving report. Please try again.", "error")

        return redirect(url_for('views.attendance_form'))


    return render_template('exit_report.html', attendance=attendance)

@views.route('/exit_reports_summary')
@login_required
def exit_reports_summary():
    # Ensure the user has authority over *at least one other role*
    visible_users = [
        user for user in User.query.all()
        if has_approval_authority(current_user.role, user.role) 
    ]

    if not visible_users: 
        flash("You do not have permission to view this page.", "error")
        return redirect(url_for('views.home'))

    # Collect reports from only users the approver can view
    summary_data = (
        db.session.query(User, ExitReport)
        .join(ExitReport, User.id == ExitReport.user_id)
        .filter(User.id.in_([u.id for u in visible_users]))
        .order_by(ExitReport.attendance_id.desc())
        .all()
    )

    # Group reports by user
    user_reports = {}
    for user, report in summary_data:
        user_reports.setdefault(user, []).append(report)

    return render_template('exit_reports_summary.html', user_reports=user_reports)

# @views.route('/exit_report_view/<int:user_id>/<date>')
# @login_required
# def exit_report_view(user_id, date):
#     from datetime import datetime

#     user = User.query.get_or_404(user_id)
#     parsed_date = datetime.strptime(date, '%Y-%m-%d').date()

#     # Ensure the current user has authority to view the selected user's reports
#     # if user.id != current_user.id and not has_approval_authority(current_user.role, user.role) and not current_user.email == "sumana@nadiya.in":
#     #     flash("You do not have permission to view this report.", "error")
#     #     return redirect(url_for('views.home'))

#     # Get attendance record
#     attendance = Attendance.query.filter_by(user_id=user_id, date=date).all()

#     # No attendance, no report
#     if not attendance:
#         flash("No attendance found for the selected date.", "warning")
#         return redirect(url_for('views.home'))

#     # Get exit reports tied to that attendance
#     reports = ExitReport.query.filter_by(attendance_id=attendance.id).order_by(ExitReport.start_time).all()

#     return render_template(
#         'exit_reports_view.html',
#         user=user,
#         date=parsed_date,
#         attendance=attendance,
#         reports=reports
#     )
@views.route('/exit_report_view/<int:user_id>/<date>')
@login_required
def exit_report_view(user_id, date):
    from datetime import datetime

    user = User.query.get_or_404(user_id)
    parsed_date = datetime.strptime(date, '%Y-%m-%d').date()

    # Uncomment this if you want role-based access enforcement
    # if user.id != current_user.id and not has_approval_authority(current_user.role, user.role) and current_user.email != "sumana@nadiya.in":
    #     flash("You do not have permission to view this report.", "error")
    #     return redirect(url_for('views.home'))

    # Get all attendance records for that user on that date
    attendances = Attendance.query.filter_by(user_id=user_id, date=parsed_date).all()

    if not attendances:
        flash("No attendance found for the selected date.", "warning")
        return redirect(url_for('views.home'))

    # Get all exit reports related to any of those attendance records
    attendance_ids = [a.id for a in attendances]
    reports = ExitReport.query.filter(ExitReport.attendance_id.in_(attendance_ids)).order_by(ExitReport.start_time).all()

    return render_template(
        'exit_reports_view.html',
        user=user,
        date=parsed_date,
        attendance=attendances,
        reports=reports
    )

@views.route('/manual_attendance', methods=['GET', 'POST'])
@login_required
def manual_attendance():
    if current_user.email not in ['sumana@nadiya.in', 'maneesh@nadiya.in']:
        flash("Access denied: Admin access only.", "danger")
        return redirect(url_for('views.home'))
    if request.method == 'POST':
        user_id = request.form.get('user_id') or current_user.id
        entry_time = request.form.get('entry_time')
        exit_time = request.form.get('exit_time')
        date = request.form.get('date')
        site_name_e = request.form.get('site_name_e')
        site_name = request.form.get('site_name')
        reason = request.form.get('reason', '')
        hol = request.form.get('holiday')

        try:
            entry_time = datetime.strptime(entry_time, "%H:%M").time()
            exit_time = datetime.strptime(exit_time, "%H:%M").time()
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()

            selected_user = User.query.get(int(user_id))
            if not selected_user:
                flash("User not found.", "error")
                return redirect(url_for('views.manual_attendance'))

            attendance = Attendance(
                user_id=selected_user.id,
                name=selected_user.first_name,
                entry_time=entry_time,
                exit_time=exit_time,
                date=date_obj,
                day=date_obj.strftime('%A'),
                site_name=site_name,
                site_name_e=site_name_e,
                reason=reason,
                hol=10000 if hol == 'on' else 0,
                entry_location="Manual Entry",
                exit_location="Manual Entry",
            )

            db.session.add(attendance)
            db.session.commit()

            # Trigger comp off calculation
            attendance.calculate_comp_off()
            flash(f"Manual attendance for {selected_user.first_name} submitted.", "success")
        except Exception as e:
            print(e)
            flash("Failed to submit manual attendance.", "error")

        return redirect(url_for('views.manual_attendance'))

    users = User.query.all() if current_user.email in ['sumana@nadiya.in', 'maneesh@nadiya.in'] else [current_user]
    return render_template("manual_attendance.html", users=users)

from sqlalchemy.orm import joinedload

@views.route('/my-compoffs')
@login_required
def my_compoffs():
    compoffs = CompOffRequest.query.options(
        joinedload(CompOffRequest.attendance)
    ).filter_by(user_id=current_user.id).order_by(CompOffRequest.requested_on.desc()).all()

    # Optional: if you want to find the date it was used (leave date)
    leave_dates = {}
    for leave in Leave.query.filter_by(user_id=current_user.id).all():
        if leave.ltype == "Comp Off":
            for compoff in compoffs:
                if compoff.used:
                    leave_dates[compoff.id] = leave.start_date.strftime("%d-%m-%Y")

    return render_template(
        "my_compoffs.html",
        compoffs=compoffs,
        leave_dates=leave_dates
    )
@views.route('/hr_policies')
@login_required
def hr_policies():
    # Only show policies sent to the current user
    policies = HRPolicy.query\
        .join(hr_policy_user)\
        .filter(hr_policy_user.c.user_id == current_user.id)\
        .order_by(HRPolicy.date_posted.desc())\
        .all()

    return render_template('hr_policies.html', policies=policies)


@views.route('/post_hr_policy', methods=['GET', 'POST'])
@login_required
def post_hr_policy():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        recipient_ids = request.form.getlist('recipients')

        image_url = None
        doc_url = None

        # Handle image upload to GCS
        image_file = request.files.get('attachments')
        if image_file and image_file.filename != '':
            image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_url = upload_file_to_gcs(image_file, image_filename, subfolder='uploads/photos')

        # Handle document upload to GCS
        doc_file = request.files.get('attachments1') or request.files.get('document')
        if doc_file and doc_file.filename != '':
            doc_filename = f"{uuid.uuid4().hex}_{secure_filename(doc_file.filename)}"
            doc_url = upload_file_to_gcs(doc_file, doc_filename, subfolder='uploads/docs')

        # Create the HR policy
        policy = HRPolicy(
            title=title,
            content=content,
            image_url=image_url,
            doc_url=doc_url
        )
        db.session.add(policy)

        # Collect valid emails and associate recipients
        valid_emails = []
        for user_id in recipient_ids:
            user = User.query.get(int(user_id))
            if user:
                policy.recipients.append(user)
                if user.email:
                    valid_emails.append(user.email)

        # Send one BCC email if there are valid emails
        if valid_emails:
            try:
                msg = Message(
                    subject='New HR Policy Posted',
                    sender=current_app.config['MAIL_DEFAULT_SENDER'],
                    recipients=[current_app.config['MAIL_DEFAULT_SENDER']],
                    bcc=valid_emails
                )
                policy_link = url_for('views.hr_policies', _external=True)
                msg.body = (
                    f"Dear All,\n\n"
                    f"A new HR policy has been posted on the portal.\n\n"
                    f"Title: {title}\n\n"
                    f"{content}\n\n"
                    f"View HR Policies: {policy_link}\n\n"
                    f"Regards,\n"
                    f"HR Team"
                )
                mail.send(msg)
            except Exception as e:
                print(f"[!] Failed to send HR policy email: {str(e)}")

        db.session.commit()
        flash('HR policy posted successfully and notifications sent to selected users!', 'success')
        return redirect(url_for('views.hr_policies'))

    users = User.query.order_by(User.first_name.asc()).all()
    return render_template('post_hr_policy.html', users=users)


@views.route('/delete_hr_policy/<int:policy_id>', methods=['POST'])
@login_required
def delete_hr_policy(policy_id):
    confirmation_id = request.form.get('confirmation_id')
    if (current_user.email == "sumana@nadiya.in" or current_user.email == "maneesh@nadiya.in") and confirmation_id == '24':
        policy = HRPolicy.query.get(policy_id)
        if policy:
            db.session.delete(policy)
            db.session.commit()
            flash('HR policy deleted successfully', 'success')
        else:
            flash('HR policy not found', 'danger')
    else:
        flash('Invalid confirmation ID or insufficient permissions', 'danger')
    return redirect(url_for('views.hr_policies'))


@views.route('/acknowledge_hr_policy/<int:policy_id>', methods=['POST'])
@login_required
def acknowledge_hr_policy(policy_id):
    existing = HRPolicyAcknowledgment.query.filter_by(
        user_id=current_user.id,
        hr_policy_id=policy_id
    ).first()
    if not existing:
        ack = HRPolicyAcknowledgment(
            user_id=current_user.id,
            hr_policy_id=policy_id
        )
        db.session.add(ack)
        db.session.commit()
        flash('Acknowledged successfully.', 'success')
    else:
        flash('You have already acknowledged this HR policy.', 'info')
    return redirect(url_for('views.hr_policies'))


@views.route('/hr-policy-read-status/<int:policy_id>')
@login_required
def hr_policy_read_status(policy_id):
    if current_user.email not in ["sumana@nadiya.in", "maneesh@nadiya.in", "support@nadiya.in"]:
        flash("Access denied.", "danger")
        return redirect(url_for('views.hr_policies'))

    policy = HRPolicy.query.get_or_404(policy_id)
    recipients = policy.recipients
    acknowledgments = {ack.user_id for ack in policy.acknowledgments}

    read_users = [user for user in recipients if user.id in acknowledgments]
    unread_users = [user for user in recipients if user.id not in acknowledgments]

    return render_template("hr_policy_status.html",
                           policy=policy,
                           read_users=read_users,
                           unread_users=unread_users)
