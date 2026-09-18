from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.models import Answer, Comment, Question, Tag, Vote

User = get_user_model()


class AjaxVoteTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='password123')
        self.voter = User.objects.create_user(username='voter', password='password123')

        self.tag = Tag.objects.create(name='django')
        self.question = Question.objects.create(
            title='How does AJAX voting work?',
            description='Question description for async testing.',
            author=self.author
        )
        self.question.tags.add(self.tag)

        self.answer = Answer.objects.create(
            question=self.question,
            author=self.author,
            content='This is a helpful answer.'
        )

        self.comment = Comment.objects.create(
            question=self.question,
            author=self.author,
            content='This is a comment.'
        )

        self.question_vote_url = reverse('app:question_vote', kwargs={'pk': self.question.pk})
        self.answer_vote_url = reverse('app:answer_vote', kwargs={'pk': self.answer.pk})
        self.comment_vote_url = reverse('app:comment_vote', kwargs={'pk': self.comment.pk})

    def test_ajax_upvote_question_returns_json_200(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.question_vote_url,
            {'value': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['score'], 1)
        self.assertEqual(data['upvotes_count'], 1)
        self.assertEqual(data['downvotes_count'], 0)
        self.assertEqual(data['user_vote'], 1)

    def test_ajax_downvote_question_returns_json_200(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.question_vote_url,
            {'value': '-1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['score'], -1)
        self.assertEqual(data['upvotes_count'], 0)
        self.assertEqual(data['downvotes_count'], 1)
        self.assertEqual(data['user_vote'], -1)

    def test_ajax_toggle_vote_off_returns_null_user_vote(self):
        self.client.login(username='voter', password='password123')
        # First upvote
        self.client.post(
            self.question_vote_url,
            {'value': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        # Second upvote cancels the vote
        response = self.client.post(
            self.question_vote_url,
            {'value': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['score'], 0)
        self.assertEqual(data['upvotes_count'], 0)
        self.assertEqual(data['downvotes_count'], 0)
        self.assertIsNone(data['user_vote'])
        self.assertEqual(Vote.objects.count(), 0)

    def test_ajax_upvote_answer_returns_json_200(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.answer_vote_url,
            {'value': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['score'], 1)
        self.assertEqual(data['upvotes_count'], 1)
        self.assertEqual(data['downvotes_count'], 0)
        self.assertEqual(data['user_vote'], 1)

    def test_ajax_upvote_comment_returns_json_200(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.comment_vote_url,
            {'value': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['score'], 1)
        self.assertEqual(data['upvotes_count'], 1)
        self.assertEqual(data['downvotes_count'], 0)
        self.assertEqual(data['user_vote'], 1)

    def test_ajax_accept_header_returns_json(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.question_vote_url,
            {'value': '1'},
            HTTP_ACCEPT='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['user_vote'], 1)

    def test_ajax_unauthenticated_user_returns_401(self):
        response = self.client.post(
            self.question_vote_url,
            {'value': '1'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data['error'], 'unauthenticated')
        self.assertIn('login', data['login_url'])
        self.assertIn(self.question_vote_url, data['login_url'])

    def test_ajax_invalid_vote_value_returns_400(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.question_vote_url,
            {'value': 'invalid_value'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['error'], 'Invalid vote value')
        self.assertEqual(Vote.objects.count(), 0)

    def test_non_ajax_post_still_redirects(self):
        self.client.login(username='voter', password='password123')
        response = self.client.post(
            self.question_vote_url,
            {'value': '1'}
        )
        expected_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})
        self.assertRedirects(response, expected_url)
