from .models import UserProfile

def get_user_role(user):
    try:
        return user.userprofile.role
    except:
        return "EMPLOYEE"