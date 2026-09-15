from django.urls import path
from app.views import (
    QuestionCreateView,
    QuestionDetailView,
    QuestionListView,
    QuestionUpdateView,
    RegisterView,
    UserLoginView,
    UserLogoutView,
)

app_name = 'app'

urlpatterns = [
    path('', QuestionListView.as_view(), name='question_list'),
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/login/', UserLoginView.as_view(), name='login'),
    path('accounts/logout/', UserLogoutView.as_view(), name='logout'),
    path('questions/ask/', QuestionCreateView.as_view(), name='question_create'),
    path('questions/<int:pk>/edit/', QuestionUpdateView.as_view(), name='question_edit'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question_detail'),
]
