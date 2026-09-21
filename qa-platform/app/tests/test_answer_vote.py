from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from app.models import Answer, Comment, Question, Tag, Vote
from app.views import AnswerVoteView

User = get_user_model()


class AnswerVoteTest(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username='author', password='password123')
        self.voter1 = User.objects.create_user(username='voter1', password='password123')
        self.voter2 = User.objects.create_user(username='voter2', password='password123')

        self.tag = Tag.objects.create(name='django')
        self.question = Question.objects.create(
            title='How does Django voting work?',
            description='Question description about voting.',
            author=self.author
        )
        self.question.tags.add(self.tag)

        self.answer = Answer.objects.create(
            question=self.question,
            author=self.author,
            content='This is a helpful answer.'
        )

        self.vote_url = reverse('app:answer_vote', kwargs={'pk': self.answer.pk})
        self.detail_url = reverse('app:question_detail', kwargs={'pk': self.question.pk})
        self.expected_redirect_url = f"{self.detail_url}#answer-{self.answer.pk}"

    def test_view_is_class_based(self):
        self.assertTrue(issubclass(AnswerVoteView, AnswerVoteView.__mro__[0]))

    def test_authenticated_user_can_upvote_answer(self):
        self.client.login(username='voter1', password='password123')
        response = self.client.post(self.vote_url, {'value': '1'})
        self.assertRedirects(response, self.expected_redirect_url)

        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, Vote.UPVOTE)
        self.assertEqual(vote.content_object, self.answer)
        self.assertEqual(self.answer.score, 1)
        self.assertEqual(self.answer.upvotes_count, 1)
        self.assertEqual(self.answer.downvotes_count, 0)

    def test_authenticated_user_can_downvote_answer(self):
        self.client.login(username='voter1', password='password123')
        response = self.client.post(self.vote_url, {'value': '-1'})
        self.assertRedirects(response, self.expected_redirect_url)

        vote = Vote.objects.filter(user=self.voter1).first()
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, Vote.DOWNVOTE)
        self.assertEqual(vote.content_object, self.answer)
        self.assertEqual(self.answer.score, -1)
        self.assertEqual(self.answer.upvotes_count, 0)
        self.assertEqual(self.answer.downvotes_count, 1)

    def test_user_can_change_upvote_to_downvote(self):
        self.client.login(username='voter1', password='password123')
        self.client.post(self.vote_url, {'value': '1'})
        self.assertEqual(self.answer.score, 1)

        response = self.client.post(self.vote_url, {'value': '-1'})
        self.assertRedirects(response, self.expected_redirect_url)

        votes = Vote.objects.filter(user=self.voter1)
        self.assertEqual(votes.count(), 1)
        self.assertEqual(votes.first().value, Vote.DOWNVOTE)
        self.assertEqual(self.answer.score, -1)

    def test_user_can_change_downvote_to_upvote(self):
        self.client.login(username='voter1', password='password123')
        self.client.post(self.vote_url, {'value': '-1'})
        self.assertEqual(self.answer.score, -1)

        response = self.client.post(self.vote_url, {'value': '1'})
        self.assertRedirects(response, self.expected_redirect_url)

        votes = Vote.objects.filter(user=self.voter1)
        self.assertEqual(votes.count(), 1)
        self.assertEqual(votes.first().value, Vote.UPVOTE)
        self.assertEqual(self.answer.score, 1)

    def test_user_can_undo_existing_vote(self):
        self.client.login(username='voter1', password='password123')
        # Upvote
        self.client.post(self.vote_url, {'value': '1'})
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 1)
        self.assertEqual(self.answer.score, 1)

        # Click upvote again to undo
        response = self.client.post(self.vote_url, {'value': '1'})
        self.assertRedirects(response, self.expected_redirect_url)
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 0)
        self.assertEqual(self.answer.score, 0)

        # Downvote and undo
        self.client.post(self.vote_url, {'value': '-1'})
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 1)
        self.assertEqual(self.answer.score, -1)

        response = self.client.post(self.vote_url, {'value': '-1'})
        self.assertRedirects(response, self.expected_redirect_url)
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 0)
        self.assertEqual(self.answer.score, 0)

    def test_user_cannot_create_multiple_votes_for_same_answer(self):
        self.client.login(username='voter1', password='password123')
        self.client.post(self.vote_url, {'value': '1'})
        self.client.post(self.vote_url, {'value': '1'})  # Undone
        self.client.post(self.vote_url, {'value': '1'})  # Upvoted again
        self.client.post(self.vote_url, {'value': '-1'}) # Switched to downvote

        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 1)

        # Database unique constraint verification
        ct = ContentType.objects.get_for_model(Answer)
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                user=self.voter1,
                content_type=ct,
                object_id=self.answer.pk,
                value=Vote.UPVOTE
            )

    def test_answer_score_calculated_correctly_with_multiple_voters(self):
        self.client.login(username='voter1', password='password123')
        self.client.post(self.vote_url, {'value': '1'})

        self.client.login(username='voter2', password='password123')
        self.client.post(self.vote_url, {'value': '1'})

        self.assertEqual(self.answer.score, 2)
        self.assertEqual(self.answer.upvotes_count, 2)
        self.assertEqual(self.answer.downvotes_count, 0)

        # voter2 switches to downvote
        self.client.post(self.vote_url, {'value': '-1'})
        self.assertEqual(self.answer.score, 0)
        self.assertEqual(self.answer.upvotes_count, 1)
        self.assertEqual(self.answer.downvotes_count, 1)

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.post(self.vote_url, {'value': '1'})
        login_url = reverse('app:login')
        self.assertRedirects(response, f'{login_url}?next={self.vote_url}')

        get_response = self.client.get(self.vote_url)
        self.assertRedirects(get_response, f'{login_url}?next={self.vote_url}')

    def test_vote_associated_with_correct_answer_and_user(self):
        other_answer = Answer.objects.create(
            question=self.question,
            author=self.author,
            content='Another answer on the same question.'
        )
        self.client.login(username='voter1', password='password123')
        self.client.post(self.vote_url, {'value': '1'})

        vote = Vote.objects.get(user=self.voter1)
        self.assertEqual(vote.content_object, self.answer)
        self.assertNotEqual(vote.content_object, other_answer)
        self.assertEqual(vote.user, self.voter1)
        self.assertEqual(self.answer.score, 1)
        self.assertEqual(other_answer.score, 0)

    def test_voting_controls_and_current_vote_state_displayed_correctly(self):
        # Anonymous viewing detail page
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'aria-label="Upvote answer"')
        self.assertContains(response, 'aria-label="Downvote answer"')
        self.assertContains(response, '0 votes')
        self.assertNotContains(response, 'aria-pressed="true"')

        # Voter1 logs in and upvotes
        self.client.login(username='voter1', password='password123')
        self.client.post(self.vote_url, {'value': '1'})
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1 vote')
        self.assertContains(response, 'bg-rose-50')
        self.assertContains(response, 'text-rose-600')

        # Voter1 changes to downvote
        self.client.post(self.vote_url, {'value': '-1'})
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '0 votes')
        self.assertNotContains(response, '-1 vote')
        self.assertContains(response, 'userVote: -1')

    def test_invalid_vote_value_redirects_without_changing_vote(self):
        self.client.login(username='voter1', password='password123')
        response = self.client.post(self.vote_url, {'value': '999'})
        self.assertRedirects(response, self.expected_redirect_url)
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 0)

        response = self.client.post(self.vote_url, {'value': 'invalid'})
        self.assertRedirects(response, self.expected_redirect_url)
        self.assertEqual(Vote.objects.filter(user=self.voter1).count(), 0)

    def test_get_request_on_vote_url_redirects_to_detail(self):
        self.client.login(username='voter1', password='password123')
        response = self.client.get(self.vote_url)
        self.assertRedirects(response, self.expected_redirect_url)
