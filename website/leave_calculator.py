from .models import User
from flask_login import current_user
from . import db

user = current_user
def calculate_initial_leaves(joining_date, is_probation=False):
 
   
    if user.probation:
        user.earned = 0
        user.medic = 0
        user.pay = 10 
    else:
        user.earned = 15 
        user.medic = 6 
        user.pay = 10

    db.session.commit()