#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from users.models import UserProfile
from django.contrib.auth.models import User

print("\n" + "="*60)
print("CURRENT DATABASE STATE - Users and Roles")
print("="*60 + "\n")

for profile in UserProfile.objects.select_related('user').order_by('id'):
    user = profile.user
    print(f"ID: {profile.id} | User: {user.username:15} | Role: {profile.role:8} | Created: {user.date_joined.date()}")

print(f"\nTotal Users: {User.objects.count()}")
print(f"Total Profiles: {UserProfile.objects.count()}")
print(f"  - Managers: {UserProfile.objects.filter(role='MANAGER').count()}")
print(f"  - Employees: {UserProfile.objects.filter(role='EMPLOYEE').count()}")
print("\n" + "="*60)
