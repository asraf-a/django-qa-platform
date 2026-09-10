from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce

from .base import TimeStampedModel


class Question(TimeStampedModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    tags = models.ManyToManyField('Tag', blank=True, related_name='questions')

    votes = GenericRelation('Vote', related_query_name='question')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

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
