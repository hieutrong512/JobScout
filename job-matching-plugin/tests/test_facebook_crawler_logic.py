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
        # Reset global workspace state về thư mục plugin cho ổn định giữa các test.
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

    def test_extract_contacts_parses_zalo_and_email(self):
        contacts = CRAWLER.extract_contacts(
            "Ứng tuyển gửi CV về hr@company.vn hoặc Zalo 0987.654.321"
        )
        self.assertEqual(contacts.get("email"), "hr@company.vn")
        self.assertEqual(contacts.get("zalo"), "0987654321")

    def test_parse_group_urls_normalizes_and_dedupes(self):
        groups = CRAWLER.parse_group_urls(
            "https://www.facebook.com/groups/pythonvietnam, "
            "https://www.facebook.com/groups/pythonvietnam/?ref=1"
        )
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["url"], "https://www.facebook.com/groups/pythonvietnam")

    def test_group_config_accepts_legacy_list_format(self):
        groups = CRAWLER.normalize_group_config(
            [{"name": "Python Vietnam", "url": "https://www.facebook.com/groups/pythonvietnam"}]
        )
        self.assertEqual(len(groups), 1)

    def test_empty_group_config_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "Chưa có Facebook Group nào"):
            CRAWLER.normalize_group_config({})

    def test_default_workspace_is_cwd(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            import os

            prev = os.getcwd()
            try:
                os.chdir(root)
                CRAWLER.configure_workspace_root(None)
                self.assertEqual(CRAWLER.WORKSPACE_ROOT, root)
            finally:
                os.chdir(prev)

    def test_display_detection_by_platform(self):
        import os

        prev_platform = CRAWLER.sys.platform
        prev_display = os.environ.get("DISPLAY")
        prev_wayland = os.environ.get("WAYLAND_DISPLAY")
        try:
            CRAWLER.sys.platform = "win32"
            self.assertTrue(CRAWLER.interactive_display_available())

            CRAWLER.sys.platform = "darwin"
            self.assertTrue(CRAWLER.interactive_display_available())

            CRAWLER.sys.platform = "linux"
            os.environ.pop("DISPLAY", None)
            os.environ.pop("WAYLAND_DISPLAY", None)
            self.assertFalse(CRAWLER.interactive_display_available())

            os.environ["DISPLAY"] = ":0"
            self.assertTrue(CRAWLER.interactive_display_available())
        finally:
            CRAWLER.sys.platform = prev_platform
            for key, val in (("DISPLAY", prev_display), ("WAYLAND_DISPLAY", prev_wayland)):
                if val is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = val

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
