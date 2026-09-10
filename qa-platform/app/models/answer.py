from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Sum
from django.db.models.functions import Coalesce


class Answer(models.Model):
    question = models.ForeignKey(
        'Question',
        on_delete=models.CASCADE,
        related_name='answers'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='answers'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    votes = GenericRelation('Vote', related_query_name='answer')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Answer by {self.author} on '{self.question.title}'"

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
