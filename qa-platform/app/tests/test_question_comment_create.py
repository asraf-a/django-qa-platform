from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.views.generic import CreateView

from app.forms import QuestionCommentForm
from app.models import Answer, Comment, Question
from app.views import QuestionCommentCreateView

User = get_user_model()


class QuestionCommentCreateViewTest(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user(username='alice', password='password123')
        self.comment_author = User.objects.create_user(username='bob', password='password123')
        self.other_user = User.objects.create_user(username='charlie', password='password123')

        self.question = Question.objects.create(
            title='How to write tests for Question Comments?',
            description='I need to test question comments thoroughly.',
            author=self.question_author
        )
        self.url = reverse('app:question_comment_create', kwargs={'pk': self.question.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based_create_view(self):
        self.assertTrue(issubclass(QuestionCommentCreateView, CreateView))

    def test_anonymous_user_redirected_to_login(self):
        response = self.client.post(self.url, {'content': 'This is an anonymous comment.'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
        self.assertEqual(Comment.objects.count(), 0)

    def test_get_request_redirects_to_question_detail(self):
        self.client.login(username='bob', password='password123')
        response = self.client.get(self.url)
        self.assertRedirects(response, self.detail_url)

    def test_authenticated_user_can_create_question_comment(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': 'Great question, thanks for asking!'})

        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.content, 'Great question, thanks for asking!')
        self.assertEqual(comment.question, self.question)
        self.assertEqual(comment.author, self.comment_author)
        self.assertIsNone(comment.parent)
        self.assertTrue(comment.is_root_comment)
        self.assertRedirects(response, self.detail_url)

    def test_comment_linked_to_correct_question(self):
        other_question = Question.objects.create(
            title='Another question',
            description='Testing question association.',
            author=self.question_author
        )
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': 'Comment specifically for question 1.'})

        self.assertRedirects(response, self.detail_url)
        self.assertEqual(self.question.comments.count(), 1)
        self.assertEqual(other_question.comments.count(), 0)
        self.assertEqual(self.question.comments.first().content, 'Comment specifically for question 1.')

    def test_author_automatically_assigned_to_logged_in_user(self):
        self.client.login(username='bob', password='password123')
        # Attempt to spoof author in POST payload
        response = self.client.post(self.url, {
            'content': 'Attempting to spoof author.',
            'author': self.other_user.pk
        })
        self.assertRedirects(response, self.detail_url)
        comment = Comment.objects.get(content='Attempting to spoof author.')
        self.assertEqual(comment.author, self.comment_author)

    def test_empty_comment_validation(self):
        self.client.login(username='bob', password='password123')
        # Empty string
        response = self.client.post(self.url, {'content': ''})
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

        # Whitespace-only string
        response = self.client.post(self.url, {'content': '    \n   '})
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_successful_creation_redirects_to_question_detail(self):
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {'content': 'Checking redirect target.'})
        self.assertRedirects(response, self.detail_url)

    def test_question_comments_appear_on_question_detail_page(self):
        Comment.objects.create(
            content='Visible comment on detail page.',
            author=self.comment_author,
            question=self.question
        )
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible comment on detail page.')
        self.assertContains(response, self.comment_author.username)

    def test_nested_comment_reply_to_question_comment(self):
        parent_comment = Comment.objects.create(
            content='Parent root comment.',
            author=self.question_author,
            question=self.question
        )
        self.client.login(username='bob', password='password123')
        response = self.client.post(self.url, {
            'content': 'This is a reply to the parent comment.',
            'parent': parent_comment.pk
        })
        self.assertRedirects(response, self.detail_url)
        self.assertEqual(Comment.objects.count(), 2)

        reply = Comment.objects.get(content='This is a reply to the parent comment.')
        self.assertEqual(reply.parent, parent_comment)
        self.assertEqual(reply.question, self.question)
        self.assertEqual(reply.author, self.comment_author)
        self.assertFalse(reply.is_root_comment)

        # Check that reply appears on question detail page
        detail_response = self.client.get(self.detail_url)
        self.assertContains(detail_response, 'Parent root comment.')
        self.assertContains(detail_response, 'This is a reply to the parent comment.')

    def test_existing_question_detail_and_answer_functionality_unaffected(self):
        Answer.objects.create(
            content='Existing working answer.',
            author=self.other_user,
            question=self.question
        )
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Existing working answer.')
        self.assertContains(response, self.question.title)
        self.assertContains(response, self.question.description)
