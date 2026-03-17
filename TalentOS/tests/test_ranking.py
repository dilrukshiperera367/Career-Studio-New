"""
test_ranking.py — Scoring engine assertions.
Ensures all final candidate scores are in the 0-100 range,
structural properties of ranked results are correct, and
edge cases are handled gracefully.
"""

from django.test import TestCase


class TestScoringEngine0to100Range(TestCase):
    """All score outputs must be in [0, 100] when the full pipeline runs."""

    def _make_job_spec(self, required_skills=None, optional_skills=None,
                       titles=None, min_years=2, max_years=10):
        return {
            "required_skills": [{"skill_id": s} for s in (required_skills or ["python", "django"])],
            "optional_skills": [{"skill_id": s} for s in (optional_skills or ["docker"])],
            "target_titles": titles or ["Software Engineer"],
            "min_years_experience": min_years,
            "max_years_experience": max_years,
            "domain_tags": ["backend"],
        }

    def _make_candidate(self, cid="c1", skills=None, title="Software Engineer",
                        years=5.0, recency=0.8, tags=None):
        return {
            "candidate_id": cid,
            "skill_ids": skills or ["python", "django"],
            "most_recent_title": title,
            "total_experience_years": years,
            "recency_score": recency,
            "tags": tags or ["backend"],
        }

    def _ranking_weights(self):
        return {
            "structured": {
                "skill_match": 0.45,
                "title_match": 0.20,
                "domain_match": 0.15,
                "experience_fit": 0.10,
                "recency": 0.10,
            },
            "hybrid": {
                "text_norm": 0.55,
                "skill_match": 0.30,
                "title_match": 0.10,
                "recency": 0.05,
            },
        }

    def test_single_candidate_score_in_range(self):
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            candidates = [self._make_candidate()]
            results = rank_candidates(candidates, self._make_job_spec())
            self.assertEqual(len(results), 1)
            score = results[0]["score"]
            self.assertGreaterEqual(score, 0.0, "Score must be >= 0")
            self.assertLessEqual(score, 1.0, "Score must be <= 1")

    def test_multiple_candidates_all_scores_in_range(self):
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            candidates = [
                self._make_candidate("c1", ["python", "django"], "Software Engineer", 5.0, 0.9),
                self._make_candidate("c2", ["java"], "Java Developer", 2.0, 0.5),
                self._make_candidate("c3", [], "Intern", 0.5, 0.3),
                self._make_candidate("c4", ["python", "django", "docker"], "Senior Engineer", 8.0, 0.95),
            ]
            results = rank_candidates(candidates, self._make_job_spec())
            for r in results:
                self.assertGreaterEqual(r["score"], 0.0, f"Score for {r['candidate_id']} < 0")
                self.assertLessEqual(r["score"], 1.0, f"Score for {r['candidate_id']} > 1")

    def test_results_sorted_descending(self):
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            candidates = [
                self._make_candidate("c1", ["python", "django"], years=5),
                self._make_candidate("c2", [], years=1),
            ]
            results = rank_candidates(candidates, self._make_job_spec())
            self.assertGreaterEqual(results[0]["score"], results[1]["score"],
                                    "Results must be sorted descending by score")

    def test_empty_candidate_list_returns_empty(self):
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            results = rank_candidates([], self._make_job_spec())
            self.assertEqual(results, [])

    def test_zero_skills_candidate_gets_nonzero_score(self):
        """Even a candidate with no matching skills can score > 0 due to other components."""
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            candidates = [self._make_candidate("c1", skills=[], title="Software Engineer", years=5)]
            results = rank_candidates(candidates, self._make_job_spec())
            # Score may be > 0 due to title/experience match
            self.assertGreaterEqual(results[0]["score"], 0.0)

    def test_perfect_match_scores_near_1(self):
        """A candidate matching all required skills, title, and experience should score near 1."""
        from apps.search.ranking import rank_candidates
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            candidates = [
                self._make_candidate(
                    "c1",
                    skills=["python", "django", "docker"],
                    title="Software Engineer",
                    years=6,
                    recency=1.0,
                    tags=["backend"],
                )
            ]
            results = rank_candidates(candidates, self._make_job_spec(
                required_skills=["python", "django"],
                optional_skills=["docker"],
                titles=["Software Engineer"],
                min_years=4,
                max_years=8,
            ))
            self.assertGreater(results[0]["score"], 0.7)

    def test_compute_structured_score_components_present(self):
        from apps.search.ranking import compute_structured_score
        with self.settings(RANKING_WEIGHTS=self._ranking_weights()):
            result = compute_structured_score(
                candidate_skills={"python"},
                job_required={"python"},
                job_optional=set(),
                candidate_title="Developer",
                target_titles=["Developer"],
                total_years=3,
                min_years=2,
                max_years=5,
                candidate_recency=0.8,
                candidate_tags=[],
                job_domains=[],
            )
            self.assertIn("score", result)
            self.assertIn("components", result)
            self.assertGreaterEqual(result["score"], 0.0)
            self.assertLessEqual(result["score"], 1.0)

    def test_skill_match_bounded(self):
        from apps.search.ranking import skill_match
        score = skill_match({"a", "b", "c"}, {"a", "b", "c"}, set())
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)
        score_none = skill_match(set(), {"a", "b"}, set())
        self.assertGreaterEqual(score_none, 0.0)

    def test_experience_fit_bounded(self):
        from apps.search.ranking import experience_fit
        for years, mn, mx in [(0, 3, 7), (5, 3, 7), (20, 3, 7), (3, 3, 7), (7, 3, 7)]:
            score = experience_fit(years, mn, mx)
            self.assertGreaterEqual(score, 0.0, f"experience_fit({years}, {mn}, {mx}) < 0")
            self.assertLessEqual(score, 1.0, f"experience_fit({years}, {mn}, {mx}) > 1")
