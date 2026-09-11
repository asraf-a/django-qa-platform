"""URLs package for the app."""

from django.urls import path
from app.views import QuestionListView

app_name = 'app'

urlpatterns = [
    path('', QuestionListView.as_view(), name='question_list'),
]
