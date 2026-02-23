from django.contrib import admin
from .models import Opportunity

# Register your models here.

admin.site.site_header = "Afrivate Admin"
admin.site.site_title = "Afrivate Admin Portal"
admin.site.index_title = "Welcome to the Afrivate Admin Portal"

admin.site.register(Opportunity)
