# Role-Based Authentication System - ERPilot AI

## Overview
This role-based authentication system provides a complete solution for managing different user roles (Employee and Manager) with separate dashboards and access control.

---

## 📋 System Components

### 1. **UserProfile Model** (`users/models.py`)
```python
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('MANAGER', 'Manager'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
```

### 2. **Authentication Forms** (`users/forms.py`)
- **LoginForm**: Simple login with username and password
- **RegistrationForm**: Complete registration with role selection

### 3. **Role-Based Decorators** (`users/decorators.py`)
- `@role_required('ROLE_NAME')`: Check specific role
- `@employee_required`: Restrict to employees
- `@manager_required`: Restrict to managers
- `get_user_role(user)`: Get user's role
- `is_employee(user)`: Check if employee
- `is_manager(user)`: Check if manager

### 4. **Views** (`users/views.py`)
- `login_view`: Login with role-based redirect
- `register_view`: Registration with role selection
- `logout_view`: Logout functionality
- `manager_dashboard`: Manager's dashboard
- `employee_dashboard`: Employee's dashboard

### 5. **Templates**
- `login.html`: Modern login page
- `register.html`: Registration with role selection
- `manager_dashboard.html`: Manager interface
- `employee_dashboard.html`: Employee interface

---

## 🚀 How to Use

### **Step 1: Create a User Profile on Registration**

When a new user registers, a `UserProfile` is automatically created with the selected role:

```python
# In register_view
user = form.save(commit=False)
user.set_password(form.cleaned_data['password'])
user.save()

role = request.POST.get('role', 'EMPLOYEE')
UserProfile.objects.create(user=user, role=role)
```

### **Step 2: Protect Views with Decorators**

#### Protect a view for Managers only:
```python
from users.decorators import manager_required

@login_required(login_url='login')
@manager_required
def review_claims(request):
    # Only managers can access this
    pass
```

#### Protect a view for Employees only:
```python
from users.decorators import employee_required

@login_required(login_url='login')
@employee_required
def submit_claim(request):
    # Only employees can access this
    pass
```

#### Check role in your code:
```python
from users.decorators import get_user_role

role = get_user_role(request.user)
if role == 'MANAGER':
    # Show manager-specific content
    pass
```

### **Step 3: Role-Based Redirects**

The login view automatically redirects users based on their role:

```python
user_profile = UserProfile.objects.get(user=user)

if user_profile.role == 'MANAGER':
    return redirect('manager_dashboard')
else:  # EMPLOYEE
    return redirect('employee_dashboard')
```

---

## 📝 URL Configuration

The following URLs are available:

```
/users/login/              → Login page
/users/register/           → Registration page
/users/logout/             → Logout
/users/manager/dashboard/  → Manager dashboard (manager only)
/users/employee/dashboard/ → Employee dashboard (employee only)
```

Update your main `urls.py`:

```python
from django.urls import path, include

urlpatterns = [
    # ... other patterns
    path('users/', include('users.urls')),
]
```

---

## 🔐 Security Features

1. **Password Hashing**: All passwords are hashed using Django's `set_password()`
2. **Login Required**: Views are protected with `@login_required` decorator
3. **Role Verification**: Each view verifies the user's role
4. **CSRF Protection**: All forms include `{% csrf_token %}`
5. **Message Framework**: User feedback with Django messages

---

## 💡 Common Usage Examples

### Example 1: Create a Manager-Only Report View

```python
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from users.decorators import manager_required
from claims.models import Claim

@login_required(login_url='login')
@manager_required
def generate_report(request):
    claims = Claim.objects.all()
    total_amount = sum(c.amount for c in claims)
    
    context = {
        'total_claims': claims.count(),
        'total_amount': total_amount,
    }
    return render(request, 'reports/manager_report.html', context)
```

### Example 2: Check Role in Template

```django
{% if request.user.userprofile.role == 'MANAGER' %}
    <a href="{% url 'manager_dashboard' %}">Manager Dashboard</a>
{% elif request.user.userprofile.role == 'EMPLOYEE' %}
    <a href="{% url 'employee_dashboard' %}">Employee Dashboard</a>
{% endif %}
```

### Example 3: Conditional URL Redirect

```python
from users.decorators import is_manager, is_employee

@login_required
def redirect_dashboard(request):
    if is_manager(request.user):
        return redirect('manager_dashboard')
    elif is_employee(request.user):
        return redirect('employee_dashboard')
    else:
        return redirect('home')
```

---

## 🎨 Customization

### Add New Roles
Modify `UserProfile.ROLE_CHOICES`:

```python
ROLE_CHOICES = (
    ('EMPLOYEE', 'Employee'),
    ('MANAGER', 'Manager'),
    ('ADMIN', 'Administrator'),
    ('AUDITOR', 'Auditor'),
)
```

### Create New Decorators
```python
def auditor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            if user_profile.role == 'AUDITOR':
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Access denied!")
                return redirect('home')
        except UserProfile.DoesNotExist:
            return redirect('login')
    
    return wrapper
```

---

## 🐛 Troubleshooting

### Issue: "User profile not found"
**Solution**: Ensure `UserProfile` is created when user registers:
```python
UserProfile.objects.get_or_create(user=user, defaults={'role': 'EMPLOYEE'})
```

### Issue: Redirect loop
**Solution**: Ensure the user has a valid role before redirecting:
```python
try:
    profile = UserProfile.objects.get(user=request.user)
    if profile.role == 'MANAGER':
        return redirect('manager_dashboard')
except UserProfile.DoesNotExist:
    messages.error(request, "Profile error")
    return redirect('login')
```

### Issue: Template showing wrong role
**Solution**: Access role correctly in template:
```django
{{ request.user.userprofile.role }}  <!-- Correct -->
{{ request.user.role }}               <!-- Wrong -->
```

---

## 📚 Integration with Existing Views

Update `claims/views.py` to use role-based access:

```python
from users.decorators import employee_required, manager_required

@login_required(login_url='login')
@employee_required
def create_claim(request):
    # Only employees can create claims
    pass

@login_required(login_url='login')
@manager_required
def review_claim(request, claim_id):
    # Only managers can review claims
    pass
```

---

## 🔄 Session Management

Sessions are automatically handled by Django. Customize session settings in `settings.py`:

```python
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_SECURE = True  # For HTTPS only
SESSION_COOKIE_HTTPONLY = True
```

---

## ✅ Testing the System

1. **Register as Employee**:
   - Go to `/users/register/`
   - Select "Employee" role
   - Submit

2. **Register as Manager**:
   - Go to `/users/register/`
   - Select "Manager" role
   - Submit

3. **Test Login Redirect**:
   - Login with employee account → redirects to employee dashboard
   - Login with manager account → redirects to manager dashboard

4. **Test Access Control**:
   - Try accessing manager dashboard as employee → should be denied
   - Try accessing employee dashboard as manager → should be denied

---

## 📞 Support

For issues or questions about the role-based authentication system, check:
1. Django Documentation: https://docs.djangoproject.com/
2. Django Authentication: https://docs.djangoproject.com/en/stable/topics/auth/
