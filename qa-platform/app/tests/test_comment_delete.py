from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.test import TestCase
from django.urls import reverse
from django.views.generic import DeleteView

from app.models import Answer, Comment, Question
from app.views import CommentDeleteView
from app.views.mixins import AuthorRequiredMixin

User = get_user_model()


class CommentDeleteViewTest(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user(username='alice', password='password123')
        self.answer_author = User.objects.create_user(username='bob', password='password123')
        self.comment_author = User.objects.create_user(username='charlie', password='password123')
        self.other_user = User.objects.create_user(username='david', password='password123')

        self.question = Question.objects.create(
            title='How to delete comments cleanly in Django?',
            description='We need to support deleting question and answer comments.',
            author=self.question_author
        )
        self.answer = Answer.objects.create(
            content='Use a class-based DeleteView with AuthorRequiredMixin.',
            author=self.answer_author,
            question=self.question
        )

        self.question_comment = Comment.objects.create(
            content='Question comment to delete.',
            author=self.comment_author,
            question=self.question
        )
        self.answer_comment = Comment.objects.create(
            content='Answer comment to delete.',
            author=self.comment_author,
            answer=self.answer
        )
        self.nested_reply = Comment.objects.create(
            content='Nested reply to delete.',
            author=self.comment_author,
            parent=self.question_comment,
            question=self.question
        )

        self.q_delete_url = reverse('app:comment_delete', kwargs={'pk': self.question_comment.pk})
        self.a_delete_url = reverse('app:comment_delete', kwargs={'pk': self.answer_comment.pk})
        self.reply_delete_url = reverse('app:comment_delete', kwargs={'pk': self.nested_reply.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_delete_view_with_required_mixins(self):
        self.assertTrue(issubclass(CommentDeleteView, DeleteView))
        self.assertTrue(issubclass(CommentDeleteView, LoginRequiredMixin))
        self.assertTrue(issubclass(CommentDeleteView, AuthorRequiredMixin))

    def test_anonymous_user_redirected_to_login(self):
        # Anonymous GET
        response_get = self.client.get(self.q_delete_url)
        self.assertEqual(response_get.status_code, 302)
        self.assertIn('/accounts/login/', response_get.url)

        # Anonymous POST
        response_post = self.client.post(self.q_delete_url)
        self.assertEqual(response_post.status_code, 302)
        self.assertIn('/accounts/login/', response_post.url)

        self.assertTrue(Comment.objects.filter(pk=self.question_comment.pk).exists())

    def test_non_owner_cannot_delete_comment(self):
        self.client.login(username='david', password='password123')

        # GET by non-owner returns 403
        response_get = self.client.get(self.q_delete_url)
        self.assertEqual(response_get.status_code, 403)

        # POST by non-owner returns 403
        response_post = self.client.post(self.q_delete_url)
        self.assertEqual(response_post.status_code, 403)

        self.assertTrue(Comment.objects.filter(pk=self.question_comment.pk).exists())

    def test_owner_can_access_delete_confirmation_question_comment(self):
        self.client.login(username='charlie', password='password123')

        response = self.client.get(self.q_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comments/comment_confirm_delete.html')
        self.assertContains(response, 'Question comment to delete.')
        self.assertContains(response, self.question.title)

        # Confirm comment was NOT deleted by GET
        self.assertTrue(Comment.objects.filter(pk=self.question_comment.pk).exists())

    def test_owner_can_access_delete_confirmation_answer_comment(self):
        self.client.login(username='charlie', password='password123')

        response = self.client.get(self.a_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'comments/comment_confirm_delete.html')
        self.assertContains(response, 'Answer comment to delete.')

        # Confirm comment was NOT deleted by GET
        self.assertTrue(Comment.objects.filter(pk=self.answer_comment.pk).exists())

    def test_get_request_never_deletes_comment(self):
        self.client.login(username='charlie', password='password123')

        initial_count = Comment.objects.count()
        response = self.client.get(self.q_delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), initial_count)
        self.assertTrue(Comment.objects.filter(pk=self.question_comment.pk).exists())

    def test_owner_successful_post_deletes_question_comment(self):
        self.client.login(username='charlie', password='password123')

        response = self.client.post(self.q_delete_url)
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Comment.objects.filter(pk=self.question_comment.pk).exists())

    def test_owner_successful_post_deletes_answer_comment(self):
        self.client.login(username='charlie', password='password123')

        response = self.client.post(self.a_delete_url)
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Comment.objects.filter(pk=self.answer_comment.pk).exists())

    def test_owner_successful_post_deletes_nested_reply(self):
        self.client.login(username='charlie', password='password123')

        response = self.client.post(self.reply_delete_url)
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Comment.objects.filter(pk=self.nested_reply.pk).exists())
        # Parent question comment still exists
        self.assertTrue(Comment.objects.filter(pk=self.question_comment.pk).exists())

    def test_deleting_parent_comment_cascades_to_replies(self):
        self.client.login(username='charlie', password='password123')

        # When question_comment is deleted, nested_reply should also be removed
        response = self.client.post(self.q_delete_url)
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(Comment.objects.filter(pk=self.question_comment.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=self.nested_reply.pk).exists())

    def test_delete_option_visibility_on_question_detail(self):
        # 1. Comment author: Delete button and modal should be visible
        self.client.login(username='charlie', password='password123')
        owner_response = self.client.get(self.detail_url)
        self.assertEqual(owner_response.status_code, 200)
        self.assertContains(owner_response, self.q_delete_url)
        self.assertContains(owner_response, self.a_delete_url)
        self.assertContains(owner_response, self.reply_delete_url)
        self.assertContains(owner_response, f'id="delete-comment-modal-{self.question_comment.pk}"')
        self.assertContains(owner_response, f'id="delete-comment-modal-{self.answer_comment.pk}"')
        self.assertContains(owner_response, f'id="delete-comment-modal-{self.nested_reply.pk}"')

        # 2. Non-owner: Delete button and modal should NOT be visible
        self.client.login(username='david', password='password123')
        non_owner_response = self.client.get(self.detail_url)
        self.assertEqual(non_owner_response.status_code, 200)
        self.assertNotContains(non_owner_response, self.q_delete_url)
        self.assertNotContains(non_owner_response, self.a_delete_url)
        self.assertNotContains(non_owner_response, self.reply_delete_url)
        self.assertNotContains(non_owner_response, f'id="delete-comment-modal-{self.question_comment.pk}"')
        self.assertNotContains(non_owner_response, f'id="delete-comment-modal-{self.answer_comment.pk}"')
        self.assertNotContains(non_owner_response, f'id="delete-comment-modal-{self.nested_reply.pk}"')

        # 3. Anonymous visitor: Delete button and modal should NOT be visible
        self.client.logout()
        anon_response = self.client.get(self.detail_url)
        self.assertEqual(anon_response.status_code, 200)
        self.assertNotContains(anon_response, self.q_delete_url)
        self.assertNotContains(anon_response, self.a_delete_url)
        self.assertNotContains(anon_response, self.reply_delete_url)
        self.assertNotContains(anon_response, f'id="delete-comment-modal-{self.question_comment.pk}"')
        self.assertNotContains(anon_response, f'id="delete-comment-modal-{self.answer_comment.pk}"')
        self.assertNotContains(anon_response, f'id="delete-comment-modal-{self.nested_reply.pk}"')

    def test_existing_comment_creation_and_editing_still_works(self):
        self.client.login(username='charlie', password='password123')

        # Creation on Question
        create_q_url = reverse('app:question_comment_create', kwargs={'pk': self.question.pk})
        res_q = self.client.post(create_q_url, {'content': 'Another comment.'})
        self.assertRedirects(res_q, self.detail_url)
        new_comment = Comment.objects.get(content='Another comment.')

        # Editing the new comment
        edit_url = reverse('app:comment_edit', kwargs={'pk': new_comment.pk})
        res_edit = self.client.post(edit_url, {'content': 'Edited another comment.'})
        self.assertRedirects(res_edit, self.detail_url)
        new_comment.refresh_from_db()
        self.assertEqual(new_comment.content, 'Edited another comment.')
