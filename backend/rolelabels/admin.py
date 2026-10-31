from django.contrib import admin

from .models import RoleLabel, UserRoleLabel

admin.site.register(RoleLabel)
admin.site.register(UserRoleLabel)
