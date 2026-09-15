"""URLs package for the app."""

from django.urls import path
from app.views import QuestionCreateView, QuestionDetailView, QuestionListView

app_name = 'app'

urlpatterns = [
    path('', QuestionListView.as_view(), name='question_list'),
    path('questions/ask/', QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question_detail'),
]
