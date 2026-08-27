import importlib.util
import tempfile
import unittest
from pathlib import Path


CRAWLER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "fb_crawler.py"
SPEC = importlib.util.spec_from_file_location("facebook_crawler", CRAWLER_PATH)
CRAWLER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(CRAWLER)


class FacebookCrawlerLogicTests(unittest.TestCase):
    def tearDown(self):
        CRAWLER.configure_workspace_root(str(CRAWLER.PLUGIN_ROOT))

    def test_search_queries_follow_profile_roles(self):
        profile = {
            "target": {
                "desired_roles": ["Senior Backend Engineer", "Python Developer"]
            }
        }

        self.assertEqual(
            CRAWLER.get_search_queries(profile),
            ["Senior Backend Engineer", "Backend", "Python Developer", "Python"],
        )

    def test_custom_queries_are_trimmed_and_deduplicated(self):
        self.assertEqual(
            CRAWLER.get_search_queries(custom_queries=" Python,python, Backend  Engineer "),
            ["Python", "Backend Engineer"],
        )

    def test_relevance_uses_profile_instead_of_ai_hard_code(self):
        backend_profile = {
            "target": {"desired_roles": ["Backend Engineer"]},
            "skills": [{"name": "Python"}, {"name": "FastAPI"}],
        }

        self.assertTrue(
            CRAWLER.is_job_relevant(
                "[HCM] Hiring Backend Engineer — Python/FastAPI, gửi CV qua email.",
                backend_profile,
            )
        )
        self.assertFalse(
            CRAWLER.is_job_relevant(
                "Tuyển Senior Graphic Designer, ứng tuyển ngay.",
                backend_profile,
            )
        )

    def test_relevance_still_requires_hiring_signal(self):
        profile = {"target": {"desired_roles": ["Backend Engineer"]}}
        self.assertFalse(
            CRAWLER.is_job_relevant("Khóa học Backend Engineer với Python", profile)
        )

    def test_workspace_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            CRAWLER.configure_workspace_root(str(root))
            with self.assertRaisesRegex(ValueError, "nằm trong workspace"):
                CRAWLER.resolve_workspace_path(str(root.parent / "outside.json"))

    def test_explicit_profile_must_be_json_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            CRAWLER.configure_workspace_root(str(root))
            profile = root / "profile.json"
            profile.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON object"):
                CRAWLER.load_candidate_profile(str(profile))


if __name__ == "__main__":
    unittest.main()
