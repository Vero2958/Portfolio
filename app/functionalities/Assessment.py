# this is the form that gets shown whenever the user wants to take an assessment.
import datetime

from app.user import User


class Assessment:
    issue = User.user[0].issue
    Assessments = []

    def __init__(self):
        self.date = datetime.datetime.today()
        if Assessment.issue == "ADHD":
            pass
        elif Assessment.issue == "anxiety":
            pass
        else:
            pass
        Assessment.Assessments.append(self)