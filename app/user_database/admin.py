from django.contrib import admin
from user_database import models

# Register your models here.

admin.site.register(models.CustomUser)
admin.site.register(models.EmailVerification)
admin.site.register(models.WaitlistEmail)
