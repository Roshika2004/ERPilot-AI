from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Count
from users.models import UserProfile


class Command(BaseCommand):
    help = 'Fix duplicate UserProfile entries and ensure all users have a profile'

    def handle(self, *args, **options):
        self.stdout.write("Starting UserProfile cleanup...")
        
        # Step 1: Ensure all users have a profile
        all_users = User.objects.all()
        created_count = 0
        
        for user in all_users:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': 'EMPLOYEE'}
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created profile for user: {user.username}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCleanup complete! Created {created_count} new profiles.'
            )
        )
        
        # Step 2: Display summary
        total_users = User.objects.count()
        total_profiles = UserProfile.objects.count()
        employees = UserProfile.objects.filter(role='EMPLOYEE').count()
        managers = UserProfile.objects.filter(role='MANAGER').count()
        
        self.stdout.write("\n--- Summary ---")
        self.stdout.write(f"Total Users: {total_users}")
        self.stdout.write(f"Total Profiles: {total_profiles}")
        self.stdout.write(f"Employees: {employees}")
        self.stdout.write(f"Managers: {managers}")

