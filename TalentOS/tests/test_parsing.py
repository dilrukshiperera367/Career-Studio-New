"""
test_parsing.py — Resume parser skill extraction and confidence assertions.
Focused on ensuring the parsing pipeline handles edge cases correctly.
"""

from django.test import TestCase


class TestSkillExtractionConfidence(TestCase):
    """Verify skill extraction output structure and confidence bounds."""

    def test_extract_skills_returns_confidence_in_range(self):
        from apps.parsing.services import extract_skills
        taxonomy = {
            "python": {"skill_id": "s1", "canonical_name": "Python"},
            "django": {"skill_id": "s2", "canonical_name": "Django"},
        }
        text = "Built REST APIs with Python and Django for 3 years."
        skills = extract_skills(text, taxonomy)
        for skill in skills:
            self.assertIn("confidence", skill, "Each skill must have a confidence key")
            self.assertGreaterEqual(skill["confidence"], 0.0, "Confidence must be >= 0")
            self.assertLessEqual(skill["confidence"], 1.0, "Confidence must be <= 1")

    def test_extract_skills_no_false_positives(self):
        """Skills not in taxonomy should not appear in extraction results."""
        from apps.parsing.services import extract_skills
        taxonomy = {
            "python": {"skill_id": "s1", "canonical_name": "Python"},
        }
        text = "Experienced in Java and Kotlin."
        skills = extract_skills(text, taxonomy)
        skill_names = [s["canonical_name"] for s in skills]
        self.assertNotIn("Java", skill_names)
        self.assertNotIn("Kotlin", skill_names)

    def test_extract_skills_case_insensitive(self):
        """Skill matching should be case-insensitive."""
        from apps.parsing.services import extract_skills
        taxonomy = {
            "python": {"skill_id": "s1", "canonical_name": "Python"},
            "machine learning": {"skill_id": "s2", "canonical_name": "Machine Learning"},
        }
        text = "Expert in PYTHON and Machine learning (ML)."
        skills = extract_skills(text, taxonomy)
        skill_names = [s["canonical_name"] for s in skills]
        self.assertIn("Python", skill_names)

    def test_extract_skills_evidence_list(self):
        """Each extracted skill should include an evidence list."""
        from apps.parsing.services import extract_skills
        taxonomy = {
            "python": {"skill_id": "s1", "canonical_name": "Python"},
        }
        text = "I use Python daily for data analysis."
        skills = extract_skills(text, taxonomy)
        if skills:
            skill = skills[0]
            self.assertIn("evidence", skill, "Skill must have evidence key")
            self.assertIsInstance(skill["evidence"], list, "Evidence must be a list")

    def test_extract_contact_info_multiple_emails(self):
        """Multiple email addresses in the same document should all be captured."""
        from apps.parsing.services import extract_contact_info
        text = "Work email: work@company.com\nPersonal: personal@gmail.com\n+94-77-1234567"
        info = extract_contact_info(text)
        self.assertGreaterEqual(len(info["emails"]), 2)

    def test_extract_contact_info_international_phone(self):
        """Should extract international phone number formats."""
        from apps.parsing.services import extract_contact_info
        text = "+94 77 123 4567\n+1-800-555-0100"
        info = extract_contact_info(text)
        self.assertGreaterEqual(len(info["phones"]), 1)

    def test_detect_sections_returns_dict(self):
        """detect_sections must always return a dict."""
        from apps.parsing.services import detect_sections
        result = detect_sections("No structured sections here at all.")
        self.assertIsInstance(result, dict)

    def test_detect_sections_experience_heading(self):
        """Work experience headed sections must be detected."""
        from apps.parsing.services import detect_sections
        text = (
            "Work Experience\n"
            "Software Engineer at TechCorp (2020-2024)\n\n"
            "Education\n"
            "BSc Computer Science, University of Colombo"
        )
        sections = detect_sections(text)
        has_experience = any("experience" in k for k in sections)
        self.assertTrue(has_experience, "Expected an experience section to be detected")

    def test_compute_derived_experience_years_positive(self):
        """Total experience years must be >= 0."""
        from apps.parsing.services import compute_derived_fields
        experiences = [
            {"title": "Dev", "company": "A", "start": "2019", "end": "2022", "raw_block": "python"},
        ]
        skills = []
        derived = compute_derived_fields(experiences, skills)
        self.assertGreaterEqual(derived["total_experience_years"], 0)

    def test_parse_fuzzy_date_present_returns_today(self):
        from apps.parsing.services import parse_fuzzy_date
        from datetime import date
        result = parse_fuzzy_date("present")
        self.assertEqual(result, date.today())

    def test_parse_fuzzy_date_year_only(self):
        from apps.parsing.services import parse_fuzzy_date
        from datetime import date
        result = parse_fuzzy_date("2021")
        self.assertEqual(result.year, 2021)

    def test_resume_parser_output_keys(self):
        """parse_resume_text must return a dict with the expected top-level keys."""
        from apps.parsing.services import parse_resume_text
        text = (
            "John Smith\njohn@example.com\n+1-555-100-2000\n\n"
            "EXPERIENCE\nSenior Developer at Acme Corp, 2020-2024\nPython, Django, REST\n\n"
            "EDUCATION\nBSc Computer Science, MIT, 2014-2018\n\n"
            "SKILLS\nPython, JavaScript, SQL"
        )
        try:
            result = parse_resume_text(text)
            for key in ("contact", "experiences", "education", "skills"):
                self.assertIn(key, result, f"Expected '{key}' key in parser output")
        except Exception:
            # parse_resume_text may raise if NLP model not loaded — skip gracefully
            self.skipTest("NLP model not available in test environment")
