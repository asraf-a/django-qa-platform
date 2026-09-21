from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.models import Answer, Comment, Question

User = get_user_model()


class FlashMessagesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='author', password='password123')
        self.client.login(username='author', password='password123')
        self.question = Question.objects.create(
            title='Sample Question',
            description='Sample description',
            author=self.user
        )

    def test_question_crud_flash_messages(self):
        # Create question
        res_create = self.client.post(reverse('app:question_create'), {
            'title': 'New Question',
            'description': 'New description'
        }, follow=True)
        self.assertContains(res_create, 'Question created successfully.')

        # Update question
        res_update = self.client.post(reverse('app:question_edit', kwargs={'pk': self.question.pk}), {
            'title': 'Updated Title',
            'description': 'Updated description'
        }, follow=True)
        self.assertContains(res_update, 'Question updated successfully.')

        # Delete question
        res_delete = self.client.post(reverse('app:question_delete', kwargs={'pk': self.question.pk}), follow=True)
        self.assertContains(res_delete, 'Question deleted successfully.')

    def test_answer_crud_flash_messages(self):
        # Create answer
        res_create = self.client.post(reverse('app:answer_create', kwargs={'pk': self.question.pk}), {
            'content': 'Valid answer content'
        }, follow=True)
        self.assertContains(res_create, 'Answer posted successfully.')
        answer = Answer.objects.filter(question=self.question).first()

        # Update answer
        res_update = self.client.post(reverse('app:answer_edit', kwargs={'pk': answer.pk}), {
            'content': 'Updated answer content'
        }, follow=True)
        self.assertContains(res_update, 'Answer updated successfully.')

        # Delete answer
        res_delete = self.client.post(reverse('app:answer_delete', kwargs={'pk': answer.pk}), follow=True)
        self.assertContains(res_delete, 'Answer deleted successfully.')

    def test_comment_crud_flash_messages(self):
        # Create comment
        res_create = self.client.post(reverse('app:question_comment_create', kwargs={'pk': self.question.pk}), {
            'content': 'Valid question comment'
        }, follow=True)
        self.assertContains(res_create, 'Comment added successfully.')
        comment = Comment.objects.filter(question=self.question).first()

        # Update comment
        res_update = self.client.post(reverse('app:comment_edit', kwargs={'pk': comment.pk}), {
            'content': 'Updated comment content'
        }, follow=True)
        self.assertContains(res_update, 'Comment updated successfully.')

        # Delete comment
        res_delete = self.client.post(reverse('app:comment_delete', kwargs={'pk': comment.pk}), follow=True)
        self.assertContains(res_delete, 'Comment deleted successfully.')

    def test_messages_container_renders_alert_and_dismiss_button(self):
        # When a message is flashed, verify container structure
        response = self.client.post(reverse('app:question_create'), {
            'title': 'Another Question',
            'description': 'Another description'
        }, follow=True)
        self.assertContains(response, 'id="messages-container"')
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, 'aria-label="Close notification"')

    def test_no_messages_container_when_no_messages(self):
        # Clean GET request without messages
        response = self.client.get(reverse('app:question_list'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="messages-container"')
