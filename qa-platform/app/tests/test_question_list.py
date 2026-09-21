from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.views.generic import ListView

from app.models import Answer, Question, Tag, Vote
from app.views import QuestionListView

User = get_user_model()


class QuestionListViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='password123')
        self.url = reverse('app:question_list')

    def test_view_is_class_based(self):
        self.assertTrue(issubclass(QuestionListView, ListView))

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

    def test_question_list_filter_by_existing_tag(self):
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
        self.assertEqual(response.context['selected_tag'], t1)
        self.assertContains(response, 'Python Question')
        self.assertNotContains(response, 'Django Question')

    def test_question_list_filter_excludes_other_tags(self):
        t1 = Tag.objects.create(name='python')
        t2 = Tag.objects.create(name='javascript')
        q1 = Question.objects.create(title='Python Q', description='D1', author=self.user)
        q1.tags.add(t1)
        q2 = Question.objects.create(title='JS Q', description='D2', author=self.user)
        q2.tags.add(t2)

        response = self.client.get(f'{self.url}?tag={t2.slug}')
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(questions, [q2])
        self.assertNotContains(response, 'Python Q')
        self.assertContains(response, 'JS Q')

    def test_question_list_filter_question_with_multiple_tags(self):
        t1 = Tag.objects.create(name='python')
        t2 = Tag.objects.create(name='django')
        q = Question.objects.create(title='Multi-Tag Question', description='D', author=self.user)
        q.tags.add(t1, t2)

        res1 = self.client.get(f'{self.url}?tag={t1.slug}')
        self.assertEqual(res1.status_code, 200)
        self.assertIn(q, res1.context['questions'])

        res2 = self.client.get(f'{self.url}?tag={t2.slug}')
        self.assertEqual(res2.status_code, 200)
        self.assertIn(q, res2.context['questions'])

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

    def test_question_list_filter_multiple_tags_or_union(self):
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

        # In OR mode, questions with python OR django are returned (3 questions), but not JS
        response = self.client.get(f'{self.url}?tag={t_py.slug}&tag={t_dj.slug}')
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(len(questions), 3)
        self.assertIn(q_both, questions)
        self.assertIn(q_py, questions)
        self.assertIn(q_dj, questions)
        self.assertNotIn(q_js, questions)
        self.assertEqual(len(response.context['selected_tags']), 2)
        self.assertIn(t_py, response.context['selected_tags'])
        self.assertIn(t_dj, response.context['selected_tags'])
        self.assertContains(response, 'Python and Django Q')
        self.assertContains(response, 'Only Python Q')
        self.assertContains(response, 'Only Django Q')
        self.assertNotContains(response, 'Only JS Q')

    def test_question_list_filter_comma_separated_tags(self):
        t_py = Tag.objects.create(name='python')
        t_dj = Tag.objects.create(name='django')
        t_js = Tag.objects.create(name='javascript')

        q_both = Question.objects.create(title='Comma Tag Q', description='Both tags', author=self.user)
        q_both.tags.add(t_py, t_dj)

        q_py = Question.objects.create(title='Py Only Q', description='Python only', author=self.user)
        q_py.tags.add(t_py)

        q_js = Question.objects.create(title='JS Only Q', description='JS only', author=self.user)
        q_js.tags.add(t_js)

        response = self.client.get(f'{self.url}?tag={t_py.slug},{t_dj.slug}')
        self.assertEqual(response.status_code, 200)
        questions = list(response.context['questions'])
        self.assertEqual(len(questions), 2)
        self.assertIn(q_both, questions)
        self.assertIn(q_py, questions)
        self.assertNotIn(q_js, questions)

    def test_question_list_filter_multiple_tags_one_nonexistent(self):
        t_py = Tag.objects.create(name='python')
        q = Question.objects.create(title='Python Q', description='desc', author=self.user)
        q.tags.add(t_py)

        # In OR mode, valid tag still returns matching questions
        response = self.client.get(f'{self.url}?tag={t_py.slug}&tag=nonexistent-tag')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['questions']), 1)
        self.assertTrue(response.context['has_invalid_tag'])
        self.assertContains(response, 'Python Q')

    def test_question_list_filter_all_nonexistent_tags(self):
        Question.objects.create(title='Sample Q', description='desc', author=self.user)

        response = self.client.get(f'{self.url}?tag=nonexistent-1&tag=nonexistent-2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['questions']), 0)
        self.assertContains(response, 'No questions found')

    def test_question_list_filter_multiple_tags_pagination(self):
        t1 = Tag.objects.create(name='python')
        t2 = Tag.objects.create(name='django')

        for i in range(15):
            q = Question.objects.create(title=f'Py-Dj Q {i}', description='desc', author=self.user)
            q.tags.add(t1, t2)

        res1 = self.client.get(f'{self.url}?tag={t1.slug}&tag={t2.slug}')
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.context['is_paginated'])
        self.assertEqual(len(res1.context['questions']), 10)
        self.assertEqual(res1.context['paginator'].count, 15)
        self.assertContains(res1, f'tag={t1.slug}')
        self.assertContains(res1, f'tag={t2.slug}')

        res2 = self.client.get(f'{self.url}?page=2&tag={t1.slug}&tag={t2.slug}')
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(len(res2.context['questions']), 5)

    def test_question_list_filter_tag_toggle_urls(self):
        t_py = Tag.objects.create(name='python')
        t_dj = Tag.objects.create(name='django')

        response = self.client.get(f'{self.url}?tag={t_py.slug}')
        self.assertEqual(response.status_code, 200)

        all_tags_data = {item['tag'].slug: item for item in response.context['all_tags_data']}
        self.assertTrue(all_tags_data['python']['is_selected'])
        self.assertFalse(all_tags_data['django']['is_selected'])

        # Python is selected: toggle_url removes python
        self.assertNotIn('tag=python', all_tags_data['python']['toggle_url'])
        # Django is not selected: toggle_url adds django to python
        self.assertIn('tag=python', all_tags_data['django']['toggle_url'])
        self.assertIn('tag=django', all_tags_data['django']['toggle_url'])
