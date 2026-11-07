# Setting deleting and updating Goals
import datetime


class Goal:
    Goals = []

    def __init__(self, desc):
        self.date = datetime.datetime.today()
        self.desc = desc
        self.progress = 0  # this goes from 0 (not started) to 10 (achieved)
        Goal.Goals.append(self)

    def __str__(self):
        if self in Goal.Goals:
            return str(self.date).split(".")[0] + " " + self.desc + " " + str(self.progress)
        else:
            return "Goal was removed"

    def update(self):
        to_update = input("what do you want to update? (desc/progress)")
        if to_update == "desc" or " desc":
            new_desc = input("insert new description: ")
            self.desc = new_desc
        else:
            updated_progress = input("what is the current progress? ")
            self.progress = updated_progress

    def delete(self):
        confirmation = input("are you sure you want to delete this goal? (Y/N)")
        if confirmation == "Y" or " Y":
            Goal.Goals.remove(self)
            print("goal was removed")


'''
goal = Goal("programming assignment")
print(goal)
goal.update()
print(goal)
goal.delete()
print(goal)
'''