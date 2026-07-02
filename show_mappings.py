#!/usr/bin/env python
"""
Script to display Employee-Manager mappings in a clear format
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from users.models import UserProfile
from django.contrib.auth.models import User

print("\n" + "="*80)
print("EMPLOYEE-MANAGER MAPPING REPORT")
print("="*80 + "\n")

# Get all managers
managers = UserProfile.objects.filter(role='MANAGER').select_related('user')
print(f"📊 TOTAL MANAGERS: {managers.count()}\n")

for manager_profile in managers:
    manager = manager_profile.user
    managed = UserProfile.objects.filter(manager=manager).select_related('user')
    
    print(f"👔 Manager: {manager.username.upper()}")
    print(f"   └─ ID: {manager.id}")
    print(f"   └─ Managed Employees: {managed.count()}")
    
    if managed.exists():
        for emp_profile in managed:
            emp = emp_profile.user
            print(f"      ├─ 👤 {emp.username} (ID: {emp.id})")
    else:
        print(f"      └─ No employees assigned yet")
    print()

# Get unassigned employees
print("\n" + "-"*80)
print("🚫 UNASSIGNED EMPLOYEES (No Manager):\n")
unassigned = UserProfile.objects.filter(role='EMPLOYEE', manager__isnull=True).select_related('user')
if unassigned.exists():
    for emp_profile in unassigned:
        emp = emp_profile.user
        print(f"   👤 {emp.username} (ID: {emp.id})")
else:
    print("   ✓ All employees are assigned!")

print("\n" + "="*80)
print("SUMMARY:")
print("="*80)
print(f"Total Users: {User.objects.count()}")
print(f"Total Profiles: {UserProfile.objects.count()}")
print(f"  - Managers: {UserProfile.objects.filter(role='MANAGER').count()}")
print(f"  - Employees: {UserProfile.objects.filter(role='EMPLOYEE').count()}")
print(f"  - Assigned Employees: {UserProfile.objects.filter(role='EMPLOYEE', manager__isnull=False).count()}")
print(f"  - Unassigned Employees: {UserProfile.objects.filter(role='EMPLOYEE', manager__isnull=True).count()}")
print("="*80 + "\n")
