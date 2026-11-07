import datetime


class Journal:
    Journal_pages = []

    def __init__(self, title, content):
        self.date = datetime.datetime.today()
        self.content = content
        self.title = title
        Journal.Journal_pages.append(self)

    def __str__(self):
        return self.title.upper() + "   " + str(self.date).split(".")[0] + "\n" + self.content

    def update(self):
        to_update = input("what do you want to update? (title/content) ")
        if to_update == "title":
            new_title = input("New title: ").upper()
            self.title = new_title
        else:
            new_content = input("modified content: ")
            self.content = new_content


'''
title = input("Title: ")
content = input("--> ")
page = Journal(title, content)
print(page)
page.update()
print(page)
'''