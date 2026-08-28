import json
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def _frontmatter(text: str) -> str:
    """Trả về khối frontmatter YAML giữa cặp '---' đầu tiên."""
    assert text.startswith("---\n"), "Thiếu frontmatter mở đầu"
    return text.split("---", 2)[1]


class PluginIntegrityTests(unittest.TestCase):
    def test_manifest_is_valid(self):
        manifest_path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "job-matching")
        self.assertTrue(manifest["version"])
        self.assertTrue(manifest["description"])
        self.assertTrue(manifest["author"]["name"])

    def test_convention_directories_exist(self):
        for component in ("skills", "agents", "commands", "schemas", "scripts", "mcp"):
            path = PLUGIN_ROOT / component
            self.assertTrue(path.is_dir(), f"Thiếu thư mục thành phần: {component}")

    def test_all_json_files_are_valid(self):
        json_paths = [
            PLUGIN_ROOT / ".claude-plugin" / "plugin.json",
            PLUGIN_ROOT / ".mcp.json",
        ]
        json_paths.extend((PLUGIN_ROOT / "schemas").glob("*.json"))

        for path in json_paths:
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_mcp_server_declared(self):
        manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest.get("mcpServers"), "./.mcp.json")
        mcp = json.loads((PLUGIN_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        server = mcp["mcpServers"]["facebook_crawler"]
        self.assertEqual(server.get("type"), "stdio")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", " ".join(server["args"]))
        self.assertEqual(
            server.get("env", {}).get("JOB_MATCHING_WORKSPACE_ROOT"),
            "${CLAUDE_PROJECT_DIR}",
        )
        self.assertTrue((PLUGIN_ROOT / "mcp" / "facebook_crawler_server.py").is_file())

    def test_marketplace_and_plugin_versions_match(self):
        manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads(
            (PLUGIN_ROOT.parent / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entry = next(plugin for plugin in marketplace["plugins"] if plugin["name"] == manifest["name"])

        self.assertEqual(manifest["version"], "1.0.1")
        self.assertEqual(entry["version"], manifest["version"])
        self.assertEqual(marketplace["metadata"]["version"], manifest["version"])

    def test_job_collector_grants_plugin_namespaced_facebook_tool(self):
        collector = (PLUGIN_ROOT / "agents" / "job-collector.md").read_text(encoding="utf-8")
        self.assertIn(
            "tools: mcp__plugin_job-matching_facebook_crawler__run_facebook_crawler,",
            collector,
        )

    def test_schemas_are_present(self):
        for name in ("profile.schema.json", "job.schema.json", "match.schema.json"):
            self.assertTrue((PLUGIN_ROOT / "schemas" / name).is_file(), f"Thiếu schema: {name}")

    def test_every_skill_has_required_frontmatter(self):
        skill_paths = sorted((PLUGIN_ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(skill_paths, "Không tìm thấy skill nào")

        for path in skill_paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path.parent.name):
                frontmatter = _frontmatter(text)
                self.assertIn("\nname:", frontmatter)
                self.assertIn("\ndescription:", frontmatter)

    def test_every_agent_has_required_frontmatter(self):
        agent_paths = sorted((PLUGIN_ROOT / "agents").glob("*.md"))
        self.assertTrue(agent_paths, "Không tìm thấy agent nào")

        for path in agent_paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(agent=path.stem):
                frontmatter = _frontmatter(text)
                self.assertIn("\nname:", frontmatter)
                self.assertIn("\ndescription:", frontmatter)

    def test_find_jobs_command_exists(self):
        command_path = PLUGIN_ROOT / "commands" / "find-jobs.md"
        self.assertTrue(command_path.is_file(), "Thiếu slash command find-jobs")
        frontmatter = _frontmatter(command_path.read_text(encoding="utf-8"))
        self.assertIn("\ndescription:", frontmatter)

    def test_plugin_root_placeholders_use_claude_convention(self):
        # Skill/agent/command tham chiếu tài nguyên đóng gói phải dùng ${CLAUDE_PLUGIN_ROOT},
        # không dùng biến của Codex.
        offenders = []
        for path in PLUGIN_ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if "CODEX_PLUGIN_ROOT" in text or "web_search" in text:
                offenders.append(str(path.relative_to(PLUGIN_ROOT)))
        self.assertEqual(offenders, [], f"Còn sót dấu vết Codex: {offenders}")


if __name__ == "__main__":
    unittest.main()
