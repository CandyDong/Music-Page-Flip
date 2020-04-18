from django.contrib import admin
from .models import Profile, RPI, Score, FlipSession

admin.site.register(RPI)
admin.site.register(Score)
admin.site.register(Profile)
admin.site.register(FlipSession)
