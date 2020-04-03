from django.db import models
from django.contrib.auth.models import User

class Score(models.Model):
    scoreName     = models.CharField(max_length=50)
    pic           = models.FileField(blank=True, default="default.png")
    content_type  = models.CharField(max_length=50)
    def __str__(self):
        return self.scoreName

class Profile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.PROTECT)
    scores        = models.ManyToManyField(Score, symmetrical=False, blank=True)

    def __str__(self):
        return self.user.username

class RPI(models.Model):
    in_use = models.BooleanField(default=False)
    user_profile = models.OneToOneField(Profile, on_delete=models.PROTECT, null=True, blank=True)