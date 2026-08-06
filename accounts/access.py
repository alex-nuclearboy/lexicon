"""Application-level authorisation policy.

This module defines access to the main application. Access is granted to
active superusers and to active authenticated users who have the dedicated
application permission.
"""

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import AnonymousUser

APPLICATION_ACCESS_PERMISSION = "accounts.access_application"

UserType = AbstractBaseUser | AnonymousUser


def can_access_application(user: UserType | None) -> bool:
    """Return whether a user may access the application.

    Access is granted when the user is active and either:
    * is a superuser; or
    * has the dedicated application access permission.

    The permission may be assigned directly to the user or inherited through
    a Django group.

    Args:
        user: The user associated with the current request, or ``None``.

    Returns:
        ``True`` when the user may access the application; otherwise ``False``.
    """
    if user is None or not user.is_authenticated:
        return False

    if not user.is_active:
        return False

    if user.is_superuser:
        return True

    return user.has_perm(APPLICATION_ACCESS_PERMISSION)
