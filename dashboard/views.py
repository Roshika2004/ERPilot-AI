
# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from users.decorators import get_user_role
from claims.models import Claim


@login_required(login_url='login')
def home(request):
    """
    Smart home page that redirects based on user role
    """
    try:
        user_role = get_user_role(request.user)
        
        if user_role == 'MANAGER':
            return redirect('manager_dashboard')
        elif user_role == 'EMPLOYEE':
            return redirect('employee_dashboard')
        else:
            # Fallback to generic home
            return render(request, 'dashboard/home.html')
    except:
        return render(request, 'dashboard/home.html')
