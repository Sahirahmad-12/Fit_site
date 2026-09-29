from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps


def superuser_required(view_func):
    """Only Django superusers can access this view."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        if not request.user.is_superuser:
            return redirect('/')          # or render a 403 page
        return view_func(request, *args, **kwargs)
    return wrapper


def staff_required(view_func):
    """Staff OR superusers can access this view."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        if not (request.user.is_staff or request.user.is_superuser):
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return wrapper