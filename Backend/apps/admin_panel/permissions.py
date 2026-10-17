from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    message = "Admin access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, "is_superuser", False)
                or getattr(user, "role", None) in ("head_admin", "sub_admin", "admin", "state_admin")
            )
        )

