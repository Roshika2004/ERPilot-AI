from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from claims.models import Claim
from users.models import UserProfile


class ManagerDashboardSearchAndInvoiceDownloadTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username='manager', password='pass1234')
        self.employee = User.objects.create_user(username='employee', password='pass1234')
        self.manager_profile, _ = UserProfile.objects.get_or_create(user=self.manager, defaults={'role': 'MANAGER'})
        self.manager_profile.role = 'MANAGER'
        self.manager_profile.save()
        self.employee_profile, _ = UserProfile.objects.get_or_create(user=self.employee, defaults={'role': 'EMPLOYEE', 'manager': self.manager})
        self.employee_profile.role = 'EMPLOYEE'
        self.employee_profile.manager = self.manager
        self.employee_profile.save()

    def test_manager_dashboard_search_filters_claims(self):
        Claim.objects.create(
            employee=self.employee,
            title='Taxi to client meeting',
            amount='120.00',
            invoice=SimpleUploadedFile('taxi.pdf', b'pdf-bytes', content_type='application/pdf'),
            status='PENDING',
        )
        Claim.objects.create(
            employee=self.employee,
            title='Lunch with team',
            amount='40.00',
            invoice=SimpleUploadedFile('lunch.pdf', b'pdf-bytes', content_type='application/pdf'),
            status='PENDING',
        )

        self.client.force_login(self.manager)
        response = self.client.get('/users/manager/dashboard/', {'search': 'taxi'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Taxi to client meeting')
        self.assertNotContains(response, 'Lunch with team')

    def test_download_claim_invoice_returns_attachment(self):
        claim = Claim.objects.create(
            employee=self.employee,
            title='Hotel dinner',
            amount='90.00',
            invoice=SimpleUploadedFile('invoice.pdf', b'invoice-bytes', content_type='application/pdf'),
            status='PENDING',
        )

        self.client.force_login(self.employee)
        response = self.client.get(f'/users/claims/{claim.id}/download-invoice/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(b''.join(response.streaming_content), b'invoice-bytes')


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='adminuser', password='pass1234')
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin, defaults={'role': 'ADMIN'})
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.save()

        self.manager = User.objects.create_user(username='manageruser', password='pass1234')
        self.manager_profile, _ = UserProfile.objects.get_or_create(user=self.manager, defaults={'role': 'MANAGER'})
        self.manager_profile.role = 'MANAGER'
        self.manager_profile.save()

        self.employee = User.objects.create_user(username='employeeuser', password='pass1234')
        self.employee_profile, _ = UserProfile.objects.get_or_create(user=self.employee, defaults={'role': 'EMPLOYEE'})
        self.employee_profile.role = 'EMPLOYEE'
        self.employee_profile.save()

    def test_admin_manage_users_shows_role_counts(self):
        self.client.force_login(self.admin)
        response = self.client.get('/users/admin/users/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_users'], 3)
        self.assertEqual(response.context['total_admins'], 1)
        self.assertEqual(response.context['total_managers'], 1)
        self.assertEqual(response.context['total_employees'], 1)

    def test_admin_manage_users_renders_total_users_count(self):
        self.client.force_login(self.admin)
        response = self.client.get('/users/admin/users/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '>3<')

    def test_admin_can_delete_a_user(self):
        self.client.force_login(self.admin)
        response = self.client.post('/users/admin/users/', {'action': 'delete', 'user_id': self.employee.id})

        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(id=self.employee.id).exists())
