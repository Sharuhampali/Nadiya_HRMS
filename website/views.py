from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for,  send_from_directory
from flask_login import login_required, current_user
from .models import User, Attendance, Leave, Document, Holiday, Announcement, IntermediateLog, AnnouncementAcknowledgment
from . import db
from flask import Flask, send_file
from io import BytesIO
import pandas as pd
from geopy.geocoders import Nominatim
from datetime import datetime
from flask_uploads import UploadSet, IMAGES, UploadNotAllowed
import os
from . import mail
from flask_mail import Message
import pytz
from werkzeug.utils import secure_filename
from leave_calculator import calculate_initial_leaves
from dateutil.relativedelta import relativedelta


views = Blueprint('views', __name__)
india_tz = pytz.timezone('Asia/Kolkata')


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    current_date = datetime.now(india_tz).date().strftime("%d-%m-%y")
    if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in' :
        
    
        return render_template(
            "home.html",
            user=current_user,
            current_date=current_date
            
        )
    users_count = User.query.count()
    pending_leaves = Leave.query.filter(
                        (Leave.approved == False) | (Leave.approved == None),
                        (Leave.rejected == False) | (Leave.rejected == None)
                                            ).count()

    today_attendance = Attendance.query.filter_by(date=date.today()).count()
    announcements_count = Announcement.query.count()
    
 
    return render_template("admin_home.html", user=current_user, current_date= current_date, users_count=users_count,
            pending_leaves=pending_leaves,
            today_attendance=today_attendance,
            announcements_count=announcements_count)

# New category routes
@views.route('/attendance-category')
@login_required
def attendance_category():
    return render_template('attendance_category.html', user=current_user)

@views.route('/leaves-category')
@login_required
def leaves_category():
    return render_template('leaves_category.html', user=current_user)

@views.route('/holidays-category')
@login_required
def holidays_category():
    return render_template('holidays_category.html', user=current_user)

@views.route('/announcements-category')
@login_required
def announcements_category():
    return render_template('announcements_category.html', user=current_user)

@views.route('/misc-category')
@login_required
def misc_category():
    if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
        flash("You do not have permission to view this page.", category='error')
        return redirect(url_for('views.home'))
    return render_template('misc_category.html', user=current_user)

@views.route('/attendance')
def attendance_form():
    name = current_user.first_name

    return render_template('attendance.html', name = name)

from datetime import  timedelta
geoLoc = Nominatim(user_agent="my_app")

@views.route('/submit', methods=['POST'])
@login_required
def submit_attendance():
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    entry_exit = request.form.get('entry_exit')  # 'entry', 'exit', etc.

    site_name = request.form.get('site_name')      # For exit or intermediate


    user_id = current_user.id
    user_attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.id.desc()).first()

    reason = request.form.get('reason', None)

    india_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(india_tz).time()

    # Handle stale entries with no exit for > 20 hours
    if user_attendance and user_attendance.exit_time is None:
        if (datetime.combine(datetime.today(), now) - datetime.combine(datetime.today(), user_attendance.entry_time)) > timedelta(hours=20):
            user_attendance.exit_time = (datetime.combine(datetime.today(), user_attendance.entry_time) + timedelta(hours=5)).time()
            user_attendance.calculate_comp_off()
            try:
                db.session.commit()
            except Exception as e:
                print(e)
                flash('There was an issue updating your attendance record.', 'error')
                return redirect(url_for('views.home'))
            user_attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.id.desc()).first()

    # Handle intermediate entries
    # Handle intermediate entries
    if entry_exit in ['intermediate_entry', 'intermediate_exit']:
        # Check last intermediate entry for the day
        last_log = IntermediateLog.query.filter_by(
            user_id=current_user.id,
            date=datetime.now(india_tz).date()
        ).order_by(IntermediateLog.id.desc()).first()

        if entry_exit == 'intermediate_entry':
            if last_log and last_log.entry_type == 'intermediate_entry':
                flash('You must mark an intermediate exit before logging a new intermediate entry.', 'warning')
                return redirect(url_for('views.home'))

        # if entry_exit == 'intermediate_exit':
            # if not last_log or last_log.entry_type != 'intermediate_entry':
            #     flash('You must mark an intermediate entry before logging an intermediate exit.', 'warning')
            #     return redirect(url_for('views.home'))

        try:
            location_obj = geoLoc.reverse(f"{latitude}, {longitude}")
            location = location_obj.address if location_obj else "Unknown"
        except Exception as e:
            print(f"Intermediate geo error: {e}")
            location = "Unknown"

        new_log = IntermediateLog(
            user_id=current_user.id,
            date=datetime.now(india_tz).date(),
            time=now.replace(microsecond=0),
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
        if user_attendance and user_attendance.exit_time is None:
            flash('Please exit the current attendance record before submitting another entry.', 'warning')
        else:
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
                entry_time=now.replace(microsecond=0),
                date=datetime.now(india_tz).date().strftime("%Y-%m-%d"),
                day=datetime.now(india_tz).strftime('%A'),
                reason=reason,
                site_name_e=site_name 
            )
            db.session.add(new_attendance)

    # Exit logic
    elif entry_exit == 'exit' and user_attendance:
        if user_attendance.exit_time is not None:
            flash('Please close the current attendance record before submitting another exit.', 'warning')
        else:
            site_name = request.form.get('site_name')
            try:
                exit_location = geoLoc.reverse(f"{latitude}, {longitude}")
                exit_address = exit_location.address if exit_location else "Unknown"
            except Exception as e:
                print(f"Error fetching exit location: {str(e)}")
                exit_address = "Unknown"

            def is_second_or_fourth_saturday(date):
                first_day_of_month = date.replace(day=1)
                first_day_weekday = first_day_of_month.weekday()
                first_saturday = first_day_of_month + timedelta(days=(5 - first_day_weekday) % 7)
                second_saturday = first_saturday + timedelta(days=7)
                fourth_saturday = first_saturday + timedelta(days=21)
                return date == second_saturday or date == fourth_saturday

            def is_holiday(date):
                return date.weekday() == 6 or is_second_or_fourth_saturday(date)

            if request.form.get('holiday'):
                user_attendance.hol = 10000

            current_date = datetime.now(india_tz).date()
            if Holiday.query.filter_by(date=current_date).first() or is_holiday(current_date):
                user_attendance.hol = 10000

            user_attendance.exit_time = now.replace(microsecond=0)
            user_attendance.exit_location = exit_address
            user_attendance.site_name = site_name  # ✅ Exit uses site_name
            user_attendance.calculate_comp_off()

    # Commit changes to DB
    try:
        db.session.commit()
        return redirect(url_for('views.home'))
    except Exception as e:
        print(e)
        flash('There was an issue submitting your attendance.', 'error')
        return redirect(url_for('views.home'))


@views.route('/all', methods=['GET'])
def all():
    try:
        user = User.query.all()
        role = [user.role for user in User.query.all()]
        emails = [user.email for user in User.query.all()]  # Fetch all emails from the database
        return render_template('all.html', emails=emails, user = user, role = role)
    except Exception as e:
        return str(e)

@views.route('/attendance_table')
@login_required
def attendance_table():
    if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
        flash("You do not have permission to view this page.", category='error')
        return redirect(url_for('views.home'))

    attendances = Attendance.query.all()


    return render_template('attendance_table.html', attendances=attendances)

from datetime import time
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

@views.route('/who_output', methods=['GET','POST'])

def who_output():
    name = current_user.first_name

    user_attendances = Attendance.query.filter_by(name=name).all()
    totes = sum(attendance.totes for attendance in user_attendances)
    late_entries = sum(1 for attendance in user_attendances if is_late(attendance.entry_time))

    return render_template('who_output.html', attendances=user_attendances, name=name,totes = totes, late_entries = late_entries)


@views.route('/who', methods=['GET','POST'])
@login_required
def who():
    return render_template('who.html')

def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)

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
    db.session.commit()

    user = User.query.get(leave.user_id)

    # Compose detailed approval message
    leave_summary = json.loads(leave.leaves_data or "[]")
    details = '\n'.join(
        f"- {entry['date']}: {entry['duration']} day(s) - {entry['type']}" 
        for entry in leave_summary
    )

    send_email(
        'Leave Approved',
        user.email,
        f"Your leave request has been approved.\n\n"
        f"Total Days: {leave.days}\n"
        f"Types: {leave.ltype}\n"
        f"Details:\n{details}\n\n"
        f"Approved by: {current_user.email}"
    )

    return redirect(url_for('views.leave_requests'))


# @views.route('/reject/<int:leave_id>', methods=['POST'])
# @login_required
# def reject(leave_id):
#     leave = Leave.query.get(leave_id)
#     if not leave:
#         flash("Leave request not found.", category='error')
#         return redirect(url_for('views.leave_requests'))

#     leave.approved_by = current_user.email
#     leave.rejected = True
#     user = User.query.get(leave.user_id)
#     days = float(leave.days)

#     # Adjust counters based on leave type
#     if leave.ltype == 'Compoff':
#         user_attendances = Attendance.query.filter_by(user_id=leave.user_id).all()
#         for attendance in user_attendances:
#             attendance.compoff += days  # Example adjustment

#     elif leave.ltype == 'Earned':
#         user.earned -= days

#     elif leave.ltype == 'Leave w/o Pay':
#         user.pay -= days

#     elif leave.ltype == 'Medical/Sick':
#         user.medic -= days

#     db.session.commit()
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
    leave.remarks = remarks  # Optional: only if you have a 'remarks' field in Leave model

    # Reverse leave balances using leaves_data breakdown
    import json
    entries = json.loads(leave.leaves_data)

    for entry in entries:
        date = entry['date']
        duration = float(entry['duration'])
        ltype = entry['type']

        if ltype == 'Compoff':
            for att in user.attendances:
                if att.date.strftime('%Y-%m-%d') == date:
                    att.compoff += duration
                    break
            else:
                if user.attendances:
                    user.attendances[0].compoff += duration

        elif ltype == 'Earned':
            user.earned -= duration

        elif ltype == 'Leave w/o Pay':
            user.pay -= duration

        elif ltype == 'Medical/Sick':
            user.medic -= duration

    db.session.commit()
    flash("Leave request rejected and leave balances restored.", "info")

    # Construct email summary
    leave_summary = json.loads(leave.leaves_data or "[]")
    details = '\n'.join(
        f"- {entry['date']}: {entry['duration']} day(s) - {entry['type']}"
        for entry in leave_summary
    )

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

    return redirect(url_for('views.leave_requests'))



@views.route('/approved_leaves')
@login_required
def approved_leaves():
    approved_leaves = Leave.query.filter_by(user_id=current_user.id, ).all()
    return render_template('approved_leaves.html', leaves=approved_leaves)

@views.route('/reset_leaves', methods=['GET', 'POST'])
@login_required
def reset_leaves():
    if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
        flash("You do not have permission to reset leaves.", category='error')
        return redirect(url_for('views.home'))

    users = User.query.all()
    for user in users:
        attendances = Attendance.query.filter_by(user_id=user.id).all()

        # Reset compoff for each attendance record
        for attendance in attendances:
            attendance.compoff = 0

    for user in users:
        e = min(10, 15 - user.earned)

    for user in users:
        user.medic = 0
        user.pay = 0
        user.earned = 0 - e
        # Add other leave types if applicable

    # Delete all contents of the Holiday table
    holidays = Holiday.query.all()
    for holiday in holidays:
        db.session.delete(holiday)

    db.session.commit()
    flash("All users' leave counts have been reset to zero, and all holidays have been deleted.", category='success')
    return redirect(url_for('views.home'))

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

    for leave in approved_leaves:
        leave_data = json.loads(leave.leaves_data)
        for entry in leave_data:
            ltype = entry.get('type')
            duration = float(entry.get('duration', 0))
            if ltype == 'Earned':
                earned_sum += duration
            elif ltype == 'Medical/Sick':
                medic_sum += duration
            elif ltype == 'Leave w/o Pay':
                pay_sum += duration


    return render_template('who1_output.html', user=user, approved_leaves=approved_leaves, earned_sum=earned_sum, medic_sum=medic_sum, pay_sum=pay_sum)

@views.route('/display_compoff', methods=['GET'])
@login_required
def display_compoff():
    if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
        flash("You do not have permission to view this page.", category='error')
        return redirect(url_for('views.home'))

    # Fetch all users with their total_compoff
    users = User.query.all()
    user_compoffs = [{'name': f'{user.first_name}', 'total_compoff': user.total_compoff} for user in users]

    return render_template('display_compoff.html', user_compoffs=user_compoffs)

photos = UploadSet('photos', IMAGES)
docs = UploadSet('docs', ('pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'))

@views.route('/profile/<int:user_id>', methods=['GET', 'POST'])
@login_required
def profile(user_id):
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", category='error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'photo' in request.files and request.files['photo']:
            filename = photos.save(request.files['photo'])
            user.photo = filename

        if 'document' in request.files and request.files['document']:
            file = request.files['document']
            if file:
                filename = docs.save(file)
                document_type = request.form.get('document_type')  # Assuming document type is selected in form
                if user.documents:
                    # Delete the old document file if it exists
                    for doc in user.documents:
                        if doc.document_type == document_type:
                            doc.filename = filename
                            break
                    else:
                        new_document = Document(user_id=user.id, filename=filename, document_type=document_type)
                        user.documents.append(new_document)
                        db.session.add(new_document)
                else:
                    new_document = Document(user_id=user.id, filename=filename, document_type=document_type)
                    user.documents.append(new_document)
                    db.session.add(new_document)

        db.session.commit()
        flash('Profile updated successfully')
        return redirect(url_for('views.profile', user_id=user_id))

    return render_template('profile.html', user=user)

@views.route('/upload', methods=['POST', 'GET'])
@login_required

def upload():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        try:
            if 'document' in request.files:
                filename = docs.save(request.files['document'])
                flash('Document uploaded successfully.', 'success')
            else:
                flash('No document selected for upload.', 'warning')
        except UploadNotAllowed:
            flash('Upload not allowed. Please check the file type.', 'error')

        return redirect(url_for('views.profile', user_id=user_id))

    elif request.method == 'GET':
        setname = request.args.get('setname')
        filename = request.args.get('filename')
        if setname and filename:
            return redirect(url_for('uploaded_file', setname=setname, filename=filename))
        else:
            return "Bad Request", 400

    return "Method not allowed", 405

@views.route('/create_user', methods=['GET', 'POST'])
@login_required

def create_user():
    users = User.query.all()
    return render_template('create_user.html', users=users)

from flask import abort, current_app


@views.route('/uploaded_file/<setname>/<filename>')
@login_required
def uploaded_file(setname, filename):
    if setname == 'photos':
        file_path = os.path.join(current_app.config['UPLOADED_PHOTOS_DEST'], filename)
        print(f"Serving photo from: {file_path}")
        if not os.path.exists(file_path):
            print("File not found:", file_path)
            return abort(404)  # Return 404 Not Found if the file does not exist
        return send_from_directory(current_app.config['UPLOADED_PHOTOS_DEST'], filename)
    elif setname == 'docs':
        file_path = os.path.join(current_app.config['UPLOADED_DOCS_DEST'], filename)
        print(f"Serving doc from: {file_path}")
        if not os.path.exists(file_path):
            print("File not found:", file_path)
            return abort(404)  # Return 404 Not Found if the file does not exist
        return send_from_directory(current_app.config['UPLOADED_DOCS_DEST'], filename)
    else:
        return "File type not supported", 400

# @views.route('/assign_roles', methods=['GET', 'POST'])
# @login_required
# def assign_roles():
#     if current_user.email != 'sumana@nadiya.in'and current_user.email!= 'maneesh@nadiya.in':
#         flash('You do not have permission to access this page.', 'error')
#         return redirect(url_for('views.home'))

#     if request.method == 'POST':
#         user_id = request.form['user_id']
#         role = request.form['role']
#         is_probation = request.form.get('probation') == 'on'
#         user = User.query.get(user_id)
#      #### this logic is not for 1.5 leaves every month, this is only for calculating leaves if app use started in the middle of the year
#         if user:
#             user.role = role
#             user.set_probation_status(is_probation)

#             if not is_probation:
#                 today = datetime.today()


#                 if today.month >= 4:  # Financial year starts on April 1st
#                     start_of_year = datetime(today.year, 4, 1)
#                     end_of_year = datetime(today.year + 1, 3, 31)
#                 else:  # Financial year starts on April 1st of the previous year
#                     start_of_year = datetime(today.year - 1, 4, 1)
#                     end_of_year = datetime(today.year, 3, 31)

#                 months_left = (end_of_year.year - today.year) * 12 + (end_of_year.month - today.month) - today.day // 30

#                 # Calculate leave entitlements and round to 2 decimal places
#                 earned_leaves = round((months_left * 15) / 12, 2)
#                 user.earned = 15 - earned_leaves

#                 m_leaves = round((months_left * 6) / 12, 2)
#                 user.medic = 6 - m_leaves

#                 p_leaves = round((months_left * 10) / 12, 2)
#                 user.pay = 10 - p_leaves

#             if is_probation:
#                 today = datetime.today()

#                 # Determine the start and end of the financial year
#                 if today.month >= 4:  # Financial year starts on April 1st
#                     start_of_year = datetime(today.year, 4, 1)
#                     end_of_year = datetime(today.year + 1, 3, 31)
#                 else:  # Financial year starts on April 1st of the previous year
#                     start_of_year = datetime(today.year - 1, 4, 1)
#                     end_of_year = datetime(today.year, 3, 31)

#                 months_left = (end_of_year.year - today.year) * 12 + (end_of_year.month - today.month) - today.day // 30
#                 p_leaves = round((months_left * 10) / 12, 2)
#                 user.pay = 10 - p_leaves

#             user.probation = is_probation

#             db.session.commit()
#             flash(f'Role {role} assigned to {user.first_name}.', 'success')
#         else:
#             flash('User not found.', 'error')
#         return redirect(url_for('views.assign_roles'))

#     users = User.query.all()

#     return render_template('assign_roles.html', users=users)
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

        user = User.query.get(user_id)
        if user:
            previously_probation = user.probation
            user.role = role
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



@views.route('/leave_requests')
@login_required
def leave_requests():
    user_role = current_user.role
    print(f"Current user's role: {user_role}")

    # # Special case override for specific admin emails
    # if current_user.email in ['sumana@nadiya.in', 'maneesh@nadiya.in']:
    #     leave_requests = Leave.query.all()
    #     return render_template('leave_requests.html', leave_requests=leave_requests)

    # # director can see everything
    # if user_role == 'director':
    #     leave_requests = Leave.query.all()
    #     return render_template('leave_requests.html', leave_requests=leave_requests)

    # Get all roles where current user is a manager (i.e., in the value list of ROLES_HIERARCHY)
    subordinate_roles = [role for role, managers in ROLES_HIERARCHY.items() if user_role in managers]

    if not subordinate_roles:
        flash("You do not have permission to view leave requests.", category='error')
        return redirect(url_for('views.home'))

    # Fetch leave requests for users with subordinate roles
    leave_requests = Leave.query.join(User).filter(User.role.in_(subordinate_roles)).all()
    return render_template('leave_requests.html', leave_requests=leave_requests)


ROLES_HIERARCHY = {
    # Lowest tier → respective manager(s)
    'design_member': ['design_head','operations_head', 'director'],
    'service_member': ['service_manager', 'operations_head', 'director'],
    'accounts_member': ['accounts_manager','operations_head','director'],
    
    # Mid-tier managers → higher-level director(s)
    'design_head': ['director','operations_head'],
    'service_manager': ['director','operations_head'],
    'business_development_manager': ['director','operations_head'],
    'accounts_manager': ['director','operations_head'],

    # Director reports to operational head and vice versa 
    'director': ['operations_head'],
    'operations_head': ['director']
}


# @views.route('/apply_leave', methods=['GET', 'POST'])
# @login_required
# def apply_leave():
#     if request.method == 'POST':
#         start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%d').date()
#         end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%d').date()
#         ltype = request.form['ltype']
#         reason = request.form.get('reason', None)
#         days = float(request.form['days'])

#         if ltype == 'Medical/Sick':
#             if current_user.medic < 6:
#                 current_user.medic += days
#             else:
#                 flash("Not enough Medical/Sick leaves left to apply", 'error')
#                 return redirect(url_for('views.apply_leave'))

#         elif ltype == 'Leave w/o Pay':
#             if current_user.pay < 10:
#                 current_user.pay += days
#             else:
#                 flash("Not enough Leave w/o Pay leaves left to apply", 'error')
#                 return redirect(url_for('views.apply_leave'))

#         elif ltype == 'Earned':
#             if current_user.earned < 15:
#                 current_user.earned += days
#             else:
#                 flash("Not enough Earned leaves left to apply", 'error')
#                 return redirect(url_for('views.apply_leave'))

#         elif ltype == 'Compoff':
#             if current_user.total_compoff < days:
#                 flash("Not enough compoff leaves left to apply", 'error')
#                 return redirect(url_for('views.apply_leave'))

#             # Deduct compoff from the first attendance record with compoff > 0
#             for attendance in current_user.attendances:
#                 if attendance.compoff >= days:
#                     attendance.compoff -= days
#                     db.session.commit()
#                     break

#         # Create a new leave instance and save it to the database
#         new_leave = Leave(
#             user_id=current_user.id,
#             start_date=start_date,
#             end_date=end_date,
#             reason=reason,
#             days=days,
#             ltype=ltype
#         )
#         db.session.add(new_leave)
#         db.session.commit()

#         # Get manager roles based on user's role
#         manager_roles = ROLES_HIERARCHY.get(current_user.role)

#         if not manager_roles:
#             flash("Your role does not have an assigned manager.", 'error')
#             return redirect(url_for('views.apply_leave'))
        
#         if isinstance(manager_roles, str):
#             manager_roles = [manager_roles]

#         # Get users matching any of the manager roles
#         managers = User.query.filter(User.role.in_(manager_roles)).all()

#         if not managers:
#             flash("No manager found for your role.", 'error')
#             return redirect(url_for('views.apply_leave'))

#         # Collect their email addresses
#         recipient_emails = [manager.email for manager in managers if manager.email]

#         # Always include this fixed oversight email
#         STATIC_MANAGER_EMAIL = "sumana@nadiya.in"
#         if STATIC_MANAGER_EMAIL not in recipient_emails:
#             recipient_emails.append(STATIC_MANAGER_EMAIL)

#         approval_url = url_for('views.approve_leave', leave_id=new_leave.id, _external=True)

#         msg = Message(
#             'New Leave Application',
#             recipients=recipient_emails
#         )
#         msg.body = (
#             f'{current_user.first_name} has applied for leave.\n\n'
#             f'Type: {ltype}\n'
#             f'Start Date: {start_date}\n'
#             f'End Date: {end_date}\n'
#             f'Days: {days}\n'
#             f'Reason: {reason}\n\n'
#             f'Click here to review/approve: {approval_url}'
#         )

#         try:
#             mail.send(msg)
#             flash('Leave application submitted successfully.', 'success')
#         except Exception as e:
#             print(f"Failed to send mail: {e}")
#             flash('Failed to send leave application.', 'error')

#         return redirect(url_for('views.apply_leave'))

#     return render_template('apply_leave.html', user=current_user, today=datetime.today().date())

import json
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

        # Build leave entry list
        for date_str, dur_str, ltype in zip(dates, durations, types):
            if not date_str or not ltype:
                continue  # Skip incomplete rows

            duration = float(dur_str)
            total_days += duration
            summary[ltype] += duration

            leave_entries.append({
                'date': date_str,
                'duration': duration,
                'type': ltype
            })
        

        # Validate leave quotas
        if summary['Medical/Sick'] > (6 - current_user.medic):
            flash("Not enough Medical/Sick leaves left.", 'error')
            return redirect(url_for('views.apply_leave'))

        if summary['Earned'] > (15 - current_user.earned):
            flash("Not enough Earned leaves left.", 'error')
            return redirect(url_for('views.apply_leave'))

        if summary['Leave w/o Pay'] > (10 - current_user.pay):
            flash("Leave w/o Pay quota exceeded.", 'error')
            return redirect(url_for('views.apply_leave'))

        if summary['Compoff'] > current_user.total_compoff:
            flash("Not enough Compoff leaves left.", 'error')
            return redirect(url_for('views.apply_leave'))

        # Deduct compoff from attendance record
        if summary['Compoff'] > 0:
            remaining = summary['Compoff']
            for att in current_user.attendances:
                if att.compoff >= remaining:
                    att.compoff -= remaining
                    db.session.commit()
                    break

        # Apply leave balances
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

        # Manager logic unchanged
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

        approval_url = url_for('views.leave_requests',  _external=True)

        msg = Message('New Leave Application', recipients=recipient_emails)
        msg.body = (
            f'{current_user.first_name} has applied for leave.\n\n'
            f'Total Days: {total_days}\n'
            f'Breakdown:\n' +
            '\n'.join([f"{k}: {v}" for k, v in summary.items() if v > 0]) +
            f'\nReason: {reason}\n\n'
            f'Approve here: {approval_url}'
        )

        try:
            mail.send(msg)
            flash('Leave application submitted successfully.', 'success')
        except Exception as e:
            print(f"Email error: {e}")
            flash('Leave application sent, but failed to notify manager.', 'warning')

        return redirect(url_for('views.apply_leave'))

    return render_template('apply_leave.html', user=current_user, today=datetime.today().date().strftime("%d-%m-%y"))


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

@views.route('/announcements')
def announcements():
    # Fetch announcements from the database
    announcements = Announcement.query.all()
    return render_template('announcements.html', announcements=announcements)

# @views.route('/post_announcement', methods=['GET', 'POST'])
# def post_announcement():
#     if request.method == 'POST':
#         title = request.form.get('title')
#         content = request.form.get('content')

#         # Create a new announcement
#         announcement = Announcement(title=title, content=content)
#         db.session.add(announcement)
#         db.session.commit()

#         # Fetch all registered user emails
#         users = User.query.all()
#         user_emails = [user.email for user in users]

#         # Send email notifications
#         with current_app.app_context():
#             for email in user_emails:
#                 msg = Message(subject='New Announcement Posted',
#                               sender=current_app.config['MAIL_DEFAULT_SENDER'],
#                               recipients=[email])
#                 msg.body = f'A new announcement has been posted:\n\nTitle: {title}\nContent: {content}'
#                 mail.send(msg)

#         flash('Announcement posted successfully and notifications sent!', 'success')
#         return redirect(url_for('views.announcements'))

#     return render_template('post_announcement.html')
@views.route('/post_announcement', methods=['GET', 'POST'])
def post_announcement():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        file = request.files.get('attachments')  # Fix name match
        file1 = request.files.get('attachments1')

        image_url = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join('static', 'uploads', 'docs', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
            image_url = f'uploads/docs/{filename}'

        doc_url = None
        if file1 and file1.filename != '':
            filename = secure_filename(file1.filename)
            file_path = os.path.join('static', 'uploads', 'docs', filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file1.save(file_path)
            doc_url = f'uploads/docs/{filename}'

        announcement = Announcement(title=title, content=content, image_url=image_url, doc_url=doc_url)
        db.session.add(announcement)
        db.session.commit()

        users = User.query.all()
        user_emails = [user.email for user in users]

        # with current_app.app_context():
        #     for email in user_emails:
        #         msg = Message(subject='New Announcement Posted',
        #                       sender=current_app.config['MAIL_DEFAULT_SENDER'],
        #                       recipients=[email])
        #         msg.body = f'A new announcement has been posted:\n\nTitle: {title}\nContent: {content}'
        #         mail.send(msg)

        flash('Announcement posted successfully and notifications sent!', 'success')
        return redirect(url_for('views.announcements'))

    return render_template('post_announcement.html')


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


# import uuid
# @views.route('/forgot_password', methods=['GET', 'POST'])
# def forgot_password():
#     if request.method == 'POST':
#         email = request.form['email']
#         user = User.query.filter_by(email=email).first()

#         if user:
#             # Generate a password reset token
#             reset_token = str(uuid.uuid4())
#             user.reset_token = reset_token
#             db.session.commit()

#             # Send reset email
#             reset_link = url_for('views.reset_password', token=reset_token, _external=True)
#             msg = Message('Password Reset Request', recipients=[email])
#             msg.body = f'Click the link below to reset your password:\n{reset_link}'
#             mail.send(msg)

#             flash('Password reset link sent to your email.', 'info')
#         else:
#             flash('No account found with that email address.', 'error')

#         return redirect(url_for('views.forgot_password'))

#     return render_template('forgot_password.html')

# from werkzeug.security import generate_password_hash

# @views.route('/reset_password/<token>', methods=['GET', 'POST'])
# def reset_password(token):
#     user = User.query.filter_by(reset_token=token).first()

#     if request.method == 'POST':
#         if user:
#             new_password = request.form['password']
#             user.password = generate_password_hash(new_password)
#             user.reset_token = None  # Invalidate the token
#             db.session.commit()

#             flash('Your password has been updated!', 'success')
#             return redirect(url_for('auth.login'))  # Redirect to login or another page
#         else:
#             flash('Invalid or expired token.', 'error')

#     return render_template('reset_password.html', token=token)

import uuid
from werkzeug.security import generate_password_hash
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
            msg.body = f'Click the link below to reset your password:\n{reset_link}\n\nThis link will expire in 1 hour.'
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

from flask_mail import Message

@views.route('/export', methods=['POST', 'GET'])
@login_required
def export_all_data():
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        tables = {
            'Users': User,
            'Documents': Document,
            'Attendance': Attendance,
            'Leaves': Leave,
            'Holidays': Holiday,
            'Announcements': Announcement
        }

        for sheet_name, model in tables.items():
            query = model.query.all()
            data = [item.__dict__.copy() for item in query]
            for row in data:
                row.pop('_sa_instance_state', None)
            df = pd.DataFrame(data)
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

    output.seek(0)

    # Send the email
    msg = Message(subject="HRMS System Backup",
                  recipients=["sumana@nadiya.in.com", "maneesh@nadiya.in"])  # Replace with actual recipient
    msg.body = "Attached is the latest system backup of all tables before reset."
    msg.attach("all_data_export.xlsx", 
               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
               output.read())

    try:
        mail.send(msg)
        flash("Exported data and emailed backup successfully.", "success")
    except Exception as e:
        flash(f"Exported data, but failed to send email: {str(e)}", "warning")

    # Reset pointer to allow browser download too (optional)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="all_data_export.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )



#############################################################################################

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


# @views.route('/approve_compoff/<int:attendance_id>', methods=['POST'])
# @login_required
# def approve_compoff(attendance_id):
#     attendance = Attendance.query.get(attendance_id)
#     submitter = User.query.get(attendance.user_id)

#     if not has_approval_authority(current_user.role, submitter.role):
#         flash("Not authorized.", "error")
#         return redirect(url_for('views.home'))

#     if attendance.compoff_pending:
#         attendance.compoff = attendance.compoff_requested
#         attendance.compoff_pending = False
#         attendance.compoff_requested = 0
#         attendance.approved_by_id = current_user.id
#         db.session.commit()
#         flash("Comp off approved.", "success")
#     return redirect(url_for('views.pending_compoffs'))
@views.route('/approve_compoff/<int:attendance_id>', methods=['POST'])
@login_required
def approve_compoff(attendance_id):
    attendance = Attendance.query.get(attendance_id)
    if not attendance:
        flash("Attendance record not found.", "error")
        return redirect(url_for('views.pending_compoffs'))

    submitter = User.query.get(attendance.user_id)
    if not submitter:
        flash("User not found for this record.", "error")
        return redirect(url_for('views.pending_compoffs'))

    if not has_approval_authority(current_user.role, submitter.role):
        flash("Not authorized.", "error")
        return redirect(url_for('views.home'))

    if attendance.compoff_pending:
        attendance.compoff = attendance.compoff_requested
        attendance.compoff_requested = 0
        attendance.compoff_pending = False
        attendance.approved_by_id = current_user.id
        db.session.commit()

        # Optional: Notify user
        send_email(
            subject="Comp Off Approved",
            recipient=submitter.email,
            body=(
                f"Dear {submitter.first_name},\n\n"
                f"Your Comp Off request for {attendance.date.strftime('%d-%m-%Y')} has been approved.\n"
                f"Approved by: {current_user.first_name} ({current_user.email})\n\n"
                f"Regards,\nHR Team"
            )
        )

        flash("Comp off approved and user notified.", "success")

    return redirect(url_for('views.pending_compoffs'))


# @views.route('/reject_compoff/<int:attendance_id>', methods=['POST'])
# @login_required
# def reject_compoff(attendance_id):
#     attendance = Attendance.query.get(attendance_id)
#     submitter = User.query.get(attendance.user_id)

#     if not has_approval_authority(current_user.role, submitter.role):
#         flash("Not authorized.", "error")
#         return redirect(url_for('views.home'))

#     if attendance.compoff_pending:
#         attendance.compoff = 0
#         attendance.compoff_pending = False
#         attendance.compoff_requested = 0
#         attendance.approved_by_id = None
#         db.session.commit()
#         flash("Comp off rejected.", "info")
#     return redirect(url_for('views.pending_compoffs'))
@views.route('/reject_compoff/<int:attendance_id>', methods=['POST'])
@login_required
def reject_compoff(attendance_id):
    attendance = Attendance.query.get(attendance_id)
    submitter = User.query.get(attendance.user_id)

    if not has_approval_authority(current_user.role, submitter.role):
        flash("Not authorized.", "error")
        return redirect(url_for('views.home'))

    remarks = request.form.get("remarks", "").strip()

    if attendance.compoff_pending:
        attendance.compoff = 0
        attendance.compoff_pending = False
        attendance.compoff_requested = 0
        attendance.approved_by_id = None
        db.session.commit()

        # Format the email
        subject = 'Comp Off Request Rejected'
        body = (
            f"Dear {submitter.first_name},\n\n"
            f"Your Comp Off request for the date: {attendance.date.strftime('%d-%m-%Y')} has been rejected.\n\n"
            f"Reason:\n{remarks}\n\n"
            f"Rejected by: {current_user.first_name} ({current_user.email})\n"
            f"If you have any questions, please reach out to your reporting manager or HR.\n\n"
            f"Regards,\nHR Team"
        )

        # Send email
        send_email(
            subject=subject,
            recipient=submitter.email,
            body=body
        )

        flash("Comp Off rejected. Notification sent to the user.", "info")
    else:
        flash("No pending Comp Off request found for this record.", "warning")

    return redirect(url_for('views.pending_compoffs'))



# @views.route('/pending_compoffs')
# @login_required
# def pending_compoffs():
#     pending_records = Attendance.query.filter_by(compoff_pending=True).all()

#     approvable = [
#         record for record in pending_records
#         if (submitter := User.query.get(record.user_id)) 
#         and has_approval_authority(current_user.role, submitter.role)
#     ]

#     return render_template('pending_compoffs.html', records=approvable)
@views.route('/pending_compoffs')
@login_required
def pending_compoffs():
    all_records = Attendance.query.filter(
        (Attendance.compoff_pending == True) |
        (Attendance.compoff > 0) |
        ((Attendance.compoff == 0) & (Attendance.compoff_requested > 0))
    ).all()

    approvable = []

    for record in all_records:
        submitter = User.query.get(record.user_id)

        if submitter and has_approval_authority(current_user.role, submitter.role):
            # Attach user object for use in template
            record.user = submitter

            # Determine compoff status inline
            if record.compoff_pending:
                record.compoff_status = 'pending'
            elif record.compoff and record.compoff > 0:
                record.compoff_status = 'approved'
            elif not record.compoff_pending and record.compoff_requested > 0 and (record.compoff == 0 or record.compoff is None):
                record.compoff_status = 'rejected'
            else:
                record.compoff_status = 'unknown'  # fallback for edge cases

            approvable.append(record)

    return render_template('pending_compoffs.html', records=approvable)




def has_approval_authority(approver_role, submitter_role):
    allowed_roles = ROLES_HIERARCHY.get(submitter_role, [])
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]
    return approver_role in allowed_roles


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
    if current_user.email not in ["sumana@nadiya.in", "maneesh@nadiya.in"]:
        flash("Access denied.", "danger")
        return redirect(url_for('views.announcements'))

    announcement = Announcement.query.get_or_404(announcement_id)
    all_users = User.query.all()
    acknowledgments = {ack.user_id for ack in announcement.acknowledgments}
    
    read_users = [user for user in all_users if user.id in acknowledgments]
    unread_users = [user for user in all_users if user.id not in acknowledgments]

    return render_template("acknowledgment_status.html", announcement=announcement,
                           read_users=read_users, unread_users=unread_users)
