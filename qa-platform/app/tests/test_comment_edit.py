from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.test import TestCase
from django.urls import reverse
from django.views.generic import UpdateView

from app.forms import CommentEditForm
from app.models import Answer, Comment, Question
from app.views import CommentUpdateView
from app.views.mixins import AuthorRequiredMixin

User = get_user_model()


class CommentUpdateViewTest(TestCase):
    def setUp(self):
        self.question_author = User.objects.create_user(username='alice', password='password123')
        self.answer_author = User.objects.create_user(username='bob', password='password123')
        self.comment_author = User.objects.create_user(username='charlie', password='password123')
        self.other_user = User.objects.create_user(username='david', password='password123')

        self.question = Question.objects.create(
            title='How to implement Comment Editing in Django?',
            description='We need to support editing question and answer comments.',
            author=self.question_author
        )
        self.answer = Answer.objects.create(
            content='Use a class-based UpdateView with AuthorRequiredMixin.',
            author=self.answer_author,
            question=self.question
        )

        self.question_comment = Comment.objects.create(
            content='Initial question comment.',
            author=self.comment_author,
            question=self.question
        )
        self.answer_comment = Comment.objects.create(
            content='Initial answer comment.',
            author=self.comment_author,
            answer=self.answer
        )
        self.nested_reply = Comment.objects.create(
            content='Initial nested reply.',
            author=self.comment_author,
            parent=self.question_comment,
            question=self.question
        )

        self.question_comment_url = reverse('app:comment_edit', kwargs={'pk': self.question_comment.pk})
        self.answer_comment_url = reverse('app:comment_edit', kwargs={'pk': self.answer_comment.pk})
        self.nested_reply_url = reverse('app:comment_edit', kwargs={'pk': self.nested_reply.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})

    def test_view_is_class_based_update_view(self):
        self.assertTrue(issubclass(CommentUpdateView, UpdateView))
        self.assertTrue(issubclass(CommentUpdateView, LoginRequiredMixin))
        self.assertTrue(issubclass(CommentUpdateView, AuthorRequiredMixin))

    def test_anonymous_user_redirected_to_login(self):
        # GET request
        response_get = self.client.get(self.question_comment_url)
        self.assertEqual(response_get.status_code, 302)
        self.assertIn('/accounts/login/', response_get.url)

        # POST request
        response_post = self.client.post(self.question_comment_url, {'content': 'Hacked content'})
        self.assertEqual(response_post.status_code, 302)
        self.assertIn('/accounts/login/', response_post.url)

        self.question_comment.refresh_from_db()
        self.assertEqual(self.question_comment.content, 'Initial question comment.')

    def test_non_owner_cannot_access_or_edit_comment(self):
        self.client.login(username='david', password='password123')

        # GET request returns 403
        response_get = self.client.get(self.question_comment_url)
        self.assertEqual(response_get.status_code, 403)

        # POST request returns 403
        response_post = self.client.post(self.question_comment_url, {'content': 'Unauthorized edit'})
        self.assertEqual(response_post.status_code, 403)

        self.question_comment.refresh_from_db()
        self.assertEqual(self.question_comment.content, 'Initial question comment.')

    def test_owner_can_edit_question_comment(self):
        self.client.login(username='charlie', password='password123')

        # GET edit page
        response_get = self.client.get(self.question_comment_url)
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'comments/comment_edit.html')
        self.assertContains(response_get, 'Initial question comment.')

        # POST updated content
        response_post = self.client.post(self.question_comment_url, {'content': 'Updated question comment.'})
        self.assertRedirects(response_post, self.detail_url)

        self.question_comment.refresh_from_db()
        self.assertEqual(self.question_comment.content, 'Updated question comment.')
        self.assertEqual(self.question_comment.author, self.comment_author)
        self.assertEqual(self.question_comment.question, self.question)

    def test_owner_can_edit_answer_comment(self):
        self.client.login(username='charlie', password='password123')

        # GET edit page
        response_get = self.client.get(self.answer_comment_url)
        self.assertEqual(response_get.status_code, 200)
        self.assertTemplateUsed(response_get, 'comments/comment_edit.html')
        self.assertContains(response_get, 'Initial answer comment.')

        # POST updated content
        response_post = self.client.post(self.answer_comment_url, {'content': 'Updated answer comment.'})
        self.assertRedirects(response_post, self.detail_url)

        self.answer_comment.refresh_from_db()
        self.assertEqual(self.answer_comment.content, 'Updated answer comment.')
        self.assertEqual(self.answer_comment.author, self.comment_author)
        self.assertEqual(self.answer_comment.answer, self.answer)

    def test_owner_can_edit_nested_comment_reply(self):
        self.client.login(username='charlie', password='password123')

        response_post = self.client.post(self.nested_reply_url, {'content': 'Updated nested reply.'})
        self.assertRedirects(response_post, self.detail_url)

        self.nested_reply.refresh_from_db()
        self.assertEqual(self.nested_reply.content, 'Updated nested reply.')
        self.assertEqual(self.nested_reply.parent, self.question_comment)
        self.assertEqual(self.nested_reply.author, self.comment_author)

    def test_comment_author_remains_unchanged(self):
        self.client.login(username='charlie', password='password123')

        # Attempt to spoof author in POST payload
        response = self.client.post(self.question_comment_url, {
            'content': 'Attempting author change.',
            'author': self.other_user.pk
        })
        self.assertRedirects(response, self.detail_url)

        self.question_comment.refresh_from_db()
        self.assertEqual(self.question_comment.author, self.comment_author)

    def test_empty_and_whitespace_comment_validation(self):
        self.client.login(username='charlie', password='password123')

        # Empty string
        response_empty = self.client.post(self.question_comment_url, {'content': ''})
        self.assertEqual(response_empty.status_code, 200)
        self.assertFormError(response_empty.context['form'], 'content', 'This field is required.')

        # Whitespace-only string
        response_whitespace = self.client.post(self.question_comment_url, {'content': '    \n   '})
        self.assertEqual(response_whitespace.status_code, 200)
        self.assertFormError(response_whitespace.context['form'], 'content', 'This field is required.')

        self.question_comment.refresh_from_db()
        self.assertEqual(self.question_comment.content, 'Initial question comment.')



    def test_edit_option_visibility_on_question_detail(self):
        # 1. Owner logged in: Inline edit button and form should be visible
        self.client.login(username='charlie', password='password123')
        owner_response = self.client.get(self.detail_url)
        self.assertEqual(owner_response.status_code, 200)
        self.assertContains(owner_response, reverse('app:comment_edit', kwargs={'pk': self.question_comment.pk}))
        self.assertContains(owner_response, reverse('app:comment_edit', kwargs={'pk': self.answer_comment.pk}))
        self.assertContains(owner_response, reverse('app:comment_edit', kwargs={'pk': self.nested_reply.pk}))
        self.assertContains(owner_response, f'id="comment-edit-form-{self.question_comment.pk}"')
        self.assertContains(owner_response, f'id="comment-edit-form-{self.answer_comment.pk}"')
        self.assertContains(owner_response, f'id="comment-edit-form-{self.nested_reply.pk}"')
        self.assertContains(owner_response, f"toggleCommentEdit('{self.question_comment.pk}')")
        self.assertContains(owner_response, f"toggleCommentEdit('{self.answer_comment.pk}')")
        self.assertContains(owner_response, f"toggleCommentEdit('{self.nested_reply.pk}')")

        # 2. Non-owner logged in: Inline edit button and form should NOT be visible
        self.client.login(username='david', password='password123')
        non_owner_response = self.client.get(self.detail_url)
        self.assertEqual(non_owner_response.status_code, 200)
        self.assertNotContains(non_owner_response, reverse('app:comment_edit', kwargs={'pk': self.question_comment.pk}))
        self.assertNotContains(non_owner_response, reverse('app:comment_edit', kwargs={'pk': self.answer_comment.pk}))
        self.assertNotContains(non_owner_response, reverse('app:comment_edit', kwargs={'pk': self.nested_reply.pk}))
        self.assertNotContains(non_owner_response, f'id="comment-edit-form-{self.question_comment.pk}"')
        self.assertNotContains(non_owner_response, f'id="comment-edit-form-{self.answer_comment.pk}"')
        self.assertNotContains(non_owner_response, f'id="comment-edit-form-{self.nested_reply.pk}"')
        self.assertNotContains(non_owner_response, f"toggleCommentEdit('{self.question_comment.pk}')")

        # 3. Anonymous user: Inline edit button and form should NOT be visible
        self.client.logout()
        anon_response = self.client.get(self.detail_url)
        self.assertEqual(anon_response.status_code, 200)
        self.assertNotContains(anon_response, reverse('app:comment_edit', kwargs={'pk': self.question_comment.pk}))
        self.assertNotContains(anon_response, reverse('app:comment_edit', kwargs={'pk': self.answer_comment.pk}))
        self.assertNotContains(anon_response, reverse('app:comment_edit', kwargs={'pk': self.nested_reply.pk}))
        self.assertNotContains(anon_response, f'id="comment-edit-form-{self.question_comment.pk}"')
        self.assertNotContains(anon_response, f'id="comment-edit-form-{self.answer_comment.pk}"')
        self.assertNotContains(anon_response, f'id="comment-edit-form-{self.nested_reply.pk}"')
        self.assertNotContains(anon_response, f"toggleCommentEdit('{self.question_comment.pk}')")

    def test_existing_question_and_answer_comments_unaffected(self):
        self.client.login(username='charlie', password='password123')

        # Adding a new question comment still works
        q_comment_url = reverse('app:question_comment_create', kwargs={'pk': self.question.pk})
        res_q = self.client.post(q_comment_url, {'content': 'Brand new question comment.'})
        self.assertRedirects(res_q, self.detail_url)
        self.assertTrue(Comment.objects.filter(content='Brand new question comment.').exists())

        # Adding a new answer comment still works
        a_comment_url = reverse('app:answer_comment_create', kwargs={'pk': self.answer.pk})
        res_a = self.client.post(a_comment_url, {'content': 'Brand new answer comment.'})
        self.assertRedirects(res_a, self.detail_url)
        self.assertTrue(Comment.objects.filter(content='Brand new answer comment.').exists())
