from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, resolve_url
from django.views import View
from django.views.generic.detail import SingleObjectMixin

from app.models import Vote


class DeleteSuccessMessageMixin:
    """Adds a success flash message upon successful deletion."""
    success_message = ""

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.success_message:
            messages.success(self.request, self.success_message)
        return response


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
    Supports both standard form submission and asynchronous (AJAX/JSON) requests.
    Subclasses must define `model` and implement `_get_redirect_url(self, obj)`.
    """
    model = None

    def _is_ajax(self, request):
        return (
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('accept', '')
        )

    def handle_no_permission(self):
        if self._is_ajax(self.request):
            login_url = resolve_url(self.get_login_url())
            return JsonResponse({
                'error': 'unauthenticated',
                'login_url': f"{login_url}?next={self.request.path}"
            }, status=401)
        return super().handle_no_permission()

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        vote_value = self._get_vote_value(request)
        is_ajax = self._is_ajax(request)

        if vote_value is None:
            if is_ajax:
                return JsonResponse({'error': 'Invalid vote value'}, status=400)
            return redirect(self._get_redirect_url(obj))

        self._apply_vote(request.user, obj, vote_value)

        if is_ajax:
            content_type = ContentType.objects.get_for_model(self.model)
            current_vote = Vote.objects.filter(
                user=request.user,
                content_type=content_type,
                object_id=obj.pk
            ).first()
            user_vote = current_vote.value if current_vote else None

            return JsonResponse({
                'score': obj.score,
                'upvotes_count': obj.upvotes_count,
                'downvotes_count': obj.downvotes_count,
                'user_vote': user_vote,
            })

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

