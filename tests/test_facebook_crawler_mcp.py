import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SERVER_PATH = Path(__file__).resolve().parents[1] / "mcp" / "facebook_crawler_server.py"
SPEC = importlib.util.spec_from_file_location("facebook_crawler_server", SERVER_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class FacebookCrawlerMcpTests(unittest.TestCase):
    def test_initialize_and_list_tools(self):
        initialized = SERVER.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            }
        )
        self.assertEqual(initialized["result"]["serverInfo"]["name"], "job-matching-facebook-crawler")

        listed = SERVER.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        self.assertEqual(listed["result"]["tools"][0]["name"], "run_facebook_crawler")

        fallback = SERVER.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "initialize",
                "params": {"protocolVersion": "2099-01-01"},
            }
        )
        self.assertEqual(fallback["result"]["protocolVersion"], SERVER.PROTOCOL_VERSION)

    def test_command_uses_absolute_workspace_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            profile = root / "data" / "profiles" / "candidate.json"
            profile.parent.mkdir(parents=True)
            profile.write_text(json.dumps({"candidate": {"name": "Test"}}), encoding="utf-8")

            command, output, command_root = SERVER.build_crawler_command(
                {
                    "workspace_root": str(root),
                    "profile_path": "data/profiles/candidate.json",
                    "groups": ["https://www.facebook.com/groups/pythonvietnam"],
                    "queries": ["AI Engineer"],
                    "limit": 10,
                    "scrolls": 3,
                }
            )

            self.assertEqual(command_root, root)
            self.assertTrue(output.is_absolute())
            self.assertIn(str(root), command)
            self.assertIn(str(profile), command)
            self.assertIn("--workspace-root", command)

    def test_rejects_output_outside_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            with self.assertRaisesRegex(ValueError, "inside workspace_root"):
                SERVER.build_crawler_command(
                    {"workspace_root": str(root), "output_path": str(root.parent / "outside.json")}
                )

    def test_rejects_spoofed_facebook_group_url(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            with self.assertRaisesRegex(ValueError, "facebook.com/groups URL"):
                SERVER.build_crawler_command(
                    {
                        "workspace_root": str(root),
                        "groups": ["https://example.com/?next=facebook.com/groups/pythonvietnam"],
                    }
                )

    def test_rejects_boolean_numeric_arguments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            with self.assertRaisesRegex(ValueError, "limit must be an integer"):
                SERVER.build_crawler_command({"workspace_root": str(root), "limit": True})

    def test_rejects_malformed_tool_params(self):
        response = SERVER.handle_message(
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": []}
        )
        self.assertEqual(response["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
