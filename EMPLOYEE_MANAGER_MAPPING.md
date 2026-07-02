# Employee-Manager Mapping & Role-Based System Documentation

**Last Updated:** May 28, 2026
**Version:** 2.0 (Enhanced with Multiple Assignment Methods)

---

## 📋 Table of Contents
1. [Database Structure](#database-structure)
2. [System Architecture](#system-architecture)
3. [Employee Assignment Methods](#employee-assignment-methods)
4. [API Reference](#api-reference)
5. [UI Components](#ui-components)
6. [Testing & Verification](#testing--verification)

---

## Database Structure

### UserProfile Model
```python
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('MANAGER', 'Manager'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_employees'
    )
```

### Database Relationship
```
users_userprofile table:
+----+----------+---------+------------+
| id | role     | user_id | manager_id |
+----+----------+---------+------------+
| 1  | MANAGER  |    1    |   NULL     | ← Manager (no manager assigned)
| 2  | EMPLOYEE |    2    |    1       | ← Assigned to user_id=1 (Manager)
| 3  | EMPLOYEE |    3    |    1       | ← Assigned to user_id=1 (Manager)
| 4  | EMPLOYEE |    4    |    NULL    | ← Unassigned employee
+----+----------+---------+------------+
```

---

## System Architecture

### Role-Based Access Control

**Three Levels of Authentication:**

1. **Registration Phase** (`register_view`)
   - User selects role: MANAGER or EMPLOYEE
   - UserProfile created with selected role
   - manager_id initially = NULL

2. **Authentication Phase** (`login_view`)
   - Login redirects based on role:
     - MANAGER → manager_dashboard
     - EMPLOYEE → employee_dashboard
   - Role verified via UserProfile.role

3. **Authorization Phase** (`@manager_required`, `@employee_required`)
   - Decorators enforce role-based access
   - Returns 403 if user lacks required role

### Key Models & Relationships

**User Flow:**
```
Registration → Create User → Create UserProfile with role
    ↓
Login → Check UserProfile.role → Redirect to appropriate dashboard
    ↓
Manager Dashboard → View available employees → Assign employees
    ↓
Employee records manager_id → Manager can now manage employee's claims
```

---

## Employee Assignment Methods

### Method 1: Manager Dashboard Quick Assignment
**Location:** `/users/manager/dashboard/`

**Flow:**
1. Manager views "Available Employees to Assign" section
2. Clicks "Assign to Me" button on any unassigned employee
3. Redirects to manage_employee page where assignment happens
4. Employee now appears in "Your Managed Employees" section

**Code:**
```python
# templates/dashboard/manager_dashboard.html (Lines 312-335)
<!-- Available Employees Section -->
<h5 class="section-title">
    <i class="bi bi-person-plus"></i> Available Employees to Assign
</h5>
<div class="row mb-4">
    {% for emp_profile in available_employees %}
        <a href="{% url 'manage_employee' emp_profile.user.id %}" 
           class="action-btn btn-manage">
            <i class="bi bi-link"></i> Assign to Me
        </a>
    {% endfor %}
</div>
```

### Method 2: Individual Employee Management Page
**Location:** `/users/manager/employee/<employee_id>/`

**Flow:**
1. Manager navigates to specific employee's page
2. Views employee details and claims history
3. Clicks "Assign to Me" or "Remove Assignment" button
4. Form submission triggers assignment/unassignment

**Code:**
```python
# views.py - manage_employee_relationship (Lines 234-280)
@login_required(login_url='login')
@manager_required
def manage_employee_relationship(request, employee_id):
    """Manage manager-employee relationship."""
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
    # ... context and rendering
```

### Method 3: Bulk Employee Management Dashboard
**Location:** `/users/manager/employees/`

**Features:**
- View all managed employees in one place
- View all available employees to assign
- Quick assign/remove functionality
- Statistics on managed vs. available employees

**Code:**
```python
# views.py - manage_all_employees (Lines 324-352)
@login_required(login_url='login')
@manager_required
def manage_all_employees(request):
    """View for managing all available employees."""
    all_employees = UserProfile.objects.filter(role='EMPLOYEE').order_by('user__username')
    managed_employees = all_employees.filter(manager=request.user)
    available_employees = all_employees.filter(manager__isnull=True)
    
    context = {
        'managed_employees': managed_employees,
        'available_employees': available_employees,
        'total_managed': managed_employees.count(),
        'total_available': available_employees.count(),
        'user_role': user_role,
    }
    return render(request, 'dashboard/manage_all_employees.html', context)
```

### Method 4: Quick Assign Endpoint
**Location:** `/users/manager/assign/<employee_id>/`

**Flow:**
1. Single-click employee assignment
2. Directly assigns employee to manager
3. Redirects back to manager dashboard

**Code:**
```python
# views.py - quick_assign_employee (Lines 303-323)
@login_required(login_url='login')
@manager_required
def quick_assign_employee(request, employee_id):
    """Quick assign endpoint - assigns employee to current manager."""
    employee_user = get_object_or_404(User, id=employee_id)
    employee_profile = get_object_or_404(UserProfile, user=employee_user)
    
    if employee_profile.manager != request.user:
        employee_profile.manager = request.user
        employee_profile.save()
        messages.success(request, f'{employee_user.username} assigned successfully!')
    
    return redirect('manager_dashboard')
```

---

## API Reference

### Views (users/views.py)

| View | URL | Methods | Role Required | Purpose |
|------|-----|---------|---------------|---------|
| `login_view` | `/users/login/` | GET, POST | None | User authentication |
| `register_view` | `/users/register/` | GET, POST | None | User registration |
| `logout_view` | `/users/logout/` | POST | Any | User logout |
| `manager_dashboard` | `/users/manager/dashboard/` | GET | Manager | Manager main dashboard |
| `employee_dashboard` | `/users/employee/dashboard/` | GET | Employee | Employee main dashboard |
| `manage_employee_relationship` | `/users/manager/employee/<id>/` | GET, POST | Manager | Individual employee management |
| `quick_assign_employee` | `/users/manager/assign/<id>/` | GET | Manager | Quick assign endpoint |
| `manage_all_employees` | `/users/manager/employees/` | GET | Manager | Bulk employee management |
| `claim_detail` | `/users/manager/claim/<id>/` | GET, POST | Manager | Claim review page |

### Models (users/models.py)

```python
# Get all managed employees for a manager
managed = UserProfile.objects.filter(manager=manager_user)

# Get unassigned employees
unassigned = UserProfile.objects.filter(role='EMPLOYEE', manager__isnull=True)

# Get user's role
profile = UserProfile.objects.get(user=user)
role = profile.role  # 'MANAGER' or 'EMPLOYEE'

# Assign employee to manager
profile = UserProfile.objects.get(user=employee)
profile.manager = manager_user
profile.save()

# Unassign employee
profile.manager = None
profile.save()
```

---

## UI Components

### Manager Dashboard Components

#### 1. Managed Employees Section
```html
<!-- Shows all employees assigned to current manager -->
<h5 class="section-title">
    <i class="bi bi-people"></i> Your Managed Employees
</h5>
<div class="row mb-4">
    {% for emp_profile in managed_employees %}
        <div class="employee-card">
            <!-- Employee info and manage button -->
        </div>
    {% endfor %}
</div>
```

#### 2. Available Employees Section
```html
<!-- Shows all employees NOT yet assigned to any manager -->
<h5 class="section-title">
    <i class="bi bi-person-plus"></i> Available Employees to Assign
</h5>
<div class="row mb-4">
    {% for emp_profile in available_employees %}
        <div class="employee-card">
            <!-- Unassigned employee info with "Assign to Me" button -->
        </div>
    {% endfor %}
</div>
```

### Manage All Employees Page

**Two Tabs:**
1. **Your Team** - Shows managed employees with Remove option
2. **Available** - Shows unassigned employees with "Assign to Me" option

---

## Testing & Verification

### Test Scenario 1: Register and Assign Employees

**Steps:**
```bash
1. Create a manager user:
   - Go to /users/register/
   - Select role: MANAGER
   
2. Create employee users:
   - Go to /users/register/ (3 times)
   - Select role: EMPLOYEE
   
3. Login as manager
   
4. Visit /users/manager/dashboard/
   - See "Available Employees to Assign" section
   - Click "Assign to Me" on an employee
   
5. Verify in "Your Managed Employees" section
```

### Test Scenario 2: Quick Assignment

```bash
1. Manager Dashboard → "Assign to Me" button on available employee
2. Should redirect and show success message
3. Employee appears in "Your Managed Employees"
```

### Test Scenario 3: Bulk Management

```bash
1. Manager Dashboard → "Manage All Employees" button
2. See statistics and tabs
3. Switch between "Your Team" and "Available" tabs
4. Test assign/remove functionality
```

### Database Verification

```bash
# Check mappings in shell
python manage.py shell
>>> from users.models import UserProfile
>>> for p in UserProfile.objects.select_related('user', 'manager'):
...     mgr = p.manager.username if p.manager else "Not Assigned"
...     print(f"{p.user.username:15} ({p.role:8}) → {mgr}")

# Expected output:
# manager_user    (MANAGER ) → Not Assigned
# emp_user_1      (EMPLOYEE) → manager_user
# emp_user_2      (EMPLOYEE) → manager_user
# emp_user_3      (EMPLOYEE) → Not Assigned
```

---

## Features & Capabilities

### ✅ Manager Capabilities
- View assigned employees
- View available employees to assign
- Assign employees (4 different methods)
- Unassign employees
- View employee claims
- Review and override AI recommendations
- See employee claim statistics

### ✅ Employee Capabilities
- Submit expense claims
- View own claims dashboard
- See claim status and AI recommendations
- Track claim history

### ✅ System Features
- Role-based access control
- Secure role-based decorators
- Multiple assignment methods
- Comprehensive employee management interface
- Statistics and analytics
- Error handling and validation

---

## Summary

The role mapping system provides:

1. **Secure Authentication** - Users logged into appropriate dashboards by role
2. **Flexible Assignment** - Multiple ways to assign employees to managers
3. **Comprehensive Management** - Full employee lifecycle management
4. **Scalable Architecture** - Easy to extend with new roles or features
5. **User-Friendly UI** - Intuitive interfaces for both managers and employees
- Assignment is done manually by the manager clicking "Assign to Me"
