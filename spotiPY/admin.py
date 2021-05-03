from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Account

# Register your models here.
class AccountAdmin(UserAdmin):
    list_display = ("email", "username", "date_joined", "is_admin")
    search_fields = ("email", "username")
    readonly_fields = ("id", "date_joined", "last_login")

    list_filter = ()
    filter_horizontal = ()
    fieldsets = ()


admin.site.register(Account, AccountAdmin)