from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.PROTECT)

    def __str__(self):
        return self.user.username

class Score(models.Model):
    scoreName     = models.CharField(max_length=50)
    pic           = models.FileField(blank=True, default="default.png")
    path          = models.CharField(max_length=200, null=False, blank=True, default="")
    content_type  = models.CharField(max_length=50)
    user_profile = models.ForeignKey(Profile, on_delete=models.PROTECT, null=True, blank=True)
    def __str__(self):
        return self.scoreName

class RPI(models.Model):
    in_use = models.BooleanField(default=False)
    user_profile = models.OneToOneField(Profile, on_delete=models.PROTECT, null=True, blank=True)