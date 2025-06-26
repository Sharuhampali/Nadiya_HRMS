from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_initial_leaves(joining_date, is_probation):
   

    if is_probation:
        return {
            "earned": 0,
            "medic": 0,
            "pay": 10
        }
    else:
        return {
            "earned": 15,
            "medic":6,
            "pay":10
        }
