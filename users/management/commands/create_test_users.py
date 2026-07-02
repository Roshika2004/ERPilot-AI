from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile


class Command(BaseCommand):
    help = 'Create default test users with roles for demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if users already exist'
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING('\n🔧 Setting up default test users...\n'))

        test_data = [
            {
                'username': 'manager1',
                'email': 'manager1@example.com',
                'password': 'manager123',
                'role': 'MANAGER',
                'first_name': 'John',
                'last_name': 'Manager'
            },
            {
                'username': 'manager2',
                'email': 'manager2@example.com',
                'password': 'manager123',
                'role': 'MANAGER',
                'first_name': 'Sarah',
                'last_name': 'Manager'
            },
            {
                'username': 'emp1',
                'email': 'emp1@example.com',
                'password': 'emp123',
                'role': 'EMPLOYEE',
                'first_name': 'Alice',
                'last_name': 'Employee'
            },
            {
                'username': 'emp2',
                'email': 'emp2@example.com',
                'password': 'emp123',
                'role': 'EMPLOYEE',
                'first_name': 'Bob',
                'last_name': 'Employee'
            },
            {
                'username': 'emp3',
                'email': 'emp3@example.com',
                'password': 'emp123',
                'role': 'EMPLOYEE',
                'first_name': 'Charlie',
                'last_name': 'Employee'
            },
            {
                'username': 'emp4',
                'email': 'emp4@example.com',
                'password': 'emp123',
                'role': 'EMPLOYEE',
                'first_name': 'Diana',
                'last_name': 'Employee'
            },
            {
                'username': 'emp5',
                'email': 'emp5@example.com',
                'password': 'emp123',
                'role': 'EMPLOYEE',
                'first_name': 'Eve',
                'last_name': 'Employee'
            },
        ]

        created_count = 0
        skipped_count = 0

        for user_data in test_data:
            username = user_data['username']
            
            # Check if user already exists
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )

            if created:
                # Set password
                user.set_password(user_data['password'])
                user.save()
                
                # Create profile with role
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={'role': user_data['role']}
                )
                
                role_badge = '👔' if user_data['role'] == 'MANAGER' else '👤'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created {role_badge} {username:15} ({user_data["role"]})'
                    )
                )
                created_count += 1
            else:
                # User exists, check if we should update
                profile = UserProfile.objects.filter(user=user).first()
                
                if not profile:
                    # Create missing profile
                    profile = UserProfile.objects.create(
                        user=user,
                        role=user_data['role']
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✓ Created profile for existing user {username}'
                        )
                    )
                    created_count += 1
                else:
                    role_badge = '👔' if profile.role == 'MANAGER' else '👤'
                    self.stdout.write(
                        self.style.WARNING(
                            f'⊘ Skipped {role_badge} {username:15} (already exists)'
                        )
                    )
                    skipped_count += 1

        # Display summary
        print()
        self.stdout.write(self.style.SUCCESS('✓ Setup complete!\n'))
        print('=' * 80)
        print('TEST USER CREDENTIALS:\n')
        
        for user_data in test_data:
            role_emoji = '👔 MANAGER' if user_data['role'] == 'MANAGER' else '👤 EMPLOYEE'
            print(f'{role_emoji:15} | Username: {user_data["username"]:12} | Password: {user_data["password"]}')
        
        print('\n' + '=' * 80)
        print(f'\n📊 Statistics:')
        print(f'   Created: {created_count}')
        print(f'   Skipped: {skipped_count}')
        print(f'   Total Users: {User.objects.count()}')
        print(f'   Total Managers: {UserProfile.objects.filter(role="MANAGER").count()}')
        print(f'   Total Employees: {UserProfile.objects.filter(role="EMPLOYEE").count()}')
        print()
