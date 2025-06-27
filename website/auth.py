from flask import Blueprint, render_template, request, flash, redirect, url_for
from .models import User
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, oauth   ##means from __init__.py import db
from flask_login import login_user, login_required, logout_user, current_user
from leave_calculator import calculate_initial_leaves
from datetime import datetime


auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.home'))
            else:
                flash('Incorrect password, try again.', category='error')
        else:
            flash('Email does not exist.', category='error')

    return render_template("login.html", user=current_user)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# @auth.route('/sign-up', methods=['GET', 'POST'])
# def sign_up():
    
#     if request.method == 'POST':
#         email = request.form.get('email')
#         first_name = request.form.get('firstName')
#         password1 = request.form.get('password1')
#         password2 = request.form.get('password2')

#         user = User.query.filter_by(email=email).first()
#         if user:
#             flash('Email already exists.', category='error')
#         elif len(email) < 4:
#             flash('Email must be greater than 3 characters.', category='error')
#         elif len(first_name) < 2:
#             flash('First name must be greater than 1 character.', category='error')
#         elif password1 != password2:
#             flash('Passwords don\'t match.', category='error')
#         elif len(password1) < 1:
#             flash('Password must be at least 7 characters.', category='error')
#         else:
#             new_user = User(email=email, first_name=first_name, password=generate_password_hash(
#                 password1, method='scrypt'))
#             db.session.add(new_user)
#             db.session.commit()
#             login_user(new_user, remember=True)
#             for leave in current_user.leaves:
#                 leave.medic = 0
#                 leave.earned = 0
#                 leave.pay = 0 
#             flash('Account created!', category='success')
#             return redirect(url_for('views.home'))

#     return render_template("sign_up.html", user=current_user)

# @auth.route('/sign-up', methods=['GET', 'POST'])
# def sign_up():
#     user_count = User.query.count()

#     # ✅ Step 1: Block non-admins from even seeing the form once the first user is created
#     if user_count > 0:
#         if not current_user.is_authenticated:
#             flash('Sign-up is restricted. Please contact the administrator.', 'error')
#             return redirect(url_for('auth.login'))
#         elif current_user.email != 'sumana@nadiya.in':
#             flash('Only the admin can create new accounts.', 'error')
#             return redirect(url_for('views.home'))

#     if request.method == 'POST':
#         email = request.form.get('email')
#         first_name = request.form.get('firstName')
#         password1 = request.form.get('password1')
#         password2 = request.form.get('password2')

#         user = User.query.filter_by(email=email).first()
#         if user:
#             flash('Email already exists.', category='error')
#         elif len(email) < 4:
#             flash('Email must be greater than 3 characters.', category='error')
#         elif len(first_name) < 2:
#             flash('First name must be greater than 1 character.', category='error')
#         elif password1 != password2:
#             flash('Passwords don\'t match.', category='error')
#         elif len(password1) < 7:
#             flash('Password must be at least 7 characters.', category='error')
#         else:
#             new_user = User(
#                 email=email,
#                 first_name=first_name,
#                 password=generate_password_hash(password1, method='scrypt')
#             )
#             db.session.add(new_user)
#             db.session.commit()

#             flash('Account created successfully.', category='success')

#             # Only log in the first ever user
#             if user_count == 0:
#                 login_user(new_user, remember=True)

#             return redirect(url_for('auth.login'))

#     return render_template("sign_up.html", user=current_user)



@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    user_count = User.query.count()

    # Only allow admin to create new users after the first one
    if user_count > 0:
        if not current_user.is_authenticated or current_user.email != 'sumana@nadiya.in':
            flash('Only the admin can create new accounts.', category='error')
            return redirect(url_for('views.home'))

    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', category='error')
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='error')
        elif len(first_name) < 2:
            flash('First name must be greater than 1 character.', category='error')
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
        elif len(password1) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            joining_date = datetime.today()
            leave_balances = calculate_initial_leaves(joining_date, is_probation=False)

            new_user = User(
                email=email,
                first_name=first_name,
                password=generate_password_hash(password1, method='scrypt'),
                joining_date=joining_date,
                earned=leave_balances['earned'],
                medic=leave_balances['medic'],
                pay=leave_balances['pay'],
                probation=False  # Default to permanent
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully.', category='success')

            if user_count == 0:
                login_user(new_user, remember=True)

            return redirect(url_for('views.home'))

    return render_template("sign_up.html", user=current_user)

# --- Google OAuth Login ---

@auth.route('/login/google')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    print("Redirect URI being used:", redirect_uri) 
    return oauth.google.authorize_redirect(redirect_uri)


# @auth.route('/login/google/callback')
# def google_callback():
#     google = oauth.create_client('google')
#     token = oauth.google.authorize_access_token()
#     if google.token.is_expired():
#         new_token = google.refresh_token(
#             url='https://oauth2.googleapis.com/token',
#             client_id=google.client_id,
#             client_secret=google.client_secret
#         )
#         token = new_token
    
#     user_info = token.get('userinfo') or oauth.google.parse_id_token(token, nonce=None)
#     print("User info received:", user_info)  # Debugging line to check user info
    
#     if user_info is None:
#         flash("Failed to authenticate with Google.", "error")
#         return redirect(url_for('auth.login'))
    
#     email = user_info.get('email')
#     first_name = user_info.get('given_name', '')

#     # Check if user exists, else create new
#     user = User.query.filter_by(email=email).first()
#     # if not user:
#     #     user = User(email=email, first_name=first_name, password='')  # No password for OAuth users
#     #     db.session.add(user)
#     #     db.session.commit()
#     if not user:
#         flash("Access denied: Your account is not registered in the system.", "error")
#         return redirect(url_for('auth.login'))

#     login_user(user, remember=True)
#     flash('Logged in successfully with Google!', 'success')
#     return redirect(url_for('views.home'))

@auth.route('/login/google/callback')
def google_callback():
    google = oauth.create_client('google')
    token = oauth.google.authorize_access_token()
    if google.token.is_expired():
        new_token = google.refresh_token(
            url='https://oauth2.googleapis.com/token',
            client_id=google.client_id,
            client_secret=google.client_secret
        )
        token = new_token

    user_info = token.get('userinfo') or oauth.google.parse_id_token(token, nonce=None)
    print("User info received:", user_info)

    if user_info is None:
        flash("Failed to authenticate with Google.", "error")
        return redirect(url_for('auth.login'))

    email = user_info.get('email')
    
    # Block if email is not from @nadiya.in
    if not email.endswith("@nadiya.in"):
        flash("Access denied: Only @nadiya.in email addresses are allowed.", "error")
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Access denied: Your account is not registered in the system.", "error")
        return redirect(url_for('auth.login'))

    login_user(user, remember=True)
    flash('Logged in successfully with Google!', 'success')
    return redirect(url_for('views.home'))
