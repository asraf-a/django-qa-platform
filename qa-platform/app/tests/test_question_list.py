from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.views.generic import ListView
from django_filters.views import FilterView

from app.models import Answer, Question, Tag, Vote
from app.views import QuestionListView

User = get_user_model()


class QuestionListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='password123')
        self.url = reverse('app:question_list')

    def test_view_is_class_based(self):
        self.assertTrue(issubclass(QuestionListView, (ListView, FilterView)))

    def test_question_list_status_code_by_name(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_question_list_status_code_at_root(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_question_list_uses_correct_templates(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, 'questions/question_list.html')
        self.assertTemplateUsed(response, 'base.html')

    def test_question_list_empty_state(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(response.context['questions'], [])
        self.assertContains(response, 'No questions asked yet')

    def test_question_list_displays_question_data(self):
        tag1 = Tag.objects.create(name='python')
        tag2 = Tag.objects.create(name='django')

        question = Question.objects.create(
            title='How to optimize Django queries?',
            description='I want to learn about select_related and prefetch_related.',
            author=self.user
        )
        question.tags.add(tag1, tag2)

        Answer.objects.create(
            question=question,
            author=self.user,
            content='Use prefetch_related for M2M and reverse relations.'
        )

        ct = ContentType.objects.get_for_model(Question)
        Vote.objects.create(
            user=self.user,
            content_type=ct,
            object_id=question.pk,
            value=Vote.UPVOTE
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'How to optimize Django queries?')
        self.assertContains(response, 'select_related')
        self.assertContains(response, 'alice')
        self.assertContains(response, '#python')
        self.assertContains(response, '#django')
        self.assertContains(response, '1')  # Vote count / score
        self.assertContains(response, '1')  # Answer count

    def test_question_list_ordering_newest_first(self):
        q1 = Question.objects.create(
            title='First Question',
            description='First description',
            author=self.user
        )
        q2 = Question.objects.create(
            title='Second Question',
            description='Second description',
            author=self.user
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q2, q1])

    def test_question_list_pagination_first_page(self):
        for i in range(15):
            Question.objects.create(
                title=f'Question {i}',
                description=f'Description {i}',
                author=self.user
            )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['questions']), 10)
        self.assertEqual(response.context['paginator'].count, 15)
        self.assertEqual(response.context['page_obj'].number, 1)
        self.assertContains(response, 'Page 1 of 2')
        self.assertContains(response, 'Next')

    def test_question_list_pagination_second_page(self):
        for i in range(15):
            Question.objects.create(
                title=f'Question {i}',
                description=f'Description {i}',
                author=self.user
            )

        response = self.client.get(f'{self.url}?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['questions']), 5)
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertContains(response, 'Page 2 of 2')
        self.assertContains(response, 'Previous')

    def test_question_list_without_tag_shows_all_questions(self):
        t1 = Tag.objects.create(name='python')
        t2 = Tag.objects.create(name='django')
        q1 = Question.objects.create(title='Q1', description='D1', author=self.user)
        q1.tags.add(t1)
        q2 = Question.objects.create(title='Q2', description='D2', author=self.user)
        q2.tags.add(t2)
        q3 = Question.objects.create(title='Q3', description='D3', author=self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['questions']), 3)
        self.assertEqual(len(response.context['selected_tags']), 0)

    def test_question_list_filter_by_single_tag(self):
        t1 = Tag.objects.create(name='python')
        t2 = Tag.objects.create(name='django')
        q1 = Question.objects.create(title='Python Question', description='D1', author=self.user)
        q1.tags.add(t1)
        q2 = Question.objects.create(title='Django Question', description='D2', author=self.user)
        q2.tags.add(t2)

        response = self.client.get(f'{self.url}?tag={t1.slug}')
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q1])
        self.assertIn(t1, response.context['selected_tags'])
        self.assertContains(response, 'Python Question')
        self.assertNotContains(response, 'Django Question')

    def test_question_list_filter_by_multiple_tags_or(self):
        t_py = Tag.objects.create(name='python')
        t_dj = Tag.objects.create(name='django')
        t_js = Tag.objects.create(name='javascript')

        q_both = Question.objects.create(title='Python and Django Q', description='Both tags', author=self.user)
        q_both.tags.add(t_py, t_dj)

        q_py = Question.objects.create(title='Only Python Q', description='One tag', author=self.user)
        q_py.tags.add(t_py)

        q_dj = Question.objects.create(title='Only Django Q', description='One tag', author=self.user)
        q_dj.tags.add(t_dj)

        q_js = Question.objects.create(title='Only JS Q', description='Different tag', author=self.user)
        q_js.tags.add(t_js)

        response = self.client.get(f'{self.url}?tag={t_py.slug}&tag={t_dj.slug}')
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(len(questions), 3)
        self.assertIn(q_both, questions)
        self.assertIn(q_py, questions)
        self.assertIn(q_dj, questions)
        self.assertNotIn(q_js, questions)
        self.assertContains(response, 'Python and Django Q')
        self.assertContains(response, 'Only Python Q')
        self.assertContains(response, 'Only Django Q')
        self.assertNotContains(response, 'Only JS Q')

    def test_question_list_filter_nonexistent_tag(self):
        Question.objects.create(title='Sample Q', description='D', author=self.user)

        response = self.client.get(f'{self.url}?tag=nonexistent-tag-123')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['questions']), 0)
        self.assertContains(response, 'No questions found')
        self.assertContains(response, 'nonexistent-tag-123')

    def test_question_list_filter_pagination(self):
        tag = Tag.objects.create(name='python')
        other_tag = Tag.objects.create(name='other')

        for i in range(15):
            q = Question.objects.create(title=f'Python Q {i}', description='D', author=self.user)
            q.tags.add(tag)

        other_q = Question.objects.create(title='Other Q', description='D', author=self.user)
        other_q.tags.add(other_tag)

        # Page 1 of filtered results
        res1 = self.client.get(f'{self.url}?tag={tag.slug}')
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.context['is_paginated'])
        self.assertEqual(len(res1.context['questions']), 10)
        self.assertEqual(res1.context['paginator'].count, 15)
        self.assertContains(res1, f'tag={tag.slug}')

        # Page 2 of filtered results
        res2 = self.client.get(f'{self.url}?tag={tag.slug}&page=2')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.context['questions']), 5)
        self.assertNotContains(res2, 'Other Q')

    def test_question_list_toggle_and_active_filters(self):
        t1 = Tag.objects.create(name='python')
        t2 = Tag.objects.create(name='django')

        # When viewing tag 'python'
        response = self.client.get(f'{self.url}?tag={t1.slug}')
        self.assertEqual(response.status_code, 200)

        # Selected tags has t1 with toggle_url back to question list
        selected_tags = response.context['selected_tags']
        self.assertEqual(len(selected_tags), 1)
        self.assertEqual(selected_tags[0].slug, t1.slug)
        self.assertEqual(selected_tags[0].toggle_url, self.url)

        # In all_tags, t1 is selected and its toggle_url removes it
        all_tags = {t.slug: t for t in response.context['all_tags']}
        self.assertTrue(all_tags[t1.slug].is_selected)
        self.assertEqual(all_tags[t1.slug].toggle_url, self.url)

        # t2 is not selected and its toggle_url adds django to python
        self.assertFalse(all_tags[t2.slug].is_selected)
        self.assertIn(f'tag={t1.slug}', all_tags[t2.slug].toggle_url)
        self.assertIn(f'tag={t2.slug}', all_tags[t2.slug].toggle_url)

    def test_question_list_sort_newest(self):
        q1 = Question.objects.create(title='Old Question', description='D', author=self.user)
        q2 = Question.objects.create(title='New Question', description='D', author=self.user)

        # Default (no sort param)
        res_default = self.client.get(self.url)
        self.assertEqual(list(res_default.context['questions']), [q2, q1])
        self.assertEqual(res_default.context['current_sort'], 'newest')

        # Explicit ?sort=newest
        res_newest = self.client.get(f'{self.url}?sort=newest')
        self.assertEqual(list(res_newest.context['questions']), [q2, q1])

        # Invalid sort falls back to newest
        res_invalid = self.client.get(f'{self.url}?sort=invalid')
        self.assertEqual(list(res_invalid.context['questions']), [q2, q1])
        self.assertEqual(res_invalid.context['current_sort'], 'newest')

    def test_question_list_sort_most_voted(self):
        ct = ContentType.objects.get_for_model(Question)
        other_user = User.objects.create_user(username='voter2', password='password123')

        q_zero = Question.objects.create(title='Zero Votes Q', description='D', author=self.user)
        q_high = Question.objects.create(title='High Votes Q', description='D', author=self.user)
        q_negative = Question.objects.create(title='Negative Votes Q', description='D', author=self.user)

        # Upvotes for q_high (+2)
        Vote.objects.create(user=self.user, content_type=ct, object_id=q_high.pk, value=Vote.UPVOTE)
        Vote.objects.create(user=other_user, content_type=ct, object_id=q_high.pk, value=Vote.UPVOTE)

        # Downvote for q_negative (-1)
        Vote.objects.create(user=self.user, content_type=ct, object_id=q_negative.pk, value=Vote.DOWNVOTE)

        response = self.client.get(f'{self.url}?sort=most_voted')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_sort'], 'most_voted')
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q_high, q_zero, q_negative])

    def test_question_list_sort_unanswered(self):
        q_answered = Question.objects.create(title='Answered Q', description='D', author=self.user)
        Answer.objects.create(question=q_answered, author=self.user, content='Some answer')

        q_unanswered = Question.objects.create(title='Unanswered Q', description='D', author=self.user)

        response = self.client.get(f'{self.url}?sort=unanswered')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['current_sort'], 'unanswered')
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q_unanswered])
        self.assertContains(response, 'Unanswered Q')
        self.assertNotContains(response, 'Answered Q')

        # Empty state when all questions have answers
        q_unanswered.delete()
        res_empty = self.client.get(f'{self.url}?sort=unanswered')
        self.assertEqual(len(res_empty.context['questions']), 0)
        self.assertContains(res_empty, 'No unanswered questions')

    def test_question_list_sort_combined_with_tags(self):
        t1 = Tag.objects.create(name='django')
        t2 = Tag.objects.create(name='python')
        ct = ContentType.objects.get_for_model(Question)

        q1 = Question.objects.create(title='Django Low Q', description='D', author=self.user)
        q1.tags.add(t1)

        q2 = Question.objects.create(title='Django High Q', description='D', author=self.user)
        q2.tags.add(t1, t2)
        Vote.objects.create(user=self.user, content_type=ct, object_id=q2.pk, value=Vote.UPVOTE)

        q3 = Question.objects.create(title='Python Only Q', description='D', author=self.user)
        q3.tags.add(t2)

        response = self.client.get(f'{self.url}?tag={t1.slug}&sort=most_voted')
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q2, q1])

        # Verify sort_tabs preserve tag param
        sort_tabs = {tab['key']: tab for tab in response.context['sort_tabs']}
        self.assertTrue(sort_tabs['most_voted']['is_active'])
        self.assertIn(f'tag={t1.slug}', sort_tabs['newest']['url'])

    def test_question_list_sort_pagination_preserves_sort(self):
        for i in range(15):
            Question.objects.create(title=f'Q {i}', description='D', author=self.user)

        response = self.client.get(f'{self.url}?sort=most_voted')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_paginated'])
        self.assertContains(response, 'sort=most_voted')
