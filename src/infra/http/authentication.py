from flask_jwt_extended import get_current_user, get_jwt, get_jwt_identity, jwt_required


def authenticated(function):
    return jwt_required()(function)


def optional_authentication(function):
    return jwt_required(optional=True)(function)


def identity():
    return get_jwt_identity()


def account():
    return get_current_user()


def claims():
    return get_jwt()
