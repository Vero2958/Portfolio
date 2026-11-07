
class User:
    user = []

    def __init__(self, name, issues, medication):
        self.name = name
        if ", " in issues:
            self.issue = issues.split(", ")
        elif "," in issues:
            self.issue = issues.split(",")
        else:
            self.issue = issues.split(" ")
        if medication == "Y":
            self.medications = "Yes"
        else:
            self.medications = "No"
        User.user.append(self)


name = input("what's your name? ")
meds = input("are you under medications? Y/N ")
issues = input("what are you struggling with? (ADHD/depression/anxiety, 1 or more) ")
User = User(name, issues, meds)
print(User.user[0].name, User.user[0].issue, User.user[0].medications)
