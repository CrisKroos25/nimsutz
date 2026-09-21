# files/admin.py
from django.contrib import admin
from .models import Folder, File, QuotaReservation

admin.site.register(Folder)
admin.site.register(File)
admin.site.register(QuotaReservation)