"""Unit tests for parsing, ranking, and dedup services."""

from datetime import date
from django.test import TestCase


class TestParsingServices(TestCase):
    """Test the parsing pipeline functions."""

    def test_clean_text_normalizes_bullets(self):
        from apps.parsing.services import clean_text
        raw = "• Python\n• Django\n• REST APIs"
        cleaned = clean_text(raw)
        self.assertIn("* Python", cleaned)
        self.assertIn("* Django", cleaned)

    def test_clean_text_dehyphenation(self):
        from apps.parsing.services import clean_text
        raw = "soft-\nware engineering"
        cleaned = clean_text(raw)
        self.assertIn("software", cleaned)

    def test_clean_text_collapse_whitespace(self):
        from apps.parsing.services import clean_text
        raw = "hello   world\n\n\n\nextra   lines"
        cleaned = clean_text(raw)
        self.assertNotIn("   ", cleaned)
        self.assertNotIn("\n\n\n", cleaned)

    def test_detect_sections_headings(self):
        from apps.parsing.services import detect_sections
        text = "John Doe\njohn@test.com\n\nEXPERIENCE\nSenior Dev at Acme 2020-2024\n\nEDUCATION\nBSc Computer Science"
        sections = detect_sections(text)
        self.assertIn("experience", sections)
        self.assertIn("education", sections)

    def test_detect_sections_fallback(self):
        from apps.parsing.services import detect_sections
        text = "John Doe\nBSc from MIT\nWorked at Google 2020 - 2023"
        sections = detect_sections(text)
        self.assertTrue(len(sections) > 0)

    def test_extract_contact_info(self):
        from apps.parsing.services import extract_contact_info
        text = "john@example.com\n+1 555-123-4567\nlinkedin.com/in/johndoe"
        info = extract_contact_info(text)
        self.assertIn("john@example.com", info["emails"])
        self.assertTrue(len(info["phones"]) > 0)
        self.assertIn("linkedin", info["urls"])

    def test_extract_date_ranges(self):
        from apps.parsing.services import extract_date_ranges
        text = "Jan 2020 - Dec 2023\n2019 - Present"
        ranges = extract_date_ranges(text)
        self.assertEqual(len(ranges), 2)
        self.assertEqual(ranges[0]["start"], "Jan 2020")
        self.assertEqual(ranges[0]["end"], "Dec 2023")

    def test_extract_skills_from_taxonomy(self):
        from apps.parsing.services import extract_skills
        taxonomy = {
            "python": {"skill_id": "s1", "canonical_name": "Python"},
            "machine learning": {"skill_id": "s2", "canonical_name": "Machine Learning"},
            "django": {"skill_id": "s3", "canonical_name": "Django"},
        }
        text = "Experienced in Python and Django. Knowledge of machine learning."
        skills = extract_skills(text, taxonomy)
        skill_names = [s["canonical_name"] for s in skills]
        self.assertIn("Python", skill_names)
        self.assertIn("Django", skill_names)
        self.assertIn("Machine Learning", skill_names)

    def test_parse_fuzzy_date(self):
        from apps.parsing.services import parse_fuzzy_date
        self.assertEqual(parse_fuzzy_date("Present"), date.today())
        yr = parse_fuzzy_date("2020")
        self.assertEqual(yr, date(2020, 1, 1))
        self.assertIsNone(parse_fuzzy_date(""))

    def test_compute_derived_fields(self):
        from apps.parsing.services import compute_derived_fields
        experiences = [
            {"title": "Senior Dev", "company": "Acme", "start": "2020", "end": "Present", "raw_block": "python"},
            {"title": "Developer", "company": "Beta", "start": "2017", "end": "2020", "raw_block": "java"},
        ]
        skills = [
            {"skill_id": "s1", "evidence": ["python"]},
            {"skill_id": "s2", "evidence": ["java"]},
        ]
        derived = compute_derived_fields(experiences, skills)
        self.assertGreater(derived["total_experience_years"], 5)
        self.assertEqual(derived["most_recent_title"], "Senior Dev")
        self.assertGreater(derived["recency_score"], 0)

    def test_non_overlapping_intervals(self):
        from apps.parsing.services import _sum_non_overlapping_intervals
        intervals = [
            (date(2020, 1, 1), date(2022, 1, 1)),
            (date(2021, 1, 1), date(2023, 1, 1)),  # overlapping
        ]
        years = _sum_non_overlapping_intervals(intervals)
        self.assertAlmostEqual(years, 3.0, delta=0.1)


class TestRankingEngine(TestCase):
    """Test the ranking score components."""

    def test_skill_match_full_overlap(self):
        from apps.search.ranking import skill_match
        self.assertAlmostEqual(
            skill_match({"a", "b", "c"}, {"a", "b"}, {"c"}),
            1.0,
        )

    def test_skill_match_no_overlap(self):
        from apps.search.ranking import skill_match
        self.assertAlmostEqual(
            skill_match({"x", "y"}, {"a", "b"}, {}),
            0.0,
        )

    def test_skill_match_partial(self):
        from apps.search.ranking import skill_match
        score = skill_match({"a"}, {"a", "b"}, {})
        self.assertGreater(score, 0)
        self.assertLess(score, 1)

    def test_title_match_exact(self):
        from apps.search.ranking import title_match
        self.assertEqual(title_match("Software Engineer", ["Software Engineer"]), 1.0)

    def test_title_match_partial(self):
        from apps.search.ranking import title_match
        self.assertEqual(title_match("Senior Software Engineer", ["Software Engineer"]), 0.5)

    def test_title_match_none(self):
        from apps.search.ranking import title_match
        self.assertEqual(title_match("Product Manager", ["Software Engineer"]), 0.0)

    def test_experience_fit_in_range(self):
        from apps.search.ranking import experience_fit
        self.assertEqual(experience_fit(5.0, 3.0, 7.0), 1.0)

    def test_experience_fit_below(self):
        from apps.search.ranking import experience_fit
        score = experience_fit(1.0, 3.0, 7.0)
        self.assertGreater(score, 0)
        self.assertLess(score, 1)

    def test_experience_fit_above(self):
        from apps.search.ranking import experience_fit
        score = experience_fit(12.0, 3.0, 7.0)
        self.assertGreaterEqual(score, 0.5)

    def test_normalize_bm25(self):
        from apps.search.ranking import normalize_bm25
        self.assertAlmostEqual(normalize_bm25(5.0, 0.0, 10.0), 0.5, places=2)
        self.assertAlmostEqual(normalize_bm25(10.0, 0.0, 10.0), 1.0, places=2)

    def test_composite_structured_score(self):
        from apps.search.ranking import compute_structured_score
        with self.settings(RANKING_WEIGHTS={"structured": {
            "skill_match": 0.45,
            "title_match": 0.20,
            "domain_match": 0.15,
            "experience_fit": 0.10,
            "recency": 0.10,
        }}):
            result = compute_structured_score(
                candidate_skills={"a", "b"},
                job_required={"a", "b"},
                job_optional=set(),
                candidate_title="Engineer",
                target_titles=["Engineer"],
                total_years=5,
                min_years=3,
                max_years=7,
                candidate_recency=0.9,
                candidate_tags=["tech"],
                job_domains=["tech"],
            )
            self.assertGreater(result["score"], 0.8)
            self.assertIn("components", result)

    def test_build_explanation(self):
        from apps.search.ranking import build_explanation
        structured = {
            "score": 0.85,
            "components": {"skill_match": 0.9, "title_match": 1.0, "experience_fit": 1.0, "recency": 0.8, "domain_match": 0.5},
            "weights": {},
        }
        explanation = build_explanation(structured, candidate_skills={"a"}, job_required={"a"})
        self.assertIn("reasons", explanation)
        self.assertGreater(len(explanation["reasons"]), 0)

    def test_rank_candidates(self):
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS={
            "structured": {
                "skill_match": 0.45, "title_match": 0.20,
                "domain_match": 0.15, "experience_fit": 0.10, "recency": 0.10,
            },
            "hybrid": {
                "text_norm": 0.55, "skill_match": 0.30,
                "title_match": 0.10, "recency": 0.05,
            },
        }):
            candidates = [
                {"candidate_id": "c1", "most_recent_title": "Engineer", "total_experience_years": 5, "recency_score": 0.9, "tags": [], "skill_ids": ["a", "b"]},
                {"candidate_id": "c2", "most_recent_title": "Manager", "total_experience_years": 2, "recency_score": 0.5, "tags": [], "skill_ids": ["a"]},
            ]
            job = {"required_skills": [{"skill_id": "a"}, {"skill_id": "b"}], "optional_skills": [], "target_titles": ["Engineer"], "min_years_experience": 3, "max_years_experience": 7, "domain_tags": []}
            result = rank_candidates(candidates, job)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["candidate_id"], "c1")
            self.assertGreater(result[0]["score"], result[1]["score"])


class TestDedupServices(TestCase):
    """Test dedup result structure."""

    def test_create_new_candidate_result(self):
        from apps.candidates.services import _create_new_candidate_result
        result = _create_new_candidate_result()
        self.assertEqual(result["action"], "created")
        self.assertIsNone(result["candidate_id"])
        self.assertEqual(result["confidence"], 0.0)


class TestWorkflowConditions(TestCase):
    """Test workflow condition matching."""

    def test_conditions_match_empty(self):
        from apps.workflows.services import _conditions_match
        self.assertTrue(_conditions_match({}, {"any": "value"}))

    def test_conditions_match_exact(self):
        from apps.workflows.services import _conditions_match
        self.assertTrue(_conditions_match(
            {"stage": "screening"},
            {"stage": "screening", "other": "value"},
        ))

    def test_conditions_match_list(self):
        from apps.workflows.services import _conditions_match
        self.assertTrue(_conditions_match(
            {"stage": ["screening", "interview"]},
            {"stage": "interview"},
        ))

    def test_conditions_no_match(self):
        from apps.workflows.services import _conditions_match
        self.assertFalse(_conditions_match(
            {"stage": "screening"},
            {"stage": "interview"},
        ))


class TestEmailTemplateRendering(TestCase):
    """Test email template variable interpolation."""

    def test_render_template_basic(self):
        from apps.messaging.services import _render_template
        result = _render_template("Hello {{name}}, welcome to {{company}}!", {"name": "John", "company": "Acme"})
        self.assertEqual(result, "Hello John, welcome to Acme!")

    def test_render_template_missing_var(self):
        from apps.messaging.services import _render_template
        result = _render_template("Hello {{name}}, your {{unknown}} is ready", {"name": "Alice"})
        self.assertEqual(result, "Hello Alice, your {{unknown}} is ready")
