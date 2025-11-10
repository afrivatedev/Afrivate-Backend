from django.contrib import admin
from .models import CustomUser, OtpToken

# Register your models here.

admin.site.register(CustomUser)
admin.site.register(OtpToken)