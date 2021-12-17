import datetime
import typing

def get_default_start_end_date() -> typing.Union[datetime.date, datetime.date]:
    start_datetime = datetime.datetime.today()
    end_datetime = start_datetime + datetime.timedelta(days = 90)

    return (start_datetime.date(), end_datetime.date())

def check_if_current_week(today:datetime.datetime, start_of_week:datetime.datetime):
    end_of_week = start_of_week + datetime.timedelta(days = 6)
    
    if today >= start_of_week and today <= end_of_week:
        return True

    return False

def check_if_today(today:datetime.datetime, d:datetime.datetime, idx:int):
    test_date = d + datetime.timedelta(days = idx)

    return today.date() == test_date.date()