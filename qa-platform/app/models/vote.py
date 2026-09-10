from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models


class Vote(models.Model):
    UPVOTE = 1
    DOWNVOTE = -1
    VOTE_CHOICES = (
        (UPVOTE, 'Upvote'),
        (DOWNVOTE, 'Downvote'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    value = models.SmallIntegerField(choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_type', 'object_id'],
                name='unique_user_vote'
            ),
            models.CheckConstraint(
                condition=models.Q(value__in=[1, -1]),
                name='valid_vote_value'
            ),
        ]

    def __str__(self):
        vote_type = 'Upvote' if self.value == self.UPVOTE else 'Downvote'
        return f"{self.user} - {vote_type} on {self.content_type} #{self.object_id}"

    def clean(self):
        super().clean()
        if self.value not in (self.UPVOTE, self.DOWNVOTE):
            raise ValidationError({'value': 'Vote value must be either 1 (upvote) or -1 (downvote).'})
