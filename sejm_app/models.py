from django.db import models
from django.db.models import JSONField

class Member(models.Model):
    sejm_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
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
        return f"{self.first_name} {self.last_name} ({self.club})"

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
        unique_together = ('voting_number', 'sitting_day', 'term')
        db_table = 'parliament"."votings' 
        app_label = 'sejm_app'

    def __str__(self):
        return f"Voting {self.voting_number}/{self.sitting_day} - {self.title}"
    

class Vote(models.Model):
    # Relacja do konkretnego głosowania
    voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name='individual_votes')
    # Relacja do posła
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='member_votes', null=True, blank=True)
    # Pole MP jest unikalnym ID z API posłów. Jeśli poseł nie zostanie znaleziony, zapiszemy MP ID z API
    mp_id_api = models.IntegerField(null=True, blank=True) # Unikalne ID posła z API, jeśli nie mamy go w bazie
    first_name = models.CharField(max_length=100, null=True, blank=True) # Zachowujemy na wypadek braku posła
    last_name = models.CharField(max_length=100, null=True, blank=True)
    club = models.CharField(max_length=100, null=True, blank=True)
    vote_choice = models.CharField(
        max_length=20,
        choices=[
            ('YES', 'Za'),
            ('NO', 'Przeciw'),
            ('ABSTAIN', 'Wstrzymał się'),
            ('NOT_PARTICIPATING', 'Nie brał udziału'), # Opcjonalne, jeśli to ma sens
        ]
    )

    class Meta:
        # Jeden poseł może głosować raz w danym głosowaniu
        unique_together = ('voting', 'member')
        db_table = 'parliament"."individual_votes' # Nazwa tabeli dla głosów indywidualnych
        app_label = 'sejm_app'

    def __str__(self):
        return f"{self.member or self.first_name + ' ' + self.last_name} głosował {self.vote_choice} w {self.voting}"