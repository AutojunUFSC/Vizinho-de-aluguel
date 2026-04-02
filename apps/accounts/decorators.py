from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied


def citizen_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'CIDADAO':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


def mei_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'MEI':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


def admin_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'ADMIN':
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper
