import django_filters
from django.contrib.contenttypes.models import ContentType
from django.db.models import IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from app.models import Question, Vote


class QuestionFilter(django_filters.FilterSet):
    SORT_OPTIONS = {
        'newest': 'Newest',
        'most_voted': 'Most Voted',
        'unanswered': 'Unanswered',
    }

    q = django_filters.CharFilter(method='filter_search')
    tag = django_filters.CharFilter(method='filter_tags')
    sort = django_filters.CharFilter(method='filter_sort')

    class Meta:
        model = Question
        fields = ['q', 'tag', 'sort']

    def filter_search(self, queryset, name, value):
        if value:
            return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value)).distinct()
        return queryset

    @property
    def current_sort(self):
        sort = self.data.get('sort', 'newest')
        return sort if sort in self.SORT_OPTIONS else 'newest'

    def filter_tags(self, queryset, name, value):
        tags = self.data.getlist('tag') if hasattr(self.data, 'getlist') else [value]
        if tags:
            return queryset.filter(tags__slug__in=tags).distinct()
        return queryset

    def filter_sort(self, queryset, name, value):
        if value == 'most_voted':
            ct = ContentType.objects.get_for_model(Question)
            vote_subquery = (
                Vote.objects
                .filter(content_type=ct, object_id=OuterRef('pk'))
                .values('object_id')
                .annotate(total=Sum('value'))
                .values('total')
            )
            return queryset.annotate(
                vote_score=Coalesce(Subquery(vote_subquery, output_field=IntegerField()), Value(0))
            ).order_by('-vote_score', '-created_at')
        elif value == 'unanswered':
            return queryset.filter(answers__isnull=True).order_by('-created_at')
        return queryset.order_by('-created_at')

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)
        if self.current_sort not in ('most_voted', 'unanswered'):
            qs = qs.order_by('-created_at')
        return qs
