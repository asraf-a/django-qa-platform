from django.core.exceptions import PermissionDenied


class AuthorRequiredMixin:
    """Ensures that only the author of an object can access or modify it."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user:
            raise PermissionDenied("You do not have permission to modify this object.")
        return obj
