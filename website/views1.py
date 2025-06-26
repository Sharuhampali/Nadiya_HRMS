# from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for,  send_from_directory
# from flask_login import login_required, current_user
# from .models import User, Attendance, Leave, Document, Holiday, Announcement
# from . import db
# from flask import Flask, send_file
# from io import BytesIO
# import pandas as pd
# from geopy.geocoders import Nominatim
# from datetime import datetime
# from flask_uploads import UploadSet, IMAGES, UploadNotAllowed
# import os
# from . import mail
# from flask_mail import Message
# import pytz


# views = Blueprint('views', __name__)
# india_tz = pytz.timezone('Asia/Kolkata')


# @views.route('/', methods=['GET', 'POST'])
# @login_required
# def home():
#     current_date = datetime.now(india_tz).date()
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in' :
#         return render_template("home.html", user=current_user, current_date= current_date)

#     return render_template("admin_home.html", user=current_user, current_date= current_date)


# @views.route('/attendance')
# def attendance_form():
#     name = current_user.first_name

#     return render_template('attendance.html', name = name)

# from datetime import  timedelta
# geoLoc = Nominatim(user_agent="my_app")

# @views.route('/submit', methods=['POST'])
# @login_required
# def submit_attendance():
#     latitude = request.form.get('latitude')
#     longitude = request.form.get('longitude')
#     entry_exit = request.form.get('entry_exit')  # 'entry' or 'exit'
#     site_name = request.form.get('site_name')  # Get site/customer name if provided
#     user_id = current_user.id
#     user_attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.id.desc()).first()

#     if 'reason' in request.form:
#         reason = request.form['reason']
#     else:
#         reason = None
    
    
#     india_tz = pytz.timezone('Asia/Kolkata')
#     now = datetime.now(india_tz).time()  # Get current time only

#     if user_attendance and user_attendance.exit_time is None:
#         if (datetime.combine(datetime.today(), now) - datetime.combine(datetime.today(), user_attendance.entry_time)) > timedelta(hours=20):
#             user_attendance.exit_time = (datetime.combine(datetime.today(), user_attendance.entry_time) + timedelta(hours=5)).time()
#             user_attendance.calculate_comp_off()  # Ensure this method exists and works as intended
#             try:
#                 db.session.commit()
#             except Exception as e:
#                 print(e)
#                 flash('There was an issue updating your attendance record.', 'error')
#                 return redirect(url_for('views.home'))
#             # Refresh user_attendance after commit
#             user_attendance = Attendance.query.filter_by(user_id=user_id).order_by(Attendance.id.desc()).first()

#     if entry_exit == 'entry':
#         if user_attendance and user_attendance.exit_time is None:
#             flash('Please exit the current attendance record before submitting another entry.', 'warning')
#         else:
#             # Get entry location
#             try:
#                 entry_location = geoLoc.reverse(f"{latitude}, {longitude}")
#                 entry_address = entry_location.address if entry_location else "Unknown"
#             except Exception as e:
#                 print(f"Error fetching entry location: {str(e)}")
#                 entry_address = "Unknown"

#             new_attendance = Attendance(
#                 name=current_user.first_name,
#                 latitude=latitude,
#                 longitude=longitude,
#                 entry_location=entry_address,
#                 user_id=user_id,
#                 entry_time=now.replace(microsecond=0),  # Store only time
#                 date=datetime.now(india_tz).date(),
#                 day=datetime.now(india_tz).strftime('%A'),
#                 reason=reason,
#                 site_name=site_name
#             )
#             db.session.add(new_attendance)

#     elif entry_exit == 'exit' and user_attendance:
#         user_attendance.site_name = site_name
#         if user_attendance.exit_time is not None:
#             flash('Please close the current attendance record before submitting another exit.', 'warning')
#         else:
#             # Get exit location
#             try:
#                 exit_location = geoLoc.reverse(f"{latitude}, {longitude}")
#                 exit_address = exit_location.address if exit_location else "Unknown"
#             except Exception as e:
#                 print(f"Error fetching exit location: {str(e)}")
#                 exit_address = "Unknown"

#             def is_second_or_fourth_saturday(date):
#                 first_day_of_month = date.replace(day=1)
#                 first_day_weekday = first_day_of_month.weekday()
#                 first_saturday = first_day_of_month + timedelta(days=(5 - first_day_weekday) % 7)
#                 second_saturday = first_saturday + timedelta(days=7)
#                 fourth_saturday = first_saturday + timedelta(days=21)

#                 return date == second_saturday or date == fourth_saturday

#             def is_holiday(date):
#                 return date.weekday() == 6 or is_second_or_fourth_saturday(date)

#             if request.form.get('holiday') and user_attendance.exit_location != user_attendance.entry_location:
#                 user_attendance.hol = 10000
#             current_date = datetime.now(india_tz).date()
#             holiday = Holiday.query.filter_by(date=current_date).first()
#             if holiday:
#                 user_attendance.hol = 10000
#             if is_holiday(current_date):
#                 user_attendance.hol = 10000
#             user_attendance.exit_time = now.replace(microsecond=0) # Store only time
#             user_attendance.exit_location = exit_address
#             if user_attendance.exit_location != user_attendance.entry_location:
#                 user_attendance.compoff = 0
#             else:
#                 user_attendance.calculate_comp_off()  # Ensure this method exists and works as intended


#     try:
#         db.session.commit()
#         return redirect(url_for('views.home'))
#     except Exception as e:
#         print(e)
#         flash('There was an issue submitting your attendance.', 'error')
#         return redirect(url_for('views.home'))

# @views.route('/all', methods=['GET'])
# def all():
#     try:
#         user = User.query.all()
#         role = [user.role for user in User.query.all()]
#         emails = [user.email for user in User.query.all()]  # Fetch all emails from the database
#         return render_template('all.html', emails=emails, user = user, role = role)
#     except Exception as e:
#         return str(e)

# @views.route('/attendance_table')
# @login_required
# def attendance_table():
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
#         flash("You do not have permission to view this page.", category='error')
#         return redirect(url_for('views.home'))

#     attendances = Attendance.query.all()


#     return render_template('attendance_table.html', attendances=attendances)

# from datetime import time
# def convert_to_str(time_obj):
#         if isinstance(time_obj, time):
#             return time_obj.strftime("%H:%M")
#         elif time_obj is None:
#             return None
#         return time_obj

# def is_late(entry_time, ideal_entry="09:30"):
#         entry_time = convert_to_str(entry_time)
#         entry = datetime.strptime(entry_time, "%H:%M")
#         ideal = datetime.strptime(ideal_entry, "%H:%M")
#         return entry > ideal

# @views.route('/who_output', methods=['POST'])
# @login_required
# def who_output():
#     name = request.form.get('name')

#     user_attendances = Attendance.query.filter_by(name=name).all()
#     totes = sum(attendance.totes for attendance in user_attendances)
#     late_entries = sum(1 for attendance in user_attendances if is_late(attendance.entry_time))

#     return render_template('who_output.html', attendances=user_attendances, name=name,totes = totes, late_entries = late_entries)


# @views.route('/who', methods=['GET','POST'])
# @login_required
# def who():
#     return render_template('who.html')




# def send_email(subject, recipient, body):
#     msg = Message(subject, recipients=[recipient])
#     msg.body = body
#     mail.send(msg)

# @views.route('/approve_leave/<int:leave_id>', methods=['POST'])
# @login_required
# def approve_leave(leave_id):
#     leave = Leave.query.get(leave_id)
#     if not leave:
#         flash("Leave request not found.", category='error')
#         return redirect(url_for('views.home'))

#     leave.approved = True
#     leave.approved_by = current_user.email
#     db.session.commit()

#     # Get user who requested leave
#     user = User.query.get(leave.user_id)
#     send_email(
#         'Leave Approved',
#         user.email,
#         'Your leave request has been approved.'
#     )

#     return redirect(url_for('views.leave_requests'))

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

#     # Send email
#     send_email(
#         'Leave Rejected',
#         user.email,
#         'Your leave request has been rejected.'
#     )

#     flash("Leave request rejected successfully.", category='success')
#     return redirect(url_for('views.leave_requests'))

# @views.route('/approved_leaves')
# @login_required
# def approved_leaves():
#     approved_leaves = Leave.query.filter_by(user_id=current_user.id, ).all()
#     return render_template('approved_leaves.html', leaves=approved_leaves)

# @views.route('/reset_leaves', methods=['GET', 'POST'])
# @login_required
# def reset_leaves():
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
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

# @views.route('/who1', methods=['GET','POST'])
# @login_required
# def who1():
#     return render_template('who1.html')

# from datetime import date

# @views.route('/who1_output', methods=['POST'])
# @login_required
# def who1_output():
#     name = request.form.get('name')

#     # Get the user based on the name
#     user = User.query.filter_by(first_name=name).first()
#     if not user:
#         flash("User not found.", category='error')
#         return redirect(url_for('views.home'))

#     # Determine the current financial year
#     today = date.today()
#     if today.month >= 4:
#         start_of_fy = date(today.year, 4, 1)
#         end_of_fy = date(today.year + 1, 3, 31)
#     else:
#         start_of_fy = date(today.year - 1, 4, 1)
#         end_of_fy = date(today.year, 3, 31)

#     # Get approved leaves for the user within the current financial year
#     approved_leaves = Leave.query.filter(
#         Leave.user_id == user.id,
#         Leave.approved == True,
#         Leave.start_date >= start_of_fy,
#         Leave.end_date <= end_of_fy
#     ).all()

#     # Initialize sums
#     earned_sum = 0
#     medic_sum = 0
#     pay_sum = 0

#     # Calculate sums for different leave types
#     for leave in approved_leaves:
#         if leave.ltype == 'Earned':
#             earned_sum += leave.days
#         elif leave.ltype == 'Medical/Sick':
#             medic_sum += leave.days
#         elif leave.ltype == 'Leave w/o pay':
#             pay_sum += leave.days

#     return render_template('who1_output.html', user=user, approved_leaves=approved_leaves, earned_sum=earned_sum, medic_sum=medic_sum, pay_sum=pay_sum)




# @views.route('/display_compoff', methods=['GET'])
# @login_required
# def display_compoff():
#     if current_user.email != "sumana@nadiya.in" and current_user.email!= 'maneesh@nadiya.in':
#         flash("You do not have permission to view this page.", category='error')
#         return redirect(url_for('views.home'))

#     # Fetch all users with their total_compoff
#     users = User.query.all()
#     user_compoffs = [{'name': f'{user.first_name}', 'total_compoff': user.total_compoff} for user in users]

#     return render_template('display_compoff.html', user_compoffs=user_compoffs)



# photos = UploadSet('photos', IMAGES)
# docs = UploadSet('docs', ('pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'))

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

# @views.route('/create_user', methods=['GET', 'POST'])
# @login_required

# def create_user():
#     users = User.query.all()
#     return render_template('create_user.html', users=users)

# from flask import abort, current_app


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
#                 user.pay = p_leaves

#             user.probation = is_probation

#             db.session.commit()
#             flash(f'Role {role} assigned to {user.first_name}.', 'success')
#         else:
#             flash('User not found.', 'error')
#         return redirect(url_for('views.assign_roles'))



#     users = User.query.all()

#     return render_template('assign_roles.html', users=users)

# @views.route('/leave_requests')
# @login_required
# def leave_requests():
#     # Check current user's role
#     print(f"Current user's role: {current_user.role}")

#     # Ensure only authorized users can view leave requests
#     if current_user.role == 'director':
#         leave_requests = Leave.query.all()
#     elif current_user.role == 'accounts_manager':
#         # Fetch leave requests for accounts members
#         leave_requests = Leave.query.join(User).filter(User.role == 'accounts_member').all()
#     elif current_user.role == 'business_manager':
#         # Fetch leave requests for business members
#         leave_requests = Leave.query.join(User).filter(User.role == 'business_member').all()
#     elif current_user.role == 'service_manager':
#         # Fetch leave requests for service members
#         leave_requests = Leave.query.join(User).filter(User.role == 'service_member').all()
#     elif current_user.role == 'service_support_manager':
#         # Fetch leave requests for service support members
#         leave_requests = Leave.query.join(User).filter(User.role == 'service_support_member').all()
#     elif current_user.role == 'sales_manager':
#         # Fetch leave requests for sales members
#         leave_requests = Leave.query.join(User).filter(User.role == 'sales_member').all()
#     elif current_user.role == 'service_member':
#         leave_requests = Leave.query.join(User).filter(User.role == 'service_emp').all()
#     else:
#         flash("You do not have permission to view leave requests.", category='error')
#         return redirect(url_for('views.home'))

#     return render_template('leave_requests.html', leave_requests=leave_requests)




# # ROLES = {
# #    'director': ['maneesh@nadiya.in', 'support@nadiya.in', 'sumana@nadiya.in', 'maneesh@nadiya.in' ],
# #     'accounts_manager': ['maneesh@nadiya.in', 'support@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in'  ],
# #     'business_manager': ['maneesh@nadiya.in', 'support@nadiya.in', 'sumana@nadiya.in', 'maneesh@nadiya.in' ],
# #     'service_manager':['maneesh@nadiya.in', 'support@nadiya.in' , 'sumana@nadiya.in', 'maneesh@nadiya.in'],
# #     'service_support_manager': ['maneesh@nadiya.in', 'support@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in' ],
# #     'sales_manager': ['maneesh@nadiya.in', 'support@nadiya.in' , 'sumana@nadiya.in','maneesh@nadiya.in' ],
# #     'others': ['maneesh@nadiya.in', 'support@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in'  ],
# #     #
# #     'accounts_member': ['sumana@nadiya.in','maneesh@nadiya.in', 'support@nadiya.in','maneesh@nadiya.in' ],
# #     'business_member': ['maneesh@nadiya.in', 'support@nadiya.in','bhanuprakash@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in' ],
# #     'service_member': ['maneesh@nadiya.in', 'support@nadiya.in','service_manager@gmail.com', 'sumana@nadiya.in','maneesh@nadiya.in' ],
# #     'service_support_member': ['maneesh@nadiya.in', 'support@nadiya.in','gibin@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in' ],
# #     'sales_member': ['maneesh@nadiya.in', 'support@nadiya.in','nivedita@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in' ],
# #     'service_emp' : ['maneesh@nadiya.in', 'support@nadiya.in','salessupport@nadiya.in', 'sumana@nadiya.in','maneesh@nadiya.in' ]
# # }
# ROLES_HEIRARCHY = {
#     'accounts_member': ['accounts_manager', 'director'],
#     'business_member': ['business_manager', 'director', 'accounts_manager'],
#     'service_member': ['service_manager', 'director', 'accounts_manager'],
#     'service_support_member': ['service_support_manager', 'director', 'accounts_manager'],
#     'sales_member': ['sales_manager', 'director', 'accounts_manager'],
#     'service_emp': ['service_manager', 'director', 'accounts_manager'],
  

#     # Optional: escalate further
#     'accounts_manager': 'director',
#     'business_manager': ['director', 'accounts_manager'],
#     'service_manager': ['director', 'accounts_manager'],
#     'service_support_manager': ['director', 'accounts_manager'],
#     'sales_manager': ['director', 'accounts_manager'],
# }


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
#                 if attendance.compoff > days:
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

#         # Get manager role based on user's role
#         manager_role = ROLES_HEIRARCHY.get(current_user.role)
        
#         if not manager_role:
#             flash("Your role does not have an assigned manager.", 'error')
#             return redirect(url_for('views.apply_leave'))

#         # Get manager user(s) by role
#         managers = User.query.filter_by(role=manager_role).all()
#         if not managers:
#             flash("No manager found for your role.", 'error')
#             return redirect(url_for('views.apply_leave'))

#         # Collect their email addresses
#         recipient_emails = [manager.email for manager in managers if manager.email]
#         approval_url = url_for('views.approve_leave', leave_id=new_leave.id, _external=True)

#         # Ensure recipient_emails is a list of strings
#         if isinstance(recipient_emails, str):
#             recipient_emails = [recipient_emails]
#         elif not isinstance(recipient_emails, list):
#             recipient_emails = [str(recipient_emails)]

#         # Debug: Print recipients to ensure they are correct
#         print(f"Recipients: {recipient_emails}")

#         # Send email to the role manager
#         msg = Message('New Leave Application',

#                       recipients=recipient_emails)
#         msg.body = (
#     f'{current_user.first_name} has applied for leave.\n\n'
#     f'Type: {ltype}\n'
#     f'Start Date: {start_date}\n'
#     f'End Date: {end_date}\n'
#     f'Days: {days}\n'
#     f'Reason: {reason}\n\n'
#     f'Click here to review/approve: {approval_url}'
# )

#         try:
#             mail.send(msg)
#             flash('Leave application submitted successfully.', 'success')
#         except Exception as e:
#             print(f"Failed to send mail: {e}")
#             flash('Failed to send leave application.', 'error')

#         return redirect(url_for('views.apply_leave'))

#     return render_template('apply_leave.html', user=current_user, today=datetime.today().date())

# @views.route('/set_holidays', methods=['GET', 'POST'])
# @login_required
# def set_holidays():
#     if request.method == 'POST':
#         for i in range(20):
#             name = request.form.get(f'holiday_name_{i}')
#             date_str = request.form.get(f'holiday_date_{i}')

#             if name and date_str:
#                 try:
#                     # Convert string to date object
#                     date = datetime.strptime(date_str, '%Y-%m-%d').date()
#                     new_holiday = Holiday(name=name, date=date)
#                     db.session.add(new_holiday)
#                 except ValueError:
#                     # Handle invalid date formats if necessary
#                     pass

#         db.session.commit()
#         return redirect(url_for('views.display_holidays'))

#     return render_template('set_holidays.html')

# @views.route('/display_holidays')
# @login_required
# def display_holidays():
#     holidays = Holiday.query.all()
#     return render_template('display_holidays.html', holidays=holidays)


# @views.route('/delete_holiday/<int:holiday_id>', methods=['POST'])
# @login_required
# def delete_holiday(holiday_id):

#     confirmation_id = request.form.get('confirmation_id')
#     if confirmation_id != '24':
#         flash('Incorrect confirmation ID', 'error')
#         return redirect(url_for('views.list_holidays'))

#     holiday = Holiday.query.get(holiday_id)
#     if holiday:
#         db.session.delete(holiday)
#         db.session.commit()
#         flash('Holiday deleted successfully', 'success')
#     else:
#         flash('Holiday not found', 'error')

#     return redirect(url_for('views.display_holidays'))


# @views.route('/delete/<email>', methods=['DELETE'])
# def delete_email(email):
#     user = User.query.filter_by(email=email).first()

#     if user:
#         # Delete related records in other tables
#         try:
#             User.query.filter_by(user_id=user.id).delete()
#             Document.query.filter_by(user_id=user.id).delete()
#             Attendance.query.filter_by(user_id=user.id).delete()
#             Leave.query.filter_by(user_id=user.id).delete()
#             Holiday.query.filter_by(user_id=user.id).delete()

#             # Delete the user itself

#             db.session.commit()

#             return jsonify({'message': f'User {email} and related records deleted successfully'}), 200
#         except Exception as e:
#             db.session.rollback()
#             return jsonify({'error': str(e)}), 500
#     else:
#         return jsonify({'error': f'User with email {email} not found'}), 404

# @views.route('/delete_user/<int:user_id>')
# def delete_user(user_id):
#     print(f"Attempting to delete user with ID: {user_id}")

#     user = User.query.get_or_404(user_id)
#     print(f"Found user: {user}")

#     Document.query.filter_by(user_id=user_id).delete()
#     Attendance.query.filter_by(user_id=user_id).delete()
#     Leave.query.filter_by(user_id=user_id).delete()


#     db.session.delete(user)
#     db.session.commit()

#     return redirect(url_for('views.all'))

# @views.route('/announcements')
# def announcements():
#     # Fetch announcements from the database
#     announcements = Announcement.query.all()
#     return render_template('announcements.html', announcements=announcements)



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



# @views.route('/delete_announcement/<int:announcement_id>', methods=['POST'])
# @login_required
# def delete_announcement(announcement_id):
#     confirmation_id = request.form.get('confirmation_id')
#     if (current_user.email == "sumana@nadiya.in" or current_user.email == "maneesh@nadiya.in") and confirmation_id == '24':


#         announcement = Announcement.query.get(announcement_id)
#         if announcement:
#             db.session.delete(announcement)
#             db.session.commit()
#             flash('Announcement deleted successfully', 'success')
#         else:
#             flash('Announcement not found', 'danger')
#     else:
#         flash('Invalid confirmation ID or insufficient permissions', 'danger')
#     return redirect(url_for('views.announcements'))

# @views.route('/add_compoff', methods=['GET', 'POST'])
# @login_required
# def add_compoff():
#     users = User.query.all()  # Retrieve all users from the database

#     if request.method == 'POST':
#         user_id = request.form['user_id']
#         compoff_amount = float(request.form['compoff_amount'])

#         # Find the user by ID
#         user = User.query.get(user_id)
#         if not user:
#             flash("User not found.", category='error')
#             return redirect(url_for('views.add_compoff'))

#         # Find the user's attendance records
#         user_attendances = Attendance.query.filter_by(user_id=user.id).all()

#         if not user_attendances:
#             flash("No attendance records found for the user.", category='error')
#             return redirect(url_for('views.add_compoff'))

#         # Add compoff to the first attendance record
#         updated = False
#         for attendance in user_attendances:
#             attendance.compoff += compoff_amount
#             db.session.commit()
#             updated = True
#             break

#         if not updated:
#             flash("No eligible attendance records found to add compoff.", category='error')
#         else:
#             flash(f'Compoff added successfully to attendance record for {user.email}.', category='success')

#         return redirect(url_for('views.home'))

#     return render_template('add_compoff.html', users=users)


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

# @views.route('/subtract-holidays', methods=['GET'])
# def show_subtract_holidays_form():
#     users = User.query.all()  # Fetch all users
#     user = current_user
#     return render_template('subtract_holidays.html', users=users, user = user)

# @views.route('/subtract-holidays', methods=['POST'])
# def subtract_holidays():
#     username = request.form.get('username')
#     leave_type = request.form.get('leave_type')
#     num_days = int(request.form.get('num_days'))

#     user = User.query.get(username)  # Get the user by ID

#     if leave_type == 'earned':
#         if user.earned >= num_days:
#             user.earned -= num_days
#         else:
#             flash('Not enough earned leave days.', category='error')
#     elif leave_type == 'medic':
#         if user.medic >= num_days:
#             user.medic -= num_days
#         else:
#             flash('Not enough medic leave days.', category='error')
#     elif leave_type == 'pay':
#         if user.pay >= num_days:
#             user.pay -= num_days
#         else:
#             flash('Not enough pay leave days.', category='error')
#     else:
#         flash('Invalid leave type.', category='error')
#         return redirect(url_for('views.show_subtract_holidays_form'))

#     db.session.commit()
#     flash('Leave days edited successfully.', category='success')
#     return redirect(url_for('views.show_subtract_holidays_form'))

# @views.route('/export', methods=['POST' , 'GET'])
# @login_required
# def export_all_data():
#     output = BytesIO()

#     # Create an ExcelWriter to write multiple DataFrames to separate sheets
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         # Map of table names to SQLAlchemy models
#         tables = {
#             'Users': User,
#             'Documents': Document,
#             'Attendance': Attendance,
#             'Leaves': Leave,
#             'Holidays': Holiday,
#             'Announcements': Announcement
#         }

#         for sheet_name, model in tables.items():
#             # Query all records from the table
#             query = model.query.all()

#             # Convert SQLAlchemy objects to dicts
#             data = [item.__dict__.copy() for item in query]

#             # Remove private fields (like _sa_instance_state)
#             for row in data:
#                 row.pop('_sa_instance_state', None)

#             # Convert to DataFrame and write to sheet
#             df = pd.DataFrame(data)
#             df.to_excel(writer, sheet_name=sheet_name[:31], index=False)  # Excel sheet names must be <=31 chars

#     output.seek(0)

#     return send_file(
#         output,
#         as_attachment=True,
#         download_name="all_data_export.xlsx",
#         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#     )
