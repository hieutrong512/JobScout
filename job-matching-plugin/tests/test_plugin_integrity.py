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

        self.assertEqual(manifest["version"], "1.1.0")
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

    # ----- Dual-manifest (Claude + Codex) integrity -----

    def test_codex_manifest_is_valid(self):
        manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        self.assertTrue(manifest_path.is_file(), "Thiếu manifest Codex")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(manifest["name"], "job-matching")
        self.assertEqual(manifest["version"], "1.1.0")
        self.assertEqual(manifest.get("skills"), "./skills/")
        server = manifest["mcpServers"]["facebook_crawler"]
        self.assertEqual(server["command"], "python")
        self.assertIn("mcp/facebook_crawler_server.py", " ".join(server["args"]))

    def test_codex_mcp_server_declared(self):
        self.assertFalse((PLUGIN_ROOT / "codex.mcp.json").exists())
        self.assertFalse((PLUGIN_ROOT / ".codex-plugin" / "mcp.json").exists())
        launcher = PLUGIN_ROOT / "scripts" / "launch_facebook_crawler_mcp.cmd"
        self.assertTrue(launcher.is_file(), "Thiếu launcher MCP cho Codex")

    def test_claude_and_codex_manifest_names_match(self):
        claude = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        codex = json.loads((PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(claude["name"], codex["name"])
        self.assertEqual(claude["version"], codex["version"])

    def test_claude_agents_and_codex_worker_skills_exist(self):
        self.assertTrue((PLUGIN_ROOT / "agents" / "job-collector.md").is_file())
        self.assertTrue((PLUGIN_ROOT / "agents" / "job-matcher.md").is_file())
        self.assertTrue((PLUGIN_ROOT / "skills" / "job-collector" / "SKILL.md").is_file())
        self.assertTrue((PLUGIN_ROOT / "skills" / "job-matcher" / "SKILL.md").is_file())
        self.assertEqual(list((PLUGIN_ROOT / "agents").glob("*.toml")), [])

    def test_repo_codex_marketplace_is_valid(self):
        path = PLUGIN_ROOT.parent / ".agents" / "plugins" / "marketplace.json"
        marketplace = json.loads(path.read_text(encoding="utf-8"))
        entry = next(item for item in marketplace["plugins"] if item["name"] == "job-matching")
        self.assertEqual(entry["source"]["path"], "./job-matching-plugin")
        self.assertIn("policy", entry)
        self.assertTrue(entry["category"])

    def test_launchers_do_not_require_optional_playwright_at_startup(self):
        launcher = (PLUGIN_ROOT / "scripts" / "launch_facebook_crawler_mcp.cmd").read_text(encoding="utf-8")
        self.assertNotIn("import playwright", launcher)
        self.assertTrue((PLUGIN_ROOT / "scripts" / "launch_facebook_crawler_mcp.sh").is_file())

    def test_command_has_no_developer_file_uri(self):
        command = (PLUGIN_ROOT / "commands" / "find-jobs.md").read_text(encoding="utf-8")
        self.assertNotIn("file:///", command.casefold())
    def test_shared_skills_are_plugin_root_relative(self):
        # Skill dùng chung không được hardcode ${CLAUDE_PLUGIN_ROOT} (Codex không expand được).
        offenders = []
        for path in (PLUGIN_ROOT / "skills").rglob("SKILL.md"):
            if "${CLAUDE_PLUGIN_ROOT}" in path.read_text(encoding="utf-8"):
                offenders.append(str(path.relative_to(PLUGIN_ROOT)))
        self.assertEqual(offenders, [], f"Skill dùng chung còn dùng biến Claude: {offenders}")


if __name__ == "__main__":
    unittest.main()
