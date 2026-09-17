from django.urls import path
from app.views import (
    AnswerCommentCreateView,
    AnswerCreateView,
    AnswerDeleteView,
    AnswerUpdateView,
    CommentUpdateView,
    QuestionCommentCreateView,
    QuestionCreateView,
    QuestionDeleteView,
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
    path('questions/<int:pk>/delete/', QuestionDeleteView.as_view(), name='question_delete'),
    path('questions/<int:pk>/comments/', QuestionCommentCreateView.as_view(), name='question_comment_create'),
    path('questions/<int:pk>/answers/', AnswerCreateView.as_view(), name='answer_create'),
    path('answers/<int:pk>/edit/', AnswerUpdateView.as_view(), name='answer_edit'),
    path('answers/<int:pk>/delete/', AnswerDeleteView.as_view(), name='answer_delete'),
    path('answers/<int:pk>/comments/', AnswerCommentCreateView.as_view(), name='answer_comment_create'),
    path('comments/<int:pk>/edit/', CommentUpdateView.as_view(), name='comment_edit'),
    path('questions/<int:pk>/', QuestionDetailView.as_view(), name='question_detail'),
]
