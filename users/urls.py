from django.urls import path
from .views import (
    login_view, logout_view, register_view, manager_dashboard, employee_dashboard, 
    claim_detail, manage_employee_relationship, quick_assign_employee, manage_all_employees,
    admin_dashboard, admin_assign_manager, admin_manage_users, employee_claim_detail,
    download_claim_invoice
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    
    # Admin URLs
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin/assign/', admin_assign_manager, name='admin_assign_manager'),
    path('admin/users/', admin_manage_users, name='admin_manage_users'),
    
    # Manager URLs
    path('manager/dashboard/', manager_dashboard, name='manager_dashboard'),
    path('employee/dashboard/', employee_dashboard, name='employee_dashboard'),
    path('manager/claim/<int:claim_id>/', claim_detail, name='claim_detail'),
    path('employee/claim/<int:claim_id>/', employee_claim_detail, name='employee_claim_detail'),
    path('manager/employee/<int:employee_id>/', manage_employee_relationship, name='manage_employee'),
    path('manager/assign/<int:employee_id>/', quick_assign_employee, name='quick_assign_employee'),
    path('manager/employees/', manage_all_employees, name='manage_all_employees'),
    path('claims/<int:claim_id>/download-invoice/', download_claim_invoice, name='download_claim_invoice'),
]