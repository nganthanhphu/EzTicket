from functools import wraps
from flask import abort, redirect
from flask_login import current_user


def anonymous_required(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect("/")
        return f(*args, **kwargs)

    return decorated_func


def role_required(*roles):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):

            if not current_user.is_authenticated:
                abort(401)

            if current_user.role.value not in roles:
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return wrapper


def run_validations(validators):
    for func, args in validators:
        is_valid, err_msg = func(*args)
        if not is_valid:
            return False, err_msg
    return True, None