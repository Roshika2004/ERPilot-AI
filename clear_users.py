#!/usr/bin/env python
"""
Script to clear all existing users from database
WARNING: This will delete all users, profiles, and related data!
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile

print("\n" + "="*80)
print("⚠️  WARNING: This will DELETE ALL USERS from the database!")
print("="*80 + "\n")

confirm = input("Type 'DELETE ALL' to confirm: ").strip()

if confirm == 'DELETE ALL':
    print("\n🗑️  Deleting all users and profiles...\n")
    
    # Get count before deletion
    user_count = User.objects.count()
    profile_count = UserProfile.objects.count()
    
    # Delete all users (profiles will cascade delete)
    User.objects.all().delete()
    
    print(f"✓ Deleted {user_count} users")
    print(f"✓ Deleted {profile_count} profiles")
    
    print("\n" + "="*80)
    print("✓ Database cleared successfully!")
    print("="*80 + "\n")
    print(f"Remaining users: {User.objects.count()}")
    print(f"Remaining profiles: {UserProfile.objects.count()}\n")
else:
    print("\n❌ Deletion cancelled.\n")
