from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views import View
from django.views.generic.detail import SingleObjectMixin

from app.models import Vote


class AuthorRequiredMixin:
    """Ensures that only the author of an object can access or modify it."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.author != self.request.user:
            raise PermissionDenied("You do not have permission to modify this object.")
        return obj


class BaseVoteView(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Base view for handling upvoting and downvoting across models.
    Subclasses must define `model` and implement `_get_redirect_url(self, obj)`.
    """
    model = None

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        vote_value = self._get_vote_value(request)
        if vote_value is not None:
            self._apply_vote(request.user, obj, vote_value)
        return redirect(self._get_redirect_url(obj))

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        return redirect(self._get_redirect_url(obj))

    def _get_redirect_url(self, obj):
        raise NotImplementedError("Subclasses must implement _get_redirect_url")

    def _get_vote_value(self, request):
        try:
            value = int(request.POST.get('value', 0))
            if value in (Vote.UPVOTE, Vote.DOWNVOTE):
                return value
        except (ValueError, TypeError):
            pass
        return None

    def _apply_vote(self, user, obj, value):
        content_type = ContentType.objects.get_for_model(self.model)
        vote = Vote.objects.filter(
            user=user,
            content_type=content_type,
            object_id=obj.pk
        ).first()

        if vote:
            if vote.value == value:
                vote.delete()
            else:
                vote.value = value
                vote.save(update_fields=['value', 'updated_at'])
        else:
            Vote.objects.create(
                user=user,
                content_type=content_type,
                object_id=obj.pk,
                value=value
            )

