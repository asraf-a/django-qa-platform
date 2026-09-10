from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from .base import TimeStampedModel


class Comment(TimeStampedModel):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField()

    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments'
    )
    answer = models.ForeignKey(
        'Answer',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    votes = GenericRelation('Vote', related_query_name='comment')

    class Meta:
        ordering = ['created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(question__isnull=False) & Q(answer__isnull=True)) |
                    (Q(question__isnull=True) & Q(answer__isnull=False))
                ),
                name='comment_exactly_one_target'
            ),
        ]

    def __str__(self):
        target = self.get_root_target()
        target_name = f"{target.__class__.__name__} #{target.pk}" if target else "Unknown"
        return f"Comment by {self.author} on {target_name}"

    @property
    def is_root_comment(self):
        return self.parent is None

    def get_root_comment(self):
        curr = self
        while curr.parent is not None:
            curr = curr.parent
        return curr

    def get_root_target(self):
        if self.question:
            return self.question
        if self.answer:
            return self.answer
        root = self.get_root_comment()
        return root.question or root.answer

    def get_depth(self):
        depth = 0
        curr = self
        while curr.parent is not None:
            depth += 1
            curr = curr.parent
        return depth

    @property
    def score(self):
        res = self.votes.aggregate(total=Coalesce(Sum('value'), 0))
        return res['total']

    @property
    def upvotes_count(self):
        return self.votes.filter(value=1).count()

    @property
    def downvotes_count(self):
        return self.votes.filter(value=-1).count()

    def _validate_self_parent(self):
        """Prevent a comment from being its own parent."""
        if self.pk and self.parent_id == self.pk:
            raise ValidationError({'parent': 'A comment cannot be its own parent.'})

    def _validate_circular_reference(self):
        """Prevent circular parent relationships by checking the parent chain."""
        if self.pk and self.parent:
            curr = self.parent
            while curr is not None:
                if curr.pk == self.pk:
                    raise ValidationError({'parent': 'Circular parent reference detected.'})
                curr = curr.parent

    def _validate_single_target(self):
        """Ensure a comment cannot explicitly belong to both a Question and an Answer."""
        if self.question and self.answer:
            raise ValidationError('A comment cannot belong to both a Question and an Answer.')

    def _validate_parent_target(self):
        """
        Handle reply and root-target validation:
        - Ensure a reply's target matches its parent.
        - Inherit the parent's Question or Answer target.
        - Ensure a top-level comment has either a Question or an Answer.
        """
        if self.parent:
            parent_root_target = self.parent.get_root_target()
            if parent_root_target is None:
                raise ValidationError({'parent': 'Parent comment has no valid root target.'})

            if self.parent.question:
                if self.answer:
                    raise ValidationError({'answer': 'Cannot attach an Answer target to a reply of a Question comment.'})
                if self.question and self.question != self.parent.question:
                    raise ValidationError({'question': 'Reply question must match parent comment question.'})
                self.question = self.parent.question
                self.answer = None
            elif self.parent.answer:
                if self.question:
                    raise ValidationError({'question': 'Cannot attach a Question target to a reply of an Answer comment.'})
                if self.answer and self.answer != self.parent.answer:
                    raise ValidationError({'answer': 'Reply answer must match parent comment answer.'})
                self.answer = self.parent.answer
                self.question = None
        else:
            if not self.question and not self.answer:
                raise ValidationError('A top-level comment must be associated with either a Question or an Answer.')

    def clean(self):
        super().clean()
        self._validate_self_parent()
        self._validate_circular_reference()
        self._validate_single_target()
        self._validate_parent_target()

    def save(self, *args, **kwargs):
        # Automatically inherit root target from parent if it is a reply
        if self.parent:
            if self.parent.question:
                self.question = self.parent.question
                self.answer = None
            elif self.parent.answer:
                self.answer = self.parent.answer
                self.question = None
        super().save(*args, **kwargs)
