import datetime


class ADHDTracker:
    def __init__(self, mood, attention, productivity, rsd, hyperactivity_m, hyperactivity_p, energy, impulsivity, concentration):
        self.date = datetime.datetime.today()  # there should be one per day
        self.mood = mood
        self.attention = attention
        self.productivity = productivity
        self.rsd = rsd
        self.hyperactivity_m = hyperactivity_m
        self.hyperactivity_p = hyperactivity_p
        self.energy = energy
        self.impulsivity = impulsivity
        self.concentration = concentration
        self.rate = (self.mood + self.attention + self.productivity + self.rsd + self.hyperactivity_m + self.hyperactivity_p + self.energy + self.impulsivity + self.concentration)/9
        # here you actually need the code to store it in the database as soon as it gets created


class DTracker:  # based on the PHQ-9 depression scale
    def __init__(self, mood, sleep, energy, appetite, self_esteem, concentration, dysfunctional_thoughts, dysfunctional_coping_mechanisms):
        self.date = datetime.datetime.today()
        self.mood = mood
        self.sleep = sleep
        self.energy = energy
        self.appetite = appetite
        self.self_esteem = self_esteem
        self.concentration = concentration
        self.dysfunctional_thoughts = dysfunctional_thoughts
        self.coping_mechanism = dysfunctional_coping_mechanisms
        self.rate = (self.mood + self.sleep + self.energy + self.appetite + self.self_esteem + self.dysfunctional_thoughts + self.coping_mechanism + self.concentration)/8
        # here add the code for the db


class ATracker:
    record = []
    daily_stats = []

    def __init__(self, trigger, reaction, intensity, lasting, thoughts, coping_m):
        self.date = datetime.datetime.today()  # more than one per day is allowed
        self.triggers = trigger  # add cases for commas
        self.reactions = reaction
        self.intensity = intensity
        self.lasting = lasting  # amount of hours the episode lasted
        self.thoughts = thoughts  # summary of thoughts during episodes
        self.coping_mechanisms = coping_m  # how did you cope?
        ATracker.record.append(self)
        # don't forget code for the db

    def day_stats(self, date=datetime.datetime.today()):
        """
        this method creates a summary for the given date, if no date is entered it just uses the current date
        :param date: the date you are considering
        :return:
        """
        today_s = []
        for track in ATracker.record:
            if track.date[:9] == date[:9]:
                today_s.append(track)
        intensities = []
        sum_i = 0
        amount = 0
        for track in today_s:
            amount += 1
            intensities.append(track.intensity)
            sum_i += track.intensity
        average = sum_i/amount
        summary = {"date": date[:9], "amount": amount, "intensities": intensities, "average_intensity": average}
        # add code to add the summary in the db
        str_summary = (f"on {date[:9]}, you've had {amount} anxiety episodes with an average intensity of {average},"
                       f" the most intense was {max(intensities)}/10, the least intense was {min(intensities)}/10")
        ATracker.daily_stats.append(str_summary)