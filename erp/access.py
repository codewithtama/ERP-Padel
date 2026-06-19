from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def is_admin_user(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))

def is_staff_user(user) -> bool:
    # Staff biasa: login tapi bukan admin/superuser (halaman operasional non-admin)
    return bool(user and user.is_authenticated and not is_admin_user(user))

def is_management_user(user) -> bool:
    # Siapapun yang sudah login boleh melihat & membuat booking
    return bool(user and user.is_authenticated)

def role_required(check):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not check(request.user):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

admin_required = role_required(is_admin_user)
staff_required = role_required(lambda u: is_staff_user(u) or is_admin_user(u))
management_required = role_required(is_management_user)

def redirect_home_for_user(user):
    if is_admin_user(user):
        return redirect("dashboard")
    return redirect("attendance")