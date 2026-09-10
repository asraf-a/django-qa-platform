from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from app.models import Answer, Comment, Question, Tag, Vote

User = get_user_model()


class TagModelTest(TestCase):
    def test_tag_creation_and_slug_generation(self):
        tag = Tag.objects.create(name='Django Web')
        self.assertEqual(tag.slug, 'django-web')
        self.assertEqual(str(tag), 'Django Web')

    def test_tag_case_insensitive_validation(self):
        Tag.objects.create(name='Python')
        duplicate_tag = Tag(name='python')
        with self.assertRaises(ValidationError):
            duplicate_tag.full_clean()

    def test_tag_case_insensitive_db_constraint(self):
        Tag.objects.create(name='Python')
        with self.assertRaises(IntegrityError):
            Tag.objects.create(name='python')

    def test_tag_slug_collision_resolution(self):
        tag1 = Tag.objects.create(name='tag')
        tag2 = Tag.objects.create(name='tag!')  # slugifies to 'tag'
        self.assertEqual(tag1.slug, 'tag')
        self.assertEqual(tag2.slug, 'tag-1')


class QuestionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.tag = Tag.objects.create(name='django')

    def test_question_creation(self):
        question = Question.objects.create(
            title='How to use Django models?',
            description='I want to understand Django ORM.',
            author=self.user
        )
        question.tags.add(self.tag)
        self.assertEqual(str(question), 'How to use Django models?')
        self.assertEqual(question.tags.count(), 1)
        self.assertEqual(question.score, 0)
        self.assertEqual(question.upvotes_count, 0)
        self.assertEqual(question.downvotes_count, 0)

    def test_question_ordering(self):
        q1 = Question.objects.create(title='Q1', description='Desc 1', author=self.user)
        q2 = Question.objects.create(title='Q2', description='Desc 2', author=self.user)
        questions = list(Question.objects.all())
        self.assertEqual(questions, [q2, q1])  # Ordered by -created_at


class AnswerModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='answerer', password='password123')
        self.question = Question.objects.create(
            title='Sample Question',
            description='Sample question description',
            author=self.user
        )

    def test_answer_creation_and_cascade(self):
        answer = Answer.objects.create(
            question=self.question,
            author=self.user,
            content='Here is the answer.'
        )
        self.assertEqual(answer.question, self.question)
        self.assertEqual(answer.score, 0)

        # Deleting question should cascade delete the answer
        self.question.delete()
        self.assertFalse(Answer.objects.filter(pk=answer.pk).exists())


class CommentModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='commenter', password='password123')
        self.question = Question.objects.create(
            title='Question for comment test',
            description='Desc',
            author=self.user
        )
        self.answer = Answer.objects.create(
            question=self.question,
            author=self.user,
            content='Answer for comment test'
        )

    def test_direct_question_comment(self):
        comment = Comment(
            author=self.user,
            content='This is a comment on question',
            question=self.question
        )
        comment.full_clean()
        comment.save()
        self.assertTrue(comment.is_root_comment)
        self.assertEqual(comment.get_root_target(), self.question)
        self.assertEqual(comment.get_depth(), 0)

    def test_direct_answer_comment(self):
        comment = Comment(
            author=self.user,
            content='This is a comment on answer',
            answer=self.answer
        )
        comment.full_clean()
        comment.save()
        self.assertTrue(comment.is_root_comment)
        self.assertEqual(comment.get_root_target(), self.answer)
        self.assertEqual(comment.get_depth(), 0)

    def test_comment_validation_neither_target(self):
        comment = Comment(author=self.user, content='No target')
        with self.assertRaises(ValidationError):
            comment.full_clean()

    def test_comment_validation_both_targets(self):
        comment = Comment(
            author=self.user,
            content='Both targets',
            question=self.question,
            answer=self.answer
        )
        with self.assertRaises(ValidationError):
            comment.full_clean()

    def test_comment_db_constraint_neither_target(self):
        with self.assertRaises(IntegrityError):
            Comment.objects.create(author=self.user, content='No target in DB')

    def test_comment_db_constraint_both_targets(self):
        with self.assertRaises(IntegrityError):
            Comment.objects.create(
                author=self.user,
                content='Both targets in DB',
                question=self.question,
                answer=self.answer
            )

    def test_threaded_reply_to_question_comment(self):
        parent_comment = Comment.objects.create(
            author=self.user,
            content='Root comment on question',
            question=self.question
        )
        reply = Comment(
            author=self.user,
            content='Reply to comment',
            parent=parent_comment
        )
        reply.full_clean()
        reply.save()

        self.assertFalse(reply.is_root_comment)
        self.assertEqual(reply.question, self.question)
        self.assertIsNone(reply.answer)
        self.assertEqual(reply.get_root_target(), self.question)
        self.assertEqual(reply.get_depth(), 1)
        self.assertEqual(reply.get_root_comment(), parent_comment)

    def test_threaded_reply_to_answer_comment(self):
        parent_comment = Comment.objects.create(
            author=self.user,
            content='Root comment on answer',
            answer=self.answer
        )
        reply = Comment(
            author=self.user,
            content='Reply to answer comment',
            parent=parent_comment
        )
        reply.full_clean()
        reply.save()

        self.assertFalse(reply.is_root_comment)
        self.assertEqual(reply.answer, self.answer)
        self.assertIsNone(reply.question)
        self.assertEqual(reply.get_root_target(), self.answer)
        self.assertEqual(reply.get_depth(), 1)

    def test_multi_level_nested_replies(self):
        root = Comment.objects.create(
            author=self.user,
            content='Level 0',
            question=self.question
        )
        level1 = Comment.objects.create(
            author=self.user,
            content='Level 1',
            parent=root
        )
        level2 = Comment.objects.create(
            author=self.user,
            content='Level 2',
            parent=level1
        )
        level3 = Comment.objects.create(
            author=self.user,
            content='Level 3',
            parent=level2
        )

        self.assertEqual(level3.get_depth(), 3)
        self.assertEqual(level3.get_root_comment(), root)
        self.assertEqual(level3.get_root_target(), self.question)
        self.assertEqual(level3.question, self.question)

    def test_cross_target_validation_error(self):
        root = Comment.objects.create(
            author=self.user,
            content='Question comment',
            question=self.question
        )
        # Attempting to reply to a question comment while specifying an answer target
        invalid_reply = Comment(
            author=self.user,
            content='Invalid reply target',
            parent=root,
            answer=self.answer
        )
        with self.assertRaises(ValidationError):
            invalid_reply.full_clean()

    def test_mismatched_target_validation_error(self):
        q2 = Question.objects.create(title='Q2', description='D2', author=self.user)
        root = Comment.objects.create(
            author=self.user,
            content='Question 1 comment',
            question=self.question
        )
        mismatched_reply = Comment(
            author=self.user,
            content='Mismatched reply',
            parent=root,
            question=q2
        )
        with self.assertRaises(ValidationError):
            mismatched_reply.full_clean()

    def test_self_parenting_validation_error(self):
        comment = Comment.objects.create(
            author=self.user,
            content='Self parent test',
            question=self.question
        )
        comment.parent = comment
        with self.assertRaises(ValidationError):
            comment.full_clean()

    def test_cascade_delete_comments(self):
        root = Comment.objects.create(author=self.user, content='Root', question=self.question)
        reply = Comment.objects.create(author=self.user, content='Reply', parent=root)

        self.question.delete()
        self.assertFalse(Comment.objects.filter(pk=root.pk).exists())
        self.assertFalse(Comment.objects.filter(pk=reply.pk).exists())


class VoteModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='voter1', password='password123')
        self.user2 = User.objects.create_user(username='voter2', password='password123')
        self.question = Question.objects.create(
            title='Votable Question',
            description='Description',
            author=self.user1
        )
        self.answer = Answer.objects.create(
            question=self.question,
            author=self.user1,
            content='Votable Answer'
        )
        self.comment = Comment.objects.create(
            author=self.user1,
            content='Votable Comment',
            question=self.question
        )

    def test_voting_on_question(self):
        ct = ContentType.objects.get_for_model(Question)
        # Upvote
        vote = Vote.objects.create(
            user=self.user1,
            content_type=ct,
            object_id=self.question.pk,
            value=Vote.UPVOTE
        )
        self.assertEqual(self.question.score, 1)
        self.assertEqual(self.question.upvotes_count, 1)
        self.assertEqual(self.question.downvotes_count, 0)

        # Vote change: change to downvote
        vote.value = Vote.DOWNVOTE
        vote.save()
        self.assertEqual(self.question.score, -1)
        self.assertEqual(self.question.upvotes_count, 0)
        self.assertEqual(self.question.downvotes_count, 1)

        # Vote removal (undo)
        vote.delete()
        self.assertEqual(self.question.score, 0)
        self.assertEqual(self.question.upvotes_count, 0)
        self.assertEqual(self.question.downvotes_count, 0)

    def test_voting_on_answer_and_comment(self):
        ct_ans = ContentType.objects.get_for_model(Answer)
        ct_com = ContentType.objects.get_for_model(Comment)

        Vote.objects.create(
            user=self.user1,
            content_type=ct_ans,
            object_id=self.answer.pk,
            value=Vote.UPVOTE
        )
        Vote.objects.create(
            user=self.user1,
            content_type=ct_com,
            object_id=self.comment.pk,
            value=Vote.DOWNVOTE
        )

        self.assertEqual(self.answer.score, 1)
        self.assertEqual(self.comment.score, -1)

    def test_one_vote_per_user_per_item_constraint(self):
        ct = ContentType.objects.get_for_model(Question)
        Vote.objects.create(
            user=self.user1,
            content_type=ct,
            object_id=self.question.pk,
            value=Vote.UPVOTE
        )
        # Attempting second vote on same item by same user raises IntegrityError
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                user=self.user1,
                content_type=ct,
                object_id=self.question.pk,
                value=Vote.DOWNVOTE
            )

    def test_invalid_vote_value_validation(self):
        ct = ContentType.objects.get_for_model(Question)
        invalid_vote = Vote(
            user=self.user1,
            content_type=ct,
            object_id=self.question.pk,
            value=5
        )
        with self.assertRaises(ValidationError):
            invalid_vote.full_clean()

    def test_invalid_vote_value_db_constraint(self):
        ct = ContentType.objects.get_for_model(Question)
        with self.assertRaises(IntegrityError):
            Vote.objects.create(
                user=self.user1,
                content_type=ct,
                object_id=self.question.pk,
                value=5
            )
