#!/usr/bin/env python
"""
Script to create default admin user for the system
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'erpilot.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserProfile

print("\n" + "="*80)
print("🔧 SETTING UP DEFAULT ADMIN USER")
print("="*80 + "\n")

# Check if admin already exists
admin_user = User.objects.filter(username='admin').first()

if admin_user:
    print("✓ Admin user already exists!")
    print(f"   Username: admin")
    print(f"   Email: {admin_user.email}")
    
    # Check if profile exists
    admin_profile = UserProfile.objects.filter(user=admin_user).first()
    if admin_profile:
        print(f"   Role: {admin_profile.role}\n")
        if admin_profile.role != 'ADMIN':
            # Update profile to ADMIN if it's not already
            admin_profile.role = 'ADMIN'
            admin_profile.save()
            print("   ✓ Updated profile to ADMIN role\n")
    else:
        # Create profile if it doesn't exist
        UserProfile.objects.create(
            user=admin_user,
            role='ADMIN'
        )
        print("   ✓ Created missing admin profile\n")
else:
    # Create admin user
    admin = User.objects.create_user(
        username='admin',
        email='admin@example.com',
        password='admin123',
        first_name='Admin',
        last_name='User'
    )
    
    # Create admin profile
    UserProfile.objects.create(
        user=admin,
        role='ADMIN'
    )
    
    print("✓ ADMIN USER CREATED!\n")

print("="*80)
print("LOGIN CREDENTIALS:")
print("="*80)
print(f"   Username: admin")
print(f"   Password: admin123")
print(f"   Email: admin@example.com")
print(f"   Role: ADMIN\n")
print("="*80)
print("FEATURES:")
print("="*80)
print("""
   ✓ View all users (Admins, Managers, Employees)
   ✓ Assign managers to employees
   ✓ Remove manager assignments
   ✓ Manage all users
   ✓ View system statistics
   """)

# Display current stats
print("\n" + "="*80)
print("CURRENT DATABASE STATISTICS:")
print("="*80)
admins = UserProfile.objects.filter(role='ADMIN').count()
managers = UserProfile.objects.filter(role='MANAGER').count()
employees = UserProfile.objects.filter(role='EMPLOYEE').count()
total = User.objects.count()

print(f"\n   Total Users: {total}")
print(f"   - Admins: {admins}")
print(f"   - Managers: {managers}")
print(f"   - Employees: {employees}\n")
