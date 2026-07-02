from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import UserProfile


def get_user_role(user):
    """
    Get the role of a user from their UserProfile.
    Returns the role string (e.g., 'MANAGER', 'EMPLOYEE') or None if profile doesn't exist.
    """
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile.role
    except UserProfile.DoesNotExist:
        return None


def role_required(required_role):
    """
    Decorator to check if user has the required role.
    Usage: @role_required('MANAGER')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Please login first!")
                return redirect('login')
            
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                if user_profile.role == required_role:
                    return view_func(request, *args, **kwargs)
                else:
                    messages.error(request, f"Access denied! Required role: {required_role}")
                    return redirect('home')
            except UserProfile.DoesNotExist:
                messages.error(request, "User profile not found!")
                return redirect('login')
        
        return wrapper
    return decorator


def employee_required(view_func):
    """
    Decorator to restrict view to employees only.
    Usage: @employee_required
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first!")
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role == 'EMPLOYEE':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "This page is for employees only!")
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found!")
            return redirect('login')
    
    return wrapper


def manager_required(view_func):
    """
    Decorator to restrict view to managers only.
    Usage: @manager_required
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first!")
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role == 'MANAGER':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "This page is for managers only!")
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found!")
            return redirect('login')
    
    return wrapper


def admin_required(view_func):
    """
    Decorator to restrict view to admins only.
    Usage: @admin_required
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first!")
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role == 'ADMIN':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "This page is for admins only!")
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found!")
            return redirect('login')
    
    return wrapper


def can_submit_claim(view_func):
    """
    Decorator to allow both employees and managers to submit claims.
    Usage: @can_submit_claim
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first!")
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role in ['EMPLOYEE', 'MANAGER']:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "You don't have permission to submit claims!")
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found!")
            return redirect('login')
    
    return wrapper


def can_review_claim(view_func):
    """
    Decorator to allow only managers to review claims.
    Usage: @can_review_claim
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first!")
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role == 'MANAGER':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Only managers can review claims!")
                return redirect('home')
        except UserProfile.DoesNotExist:
            messages.error(request, "User profile not found!")
            return redirect('login')
    
    return wrapper


def get_user_role(user):
    """
    Helper function to get user's role.
    Returns: 'EMPLOYEE', 'MANAGER', or None
    """
    try:
        user_profile = UserProfile.objects.get(user=user)
        return user_profile.role
    except UserProfile.DoesNotExist:
        return None


def is_employee(user):
    """Check if user is an employee"""
    return get_user_role(user) == 'EMPLOYEE'


def is_manager(user):
    """Check if user is a manager"""
    return get_user_role(user) == 'MANAGER'


def can_submit_claims(user):
    """Check if user can submit claims (employees and managers)"""
    return get_user_role(user) in ['EMPLOYEE', 'MANAGER']