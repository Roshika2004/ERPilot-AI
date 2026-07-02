from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'get_email', 'get_username']
    list_filter = ['role']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['user']
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
