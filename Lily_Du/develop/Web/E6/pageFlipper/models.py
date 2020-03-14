from django.db import models
from django.contrib.auth.models import User

class RPI(models.Model):
    in_use           = models.CharField(blank=True, max_length=200)

    def __str__(self):
        return

class Score(models.Model):
    profile_picture  = models.FileField(blank=True, default="default.png")

    def __str__(self):
        return

class Profile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.PROTECT)
    rpiId         = models.CharField(max_length=50)
    content_type  = models.CharField(max_length=50)
    scores        = models.ManyToManyField(Score, symmetrical=False, blank=True)

    def __str__(self):
        return self.user.username