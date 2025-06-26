from datetime import datetime
from dateutil.relativedelta import relativedelta

def calculate_initial_leaves(joining_date, is_probation):
    if joining_date.month >= 4:
        start_of_year = datetime(joining_date.year, 4, 1)
        end_of_year = datetime(joining_date.year + 1, 3, 31)
    else:
        start_of_year = datetime(joining_date.year - 1, 4, 1)
        end_of_year = datetime(joining_date.year, 3, 31)

    months_left = (end_of_year.year - joining_date.year) * 12 + (end_of_year.month - joining_date.month) - joining_date.day // 30

    if is_probation:
        return {
            "earned": 0,
            "medic": 0,
            "pay": round(10 - (months_left * 10 / 12), 2)
        }
    else:
        return {
            "earned": round(15 - (months_left * 15 / 12), 2),
            "medic": round(6 - (months_left * 6 / 12), 2),
            "pay": round(10 - (months_left * 10 / 12), 2)
        }
