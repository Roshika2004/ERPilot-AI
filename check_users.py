#!/usr/bin/env python
"""
Script to check current users and create default test users for demonstration
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile

print("\n" + "="*80)
print("CURRENT USERS IN DATABASE")
print("="*80 + "\n")

users = User.objects.all()
if users.count() == 0:
    print("⚠️  No users found in database!")
else:
    for user in users:
        try:
            profile = UserProfile.objects.get(user=user)
            manager = profile.manager.username if profile.manager else "Not Assigned"
            print(f"✓ {user.username:20} | Role: {profile.role:10} | Manager: {manager}")
        except UserProfile.DoesNotExist:
            print(f"⚠ {user.username:20} | NO PROFILE")

print(f"\n📊 STATISTICS:")
print(f"   Total Users: {User.objects.count()}")
print(f"   Total Managers: {UserProfile.objects.filter(role='MANAGER').count()}")
print(f"   Total Employees: {UserProfile.objects.filter(role='EMPLOYEE').count()}")

print("\n" + "="*80)
print("DEFAULT TEST USERS (Ready to create if needed)")
print("="*80 + "\n")

test_users = [
    {"username": "manager1", "email": "manager1@example.com", "password": "manager123", "role": "MANAGER", "first_name": "John", "last_name": "Manager"},
    {"username": "manager2", "email": "manager2@example.com", "password": "manager123", "role": "MANAGER", "first_name": "Sarah", "last_name": "Manager"},
    {"username": "emp1", "email": "emp1@example.com", "password": "emp123", "role": "EMPLOYEE", "first_name": "Alice", "last_name": "Employee"},
    {"username": "emp2", "email": "emp2@example.com", "password": "emp123", "role": "EMPLOYEE", "first_name": "Bob", "last_name": "Employee"},
    {"username": "emp3", "email": "emp3@example.com", "password": "emp123", "role": "EMPLOYEE", "first_name": "Charlie", "last_name": "Employee"},
    {"username": "emp4", "email": "emp4@example.com", "password": "emp123", "role": "EMPLOYEE", "first_name": "Diana", "last_name": "Employee"},
    {"username": "emp5", "email": "emp5@example.com", "password": "emp123", "role": "EMPLOYEE", "first_name": "Eve", "last_name": "Employee"},
]

print("Available test users:\n")
for i, user_data in enumerate(test_users, 1):
    role_badge = "👔 MANAGER" if user_data["role"] == "MANAGER" else "👤 EMPLOYEE"
    print(f"{i}. {role_badge:15} | {user_data['username']:12} | {user_data['email']}")
    print(f"   Password: {user_data['password']}")
    print()
