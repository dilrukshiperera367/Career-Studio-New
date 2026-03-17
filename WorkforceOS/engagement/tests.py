"""
Engagement tests — Survey creation, survey response, unique response constraint,
RecognitionEntry peer kudos, and eNPS score validation.
"""

import datetime
from django.test import TestCase

from tenants.models import Tenant
from core_hr.models import Company, Employee
from engagement.models import Survey, SurveyResponse, RecognitionEntry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tenant(slug='engagement-test'):
    return Tenant.objects.create(name='Engagement Test Org', slug=slug)


def _make_company(tenant):
    return Company.objects.create(tenant=tenant, name='Engage Co.', country='LKA', currency='LKR')


def _make_employee(tenant, company, number='EMP001'):
    return Employee.objects.create(
        tenant=tenant, company=company,
        employee_number=number,
        first_name='Eng', last_name='User',
        work_email=f'{number.lower()}@example.com',
        hire_date='2022-01-01', status='active',
    )


# ---------------------------------------------------------------------------
# Survey model tests
# ---------------------------------------------------------------------------

class TestSurvey(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('survey-test')

    def test_create_survey(self):
        survey = Survey.objects.create(
            tenant=self.tenant,
            title='Q2 Pulse Survey',
            type='pulse',
            questions=[
                {'id': 'q1', 'text': 'How satisfied are you?', 'type': 'rating'},
            ],
        )
        self.assertEqual(survey.type, 'pulse')
        self.assertEqual(survey.status, 'draft')

    def test_survey_default_anonymous(self):
        """Surveys are anonymous by default."""
        survey = Survey.objects.create(tenant=self.tenant, title='Anonymous Survey')
        self.assertTrue(survey.anonymous)

    def test_survey_status_lifecycle(self):
        survey = Survey.objects.create(tenant=self.tenant, title='Status Test Survey')
        survey.status = 'active'
        survey.save()
        survey.refresh_from_db()
        self.assertEqual(survey.status, 'active')


# ---------------------------------------------------------------------------
# SurveyResponse tests
# ---------------------------------------------------------------------------

class TestSurveyResponse(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('response-test')
        self.company = _make_company(self.tenant)
        self.employee = _make_employee(self.tenant, self.company)
        self.survey = Survey.objects.create(
            tenant=self.tenant,
            title='eNPS Q3',
            type='enps',
            questions=[{'id': 'nps', 'text': 'Would you recommend?', 'type': 'nps'}],
        )

    def test_submit_response(self):
        response = SurveyResponse.objects.create(
            tenant=self.tenant, survey=self.survey, employee=self.employee,
            answers={'nps': 8}, nps_score=8,
        )
        self.assertEqual(response.nps_score, 8)
        self.assertEqual(response.answers['nps'], 8)

    def test_unique_response_per_survey_per_employee(self):
        """An employee can only respond to a survey once."""
        SurveyResponse.objects.create(
            tenant=self.tenant, survey=self.survey, employee=self.employee,
            answers={'nps': 9}, nps_score=9,
        )
        with self.assertRaises(Exception):
            SurveyResponse.objects.create(
                tenant=self.tenant, survey=self.survey, employee=self.employee,
                answers={'nps': 7}, nps_score=7,
            )

    def test_nps_score_valid_range(self):
        """NPS score is 0–10."""
        response = SurveyResponse.objects.create(
            tenant=self.tenant, survey=self.survey, employee=self.employee,
            answers={}, nps_score=10,
        )
        self.assertGreaterEqual(response.nps_score, 0)
        self.assertLessEqual(response.nps_score, 10)


# ---------------------------------------------------------------------------
# RecognitionEntry tests
# ---------------------------------------------------------------------------

class TestRecognitionEntry(TestCase):
    def setUp(self):
        self.tenant = _make_tenant('recognition-test')
        self.company = _make_company(self.tenant)
        self.emp_alice = _make_employee(self.tenant, self.company, 'E001')
        self.emp_bob = _make_employee(self.tenant, self.company, 'E002')

    def test_create_recognition(self):
        entry = RecognitionEntry.objects.create(
            tenant=self.tenant,
            from_employee=self.emp_alice,
            to_employee=self.emp_bob,
            category='kudos',
            message='Great work on the product launch!',
            badges=['teamwork', 'leadership'],
        )
        self.assertEqual(entry.category, 'kudos')
        self.assertIn('teamwork', entry.badges)

    def test_recognition_default_likes_zero(self):
        entry = RecognitionEntry.objects.create(
            tenant=self.tenant,
            from_employee=self.emp_alice,
            to_employee=self.emp_bob,
            category='shoutout',
            message='Excellent support!',
        )
        self.assertEqual(entry.likes_count, 0)

    def test_multiple_recognitions(self):
        for i in range(3):
            RecognitionEntry.objects.create(
                tenant=self.tenant,
                from_employee=self.emp_alice,
                to_employee=self.emp_bob,
                category='kudos',
                message=f'Well done #{i}',
            )
        count = RecognitionEntry.objects.filter(to_employee=self.emp_bob).count()
        self.assertEqual(count, 3)
