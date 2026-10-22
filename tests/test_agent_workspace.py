import json
import tempfile
import unittest
from pathlib import Path

from scripts.agent_workspace import route_messages, validate_goal_file, validate_repo


class WorkspaceTests(unittest.TestCase):
    def test_dependency_cycle_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "goals.json"
            path.write_text(json.dumps({
                "schema_version": "1.0",
                "agent_id": "alpha",
                "goals": [
                    {"id": "G-1", "title": "One", "horizon": "ongoing", "status": "active",
                     "priority": "high", "depends_on": ["G-2"], "supports": []},
                    {"id": "G-2", "title": "Two", "horizon": "short_term", "status": "proposed",
                     "priority": "normal", "depends_on": ["G-1"], "supports": []}
                ]
            }), encoding="utf-8")
            errors = validate_goal_file(path, "alpha")
            self.assertTrue(any("dependency cycle" in item for item in errors))

    def test_shared_goal_registry_is_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "agents").mkdir()
            project = root / "projects" / "central"
            project.mkdir(parents=True)
            (project / "shared-goals.json").write_text(json.dumps({
                "schema_version": "1.0",
                "registry": "shared",
                "scope": "central",
                "goals": [
                    {"id": "CG-1", "title": "One", "horizon": "ongoing", "status": "active",
                     "priority": "high", "depends_on": ["CG-9"], "supports": []}
                ]
            }), encoding="utf-8")
            errors = validate_repo(root)
            self.assertTrue(any("missing goal 'CG-9'" in item for item in errors))
            self.assertFalse(any("agent_id" in item for item in errors))

    def test_router_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inbox = root / "agents" / "alpha" / "inbox"
            ledger = root / "shared" / "communications"
            inbox.mkdir(parents=True)
            ledger.mkdir(parents=True)
            (inbox / "messages.jsonl").write_text("", encoding="utf-8")
            (ledger / "log.jsonl").write_text(json.dumps({
                "timestamp": "2026-01-01T00:00:00Z", "sender": "unverified",
                "target": "alpha", "type": "proposal", "content": "Review"
            }) + "\n", encoding="utf-8")
            self.assertEqual(route_messages(root), (1, 1))
            self.assertEqual(route_messages(root), (0, 0))
            message = json.loads((inbox / "messages.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(message["authentication"], "unverified-ledger-claim")


if __name__ == "__main__":
    unittest.main()
