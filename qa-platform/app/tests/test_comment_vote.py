from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from app.models import Answer, Comment, Question, Tag, Vote
from app.views import CommentVoteView
from app.views.mixins import BaseVoteView

User = get_user_model()


class CommentVoteTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='password123')
        self.voter1 = User.objects.create_user(username='voter1', password='password123')
        self.voter2 = User.objects.create_user(username='voter2', password='password123')

        self.tag = Tag.objects.create(name='django')
        self.question = Question.objects.create(
            title='How does Django comment voting work?',
            description='Question description.',
            author=self.author
        )
        self.question.tags.add(self.tag)

        self.question_comment = Comment.objects.create(
            content='Question comment content.',
            author=self.author,
            question=self.question
        )

        self.answer = Answer.objects.create(
            content='Answer content.',
            author=self.author,
            question=self.question
        )

        self.answer_comment = Comment.objects.create(
            content='Answer comment content.',
            author=self.author,
            answer=self.answer
        )

        self.reply_comment = Comment.objects.create(
            content='Reply content.',
            author=self.author,
            parent=self.question_comment
        )

    def test_view_is_class_based_and_inherits_base_vote_view(self):
        self.assertTrue(issubclass(CommentVoteView, BaseVoteView))

    def test_authenticated_user_can_upvote_question_comment(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})
        response = self.client.post(vote_url, {'value': '1'})
        expected_url = f"{reverse('app:question_detail', kwargs={'pk': self.question.pk})}#comment-{self.question_comment.pk}"
        self.assertRedirects(response, expected_url)

        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, Vote.UPVOTE)
        self.assertEqual(vote.content_object, self.question_comment)
        self.assertEqual(self.question_comment.score, 1)
        self.assertEqual(self.question_comment.upvotes_count, 1)
        self.assertEqual(self.question_comment.downvotes_count, 0)

    def test_authenticated_user_can_downvote_question_comment(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})
        response = self.client.post(vote_url, {'value': '-1'})
        expected_url = f"{reverse('app:question_detail', kwargs={'pk': self.question.pk})}#comment-{self.question_comment.pk}"
        self.assertRedirects(response, expected_url)

        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, Vote.DOWNVOTE)
        self.assertEqual(vote.content_object, self.question_comment)
        self.assertEqual(self.question_comment.score, -1)
        self.assertEqual(self.question_comment.upvotes_count, 0)
        self.assertEqual(self.question_comment.downvotes_count, 1)

    def test_authenticated_user_can_upvote_answer_comment(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.answer_comment.pk})
        response = self.client.post(vote_url, {'value': '1'})
        expected_url = f"{reverse('app:question_detail', kwargs={'pk': self.question.pk})}#comment-{self.answer_comment.pk}"
        self.assertRedirects(response, expected_url)

        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, Vote.UPVOTE)
        self.assertEqual(vote.content_object, self.answer_comment)
        self.assertEqual(self.answer_comment.score, 1)
        self.assertEqual(self.answer_comment.upvotes_count, 1)

    def test_authenticated_user_can_upvote_reply_comment(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.reply_comment.pk})
        response = self.client.post(vote_url, {'value': '1'})
        expected_url = f"{reverse('app:question_detail', kwargs={'pk': self.question.pk})}#comment-{self.reply_comment.pk}"
        self.assertRedirects(response, expected_url)

        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, Vote.UPVOTE)
        self.assertEqual(vote.content_object, self.reply_comment)
        self.assertEqual(self.reply_comment.score, 1)

    def test_user_can_cancel_vote_by_submitting_same_value(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})
        self.client.post(vote_url, {'value': '1'})
        self.assertEqual(self.question_comment.score, 1)

        self.client.post(vote_url, {'value': '1'})
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 0)
        self.assertEqual(self.question_comment.score, 0)
        self.assertEqual(self.question_comment.upvotes_count, 0)
        self.assertEqual(self.question_comment.downvotes_count, 0)

    def test_user_can_switch_vote_from_upvote_to_downvote(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})
        self.client.post(vote_url, {'value': '1'})
        self.assertEqual(self.question_comment.score, 1)

        self.client.post(vote_url, {'value': '-1'})
        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertEqual(vote.value, Vote.DOWNVOTE)
        self.assertEqual(self.question_comment.score, -1)
        self.assertEqual(self.question_comment.upvotes_count, 0)
        self.assertEqual(self.question_comment.downvotes_count, 1)

    def test_anonymous_user_redirected_to_login(self):
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})
        response = self.client.post(vote_url, {'value': '1'})
        login_url = reverse('app:login')
        self.assertRedirects(response, f"{login_url}?next={vote_url}")
        self.assertEqual(Vote.objects.count(), 0)

    def test_invalid_vote_value_redirects_without_changing_vote(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})
        expected_url = f"{reverse('app:question_detail', kwargs={'pk': self.question.pk})}#comment-{self.question_comment.pk}"

        response = self.client.post(vote_url, {'value': '2'})
        self.assertRedirects(response, expected_url)

        response = self.client.post(vote_url, {'value': 'abc'})
        self.assertRedirects(response, expected_url)
        self.assertEqual(Vote.objects.count(), 0)

    def test_voting_nonexistent_comment_returns_404(self):
        self.client.login(username='voter1', password='password123')
        vote_url = reverse('app:comment_vote', kwargs={'pk': 99999})
        response = self.client.post(vote_url, {'value': '1'})
        self.assertEqual(response.status_code, 404)

    def test_multiple_users_voting_comment(self):
        vote_url = reverse('app:comment_vote', kwargs={'pk': self.question_comment.pk})

        self.client.login(username='voter1', password='password123')
        self.client.post(vote_url, {'value': '1'})

        self.client.login(username='voter2', password='password123')
        self.client.post(vote_url, {'value': '1'})

        self.assertEqual(self.question_comment.score, 2)
        self.assertEqual(self.question_comment.upvotes_count, 2)
        self.assertEqual(self.question_comment.downvotes_count, 0)

    def test_question_detail_template_renders_vote_buttons_and_counts(self):
        Vote.objects.create(
            user=self.voter1,
            value=Vote.UPVOTE,
            content_object=self.question_comment
        )
        self.client.login(username='voter1', password='password123')
        response = self.client.get(reverse('app:question_detail', kwargs={'pk': self.question.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'id="comment-{self.question_comment.pk}"')
        self.assertContains(response, f'action="{reverse("app:comment_vote", kwargs={"pk": self.question_comment.pk})}"')
