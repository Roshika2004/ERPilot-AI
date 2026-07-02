#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from users.models import UserProfile
from django.contrib.auth.models import User

print("\n=== CURRENT USER ROLES ===\n")
for profile in UserProfile.objects.select_related('user').order_by('role'):
    user = profile.user
    manager_name = profile.manager.username if profile.manager else "None"
    print(f"ID: {profile.id} | Username: {user.username:12} | Role: {profile.role:8} | Manager: {manager_name}")

# Count summary
managers = UserProfile.objects.filter(role='MANAGER').count()
employees = UserProfile.objects.filter(role='EMPLOYEE').count()
print(f"\n✓ Total Managers: {managers}")
print(f"✓ Total Employees: {employees}")
