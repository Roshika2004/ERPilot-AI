import os
from decimal import Decimal, InvalidOperation
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import LoginForm, RegistrationForm
from .models import UserProfile
from .decorators import manager_required, employee_required, admin_required, get_user_role


def login_view(request):
    """
    Login view with role-based authentication.
    """
    if request.method == 'POST':
        form = LoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Role-based redirect
                try:
                    user_profile = UserProfile.objects.get(user=user)
                    
                    if user_profile.role == 'ADMIN':
                        messages.success(request, f"Welcome Admin, {user.first_name or user.username}!")
                        return redirect('admin_dashboard')
                    elif user_profile.role == 'MANAGER':
                        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                        return redirect('manager_dashboard')
                    else:  # EMPLOYEE
                        messages.success(request, f"Welcome back, {user.first_name or user.username}!")
                        return redirect('home')
                        
                except UserProfile.DoesNotExist:
                    messages.warning(request, "User profile not found. Redirecting to home.")
                    return redirect('home')
            else:
                messages.error(request, 'Invalid username or password')
                form.add_error(None, 'Invalid credentials')
    else:
        form = LoginForm()
    
    return render(request, 'users/login.html', {'form': form})


def register_view(request):
    """
    Registration view with role selection.
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            # Create user
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Get role from cleaned data - this is the crucial part
            role = form.cleaned_data.get('role')
            
            # Ensure role is valid, fallback to EMPLOYEE if not set
            if not role:
                role = 'EMPLOYEE'
            
            # DEBUG: Print what we're saving
            print(f"[DEBUG] Registering user {user.username} with role: {role}")
            
            # Create or update user profile with the selected role
            user_profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={'role': role}
            )
            
            # If profile already existed, update the role
            if not created:
                user_profile.role = role
                user_profile.save()
                print(f"[DEBUG] Updated existing profile for {user.username} to {role}")
            else:
                print(f"[DEBUG] Created new profile for {user.username} with role {role}")
            
            # Verify it was saved
            final_profile = UserProfile.objects.get(user=user)
            print(f"[DEBUG] Verified: {final_profile.user.username} has role {final_profile.role}")
            
            if created:
                messages.success(request, f'Account created successfully as {role}! Please login.')
            else:
                messages.success(request, f'Account updated! Please login.')
            
            return redirect('login')
        else:
            # Form validation failed
            print(f"[DEBUG] Form validation failed. Errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})


@login_required(login_url='login')
def logout_view(request):
    """
    Logout view.
    """
    username = request.user.first_name or request.user.username
    logout(request)
    messages.success(request, f'Goodbye, {username}! You have been logged out.')
    return redirect('login')


@login_required(login_url='login')
@manager_required
def manager_dashboard(request):
    """
    Manager dashboard - only accessible to managers.
    Shows ONLY claims from assigned employees.
    """
    # Get claims data for manager
    from claims.models import Claim
    from django.contrib.auth.models import User
    
    # Get managed employees for this manager
    try:
        manager_profile = UserProfile.objects.get(user=request.user)
        managed_employees = UserProfile.objects.filter(manager=request.user).order_by('user__username')
    except UserProfile.DoesNotExist:
        managed_employees = UserProfile.objects.none()
    
    # Get list of managed employee user IDs
    managed_employee_ids = managed_employees.values_list('user_id', flat=True)
    
    # Get ONLY claims from managed employees
    all_claims = Claim.objects.filter(employee_id__in=managed_employee_ids).order_by('-created_at')
    
    # Get filter from request
    claims_filter = request.GET.get('filter', 'all')
    search_query = request.GET.get('search', '').strip()

    if claims_filter == 'pending':
        filtered_claims = all_claims.filter(status='PENDING')
    elif claims_filter == 'approved':
        filtered_claims = all_claims.filter(status='APPROVED')
    elif claims_filter == 'rejected':
        filtered_claims = all_claims.filter(status='REJECTED')
    else:  # 'all'
        filtered_claims = all_claims

    if search_query:
        query_terms = [term for term in search_query.split() if term]
        search_filter = Q()
        for term in query_terms:
            search_filter |= Q(title__icontains=term)
            search_filter |= Q(employee__username__icontains=term)
            search_filter |= Q(employee__first_name__icontains=term)
            search_filter |= Q(employee__last_name__icontains=term)
            try:
                amount_value = Decimal(term)
                search_filter |= Q(amount=amount_value)
            except (InvalidOperation, ValueError):
                pass
        filtered_claims = filtered_claims.filter(search_filter)

    filtered_claims = filtered_claims.order_by('-created_at')
    
    # Calculate stats for managed employees ONLY
    pending_claims = all_claims.filter(status='PENDING').count()
    total_claims = all_claims.count()
    approved_claims = all_claims.filter(status='APPROVED').count()
    rejected_claims = all_claims.filter(status='REJECTED').count()
    
    # Get available employees (not yet assigned to this manager)
    available_employees = UserProfile.objects.filter(role='EMPLOYEE', manager__isnull=True).order_by('user__username')
    
    # Add employee_profile to each claim for display
    claims_with_profiles = []
    for claim in filtered_claims:
        try:
            employee_profile = UserProfile.objects.get(user=claim.employee)
            claim.employee_profile = employee_profile
        except UserProfile.DoesNotExist:
            claim.employee_profile = None
        claims_with_profiles.append(claim)
    
    # Get user role
    user_role = get_user_role(request.user)
    
    context = {
        'claims_pending': claims_with_profiles,
        'claims_all': claims_with_profiles,
        'pending_claims': pending_claims,
        'total_claims': total_claims,
        'approved_claims': approved_claims,
        'rejected_claims': rejected_claims,
        'managed_employees': managed_employees,
        'available_employees': available_employees,
        'user_role': user_role,
        'current_filter': claims_filter,
        'search_query': search_query,
    }
    
    return render(request, 'dashboard/manager_dashboard.html', context)


@login_required(login_url='login')
def download_claim_invoice(request, claim_id):
    """Download a claim invoice for the employee or their manager."""
    from claims.models import Claim

    claim = get_object_or_404(Claim, id=claim_id)
    user_profile = UserProfile.objects.filter(user=request.user).first()

    is_owner = request.user == claim.employee
    is_manager = user_profile and user_profile.role in ['MANAGER', 'ADMIN']
    is_assigned_manager = bool(
        user_profile and user_profile.role == 'MANAGER' and
        UserProfile.objects.filter(user=claim.employee, manager=request.user).exists()
    )

    if not (request.user.is_superuser or is_owner or is_manager or is_assigned_manager):
        raise Http404('You do not have access to this invoice.')

    if not claim.invoice:
        raise Http404('No invoice uploaded for this claim.')

    if not claim.invoice.storage.exists(claim.invoice.name):
        raise Http404('Invoice file not found.')

    response = FileResponse(claim.invoice.open('rb'), as_attachment=True)
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(claim.invoice.name)}"'
    return response


@login_required(login_url='login')
@employee_required
def employee_dashboard(request):
    """
    Employee dashboard - only accessible to employees.
    """
    # Get user's claims
    from claims.models import Claim
    
    my_claims = Claim.objects.filter(employee=request.user)
    approved = my_claims.filter(status='APPROVED').count()
    pending = my_claims.filter(status='PENDING').count()
    rejected = my_claims.filter(status='REJECTED').count()
    total = my_claims.count()
    
    # Get user role
    user_role = get_user_role(request.user)
    
    context = {
        'my_claims': my_claims,
        'approved': approved,
        'pending': pending,
        'rejected': rejected,
        'total': total,
        'user_role': user_role,
    }
    
    return render(request, 'dashboard/employee_dashboard.html', context)


@login_required(login_url='login')
@manager_required
def claim_detail(request, claim_id):
    """
    View detailed information about a claim and allow manager to override AI decision.
    """
    from claims.models import Claim
    from django.shortcuts import get_object_or_404
    
    claim = get_object_or_404(Claim, id=claim_id)
    
    if request.method == 'POST':
        override_status = request.POST.get('override_status')
        override_reason = request.POST.get('override_reason')
        
        if override_status in ['APPROVED', 'REJECTED']:
            from django.utils import timezone
            claim.override_status = override_status
            claim.override_reason = override_reason
            claim.overridden_by = request.user
            claim.overridden_at = timezone.now()
            claim.status = override_status  # Update the status based on override
            claim.save()
            
            messages.success(request, f"Claim {override_status.lower()} and decision saved!")
            return redirect('manager_dashboard')
    
    context = {
        'claim': claim,
    }
    
    return render(request, 'dashboard/claim_detail.html', context)


@login_required(login_url='login')
@employee_required
def employee_claim_detail(request, claim_id):
    """
    View detailed information about a claim for employees.
    Employees can only view their own claims.
    """
    from claims.models import Claim
    from django.shortcuts import get_object_or_404
    
    claim = get_object_or_404(Claim, id=claim_id)
    
    # Ensure employee can only view their own claims
    if claim.employee != request.user:
        messages.error(request, "You can only view your own claims!")
        return redirect('employee_dashboard')
    
    context = {
        'claim': claim,
        'user_role': get_user_role(request.user),
    }
    
    return render(request, 'dashboard/employee_claim_detail.html', context)


@login_required(login_url='login')
@manager_required
def manage_employee_relationship(request, employee_id):
    """
    Manage manager-employee relationship.
    """
    from django.shortcuts import get_object_or_404
    from django.contrib.auth.models import User
    
    employee_user = get_object_or_404(User, id=employee_id)
    employee_profile = get_object_or_404(UserProfile, user=employee_user)
    
    if request.method == 'POST':
        assign_to_manager = request.POST.get('assign_to_manager')
        
        if assign_to_manager == 'yes':
            employee_profile.manager = request.user
            employee_profile.save()
            messages.success(request, f"{employee_user.username} is now assigned to you!")
        elif assign_to_manager == 'no':
            employee_profile.manager = None
            employee_profile.save()
            messages.success(request, f"{employee_user.username} has been unassigned!")
        
        return redirect('manager_dashboard')
    
    # Get all claims for this employee
    from claims.models import Claim
    employee_claims = Claim.objects.filter(employee=employee_user).order_by('-created_at')
    
    # Count statistics
    total_claims = employee_claims.count()
    pending_claims = employee_claims.filter(status='PENDING').count()
    approved_claims = employee_claims.filter(status='APPROVED').count()
    rejected_claims = employee_claims.filter(status='REJECTED').count()
    overridden_claims = employee_claims.exclude(override_status='NONE').count()
    
    context = {
        'employee': employee_user,
        'employee_profile': employee_profile,
        'employee_claims': employee_claims,
        'total_claims': total_claims,
        'pending_claims': pending_claims,
        'approved_claims': approved_claims,
        'rejected_claims': rejected_claims,
        'overridden_claims': overridden_claims,
    }
    
    return render(request, 'dashboard/manage_employee.html', context)


@login_required(login_url='login')
@manager_required
def quick_assign_employee(request, employee_id):
    """
    Quick assign endpoint - assigns employee to the current manager via AJAX/form submission.
    """
    from django.shortcuts import get_object_or_404
    from django.http import JsonResponse
    from django.contrib.auth.models import User
    
    employee_user = get_object_or_404(User, id=employee_id)
    employee_profile = get_object_or_404(UserProfile, user=employee_user)
    
    # Check if already assigned to this manager
    if employee_profile.manager == request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'info', 'message': f'{employee_user.username} is already assigned to you'})
        messages.info(request, f'{employee_user.username} is already assigned to you')
    else:
        # Assign to current manager
        employee_profile.manager = request.user
        employee_profile.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'success', 'message': f'{employee_user.username} assigned successfully!'})
        messages.success(request, f'{employee_user.username} assigned to you successfully!')
    
    return redirect('manager_dashboard')


@login_required(login_url='login')
@manager_required
def manage_all_employees(request):
    """
    View for managing all available employees and assigning them to the manager.
    """
    # Get all employees
    all_employees = UserProfile.objects.filter(role='EMPLOYEE').order_by('user__username')
    
    # Separate managed and available employees
    managed_employees = all_employees.filter(manager=request.user)
    available_employees = all_employees.filter(manager__isnull=True)
    
    # Get user role
    user_role = get_user_role(request.user)
    
    context = {
        'managed_employees': managed_employees,
        'available_employees': available_employees,
        'total_managed': managed_employees.count(),
        'total_available': available_employees.count(),
        'user_role': user_role,
    }
    
    return render(request, 'dashboard/manage_all_employees.html', context)


@login_required(login_url='login')
@admin_required
def admin_dashboard(request):
    """
    Admin dashboard - accessible to admins only.
    Allows admins to manage all users and assign managers to employees.
    """
    from .decorators import admin_required
    from django.contrib.auth.models import User
    
    # Get all users with their profiles
    all_users = User.objects.all()
    managers = UserProfile.objects.filter(role='MANAGER').select_related('user')
    employees = UserProfile.objects.filter(role='EMPLOYEE').select_related('user', 'manager')
    admins = UserProfile.objects.filter(role='ADMIN').select_related('user')
    
    # Unassigned employees
    unassigned_employees = employees.filter(manager__isnull=True)
    
    context = {
        'managers': managers,
        'employees': employees,
        'unassigned_employees': unassigned_employees,
        'admins': admins,
        'total_users': all_users.count(),
        'total_managers': managers.count(),
        'total_employees': employees.count(),
        'total_admins': admins.count(),
        'total_unassigned': unassigned_employees.count(),
        'user_role': get_user_role(request.user),
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required(login_url='login')
@admin_required
def admin_assign_manager(request):
    """
    Admin page to assign managers to employees.
    """
    from django.contrib.auth.models import User
    
    managers = UserProfile.objects.filter(role='MANAGER').select_related('user')
    employees = UserProfile.objects.filter(role='EMPLOYEE').select_related('user', 'manager')
    
    if request.method == 'POST':
        employee_id = request.POST.get('employee_id')
        manager_id = request.POST.get('manager_id')
        action = request.POST.get('action')
        
        try:
            employee_user = User.objects.get(id=employee_id)
            employee_profile = UserProfile.objects.get(user=employee_user)
            
            if action == 'assign':
                manager_user = User.objects.get(id=manager_id)
                employee_profile.manager = manager_user
                employee_profile.save()
                messages.success(request, f"✓ Assigned {employee_user.username} to {manager_user.username}")
            elif action == 'remove':
                employee_profile.manager = None
                employee_profile.save()
                messages.success(request, f"✓ Removed manager assignment from {employee_user.username}")
            
            return redirect('admin_assign_manager')
        
        except (User.DoesNotExist, UserProfile.DoesNotExist) as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('admin_assign_manager')
    
    context = {
        'managers': managers,
        'employees': employees,
        'user_role': get_user_role(request.user),
    }
    
    return render(request, 'dashboard/admin_assign_manager.html', context)


@login_required(login_url='login')
@admin_required
def admin_manage_users(request):
    """
    Admin page to view and manage all users.
    """
    from django.contrib.auth.models import User

    all_users = User.objects.all().order_by('username')

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        if action == 'delete' and user_id:
            try:
                target_user = User.objects.get(id=user_id)
                if target_user == request.user:
                    messages.error(request, 'You cannot delete your own admin account.')
                else:
                    target_user.delete()
                    messages.success(request, f'User {target_user.username} deleted successfully.')
            except User.DoesNotExist:
                messages.error(request, 'Selected user does not exist.')

            return redirect('admin_manage_users')

    role_counts = {
        'total_users': all_users.count(),
        'total_admins': UserProfile.objects.filter(role='ADMIN').count(),
        'total_managers': UserProfile.objects.filter(role='MANAGER').count(),
        'total_employees': UserProfile.objects.filter(role='EMPLOYEE').count(),
    }

    context = {
        'users': all_users,
        'user_role': get_user_role(request.user),
        **role_counts,
    }

    return render(request, 'dashboard/admin_manage_users.html', context)