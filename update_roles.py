#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from users.models import UserProfile

# Update the first user to be a MANAGER
profile = UserProfile.objects.first()
profile.role = 'MANAGER'
profile.save()

print(f"Updated {profile.user.username} to MANAGER role")

# Display all profiles
print("\n--- All User Profiles ---")
for p in UserProfile.objects.all():
    print(f"{p.user.username}: {p.role}")
