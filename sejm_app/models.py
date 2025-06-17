from django.db import models

class Member(models.Model):
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    club = models.CharField(max_length=50, null=True, blank=True)
    district_name = models.CharField(max_length=50, null=True, blank=True)
    district_num = models.IntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    voivodeship = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'parliament"."members'
        app_label = 'sejm_app'

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Voting(models.Model):
    abstain = models.IntegerField(null=True, blank=True)
    date = models.DateTimeField(null=True, blank=True)
    kind = models.CharField(max_length=50, null=True, blank=True)
    links = models.JSONField(null=True, blank=True)
    majority_type = models.CharField(max_length=50, null=True, blank=True)
    majority_votes = models.IntegerField(null=True, blank=True)
    no = models.IntegerField(null=True, blank=True)
    not_participating = models.IntegerField(null=True, blank=True)
    present = models.IntegerField(null=True, blank=True)
    sitting = models.IntegerField(null=True, blank=True)
    sitting_day = models.IntegerField(null=True, blank=True)
    term = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=200, null=True, blank=True)
    topic = models.CharField(max_length=200, null=True, blank=True)
    total_voted = models.IntegerField(null=True, blank=True)
    voting_number = models.IntegerField(null=True, blank=True)
    yes = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'parliament"."votings'
        app_label = 'sejm_app'

    def __str__(self):
        return f"Voting {self.voting_number}: {self.title}"