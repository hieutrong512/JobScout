import json
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class PluginIntegrityTests(unittest.TestCase):
    def test_manifest_references_existing_components(self):
        manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "job-matching")
        self.assertTrue(manifest["version"])
        self.assertTrue(manifest["description"])
        self.assertTrue(manifest["author"]["name"])

        for field in ("skills", "mcpServers"):
            component = (PLUGIN_ROOT / manifest[field]).resolve()
            self.assertTrue(component.exists(), f"Missing manifest component: {field}")
            self.assertTrue(component.is_relative_to(PLUGIN_ROOT.resolve()))

    def test_all_json_files_are_valid(self):
        json_paths = [PLUGIN_ROOT / ".mcp.json", PLUGIN_ROOT / ".codex-plugin" / "plugin.json"]
        json_paths.extend((PLUGIN_ROOT / "schemas").glob("*.json"))

        for path in json_paths:
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_every_skill_has_required_frontmatter(self):
        skill_paths = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(skill_paths)

        for path in skill_paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                self.assertTrue(text.startswith("---\n"))
                frontmatter = text.split("---", 2)[1]
                self.assertIn("\nname:", frontmatter)
                self.assertIn("\ndescription:", frontmatter)


if __name__ == "__main__":
    unittest.main()
