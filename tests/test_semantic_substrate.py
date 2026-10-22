import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class SemanticSubstrateTests(unittest.TestCase):
    def test_modern_messages_reference_registered_threads(self):
        messages = jsonl(ROOT / "shared/communications/messages.jsonl")
        threads = jsonl(ROOT / "shared/communications/threads.jsonl")
        thread_ids = {x["thread_id"] for x in threads}
        message_ids = {x["message_id"] for x in messages}
        self.assertEqual(len(message_ids), len(messages))
        self.assertTrue(messages)
        self.assertTrue(all(m["thread_id"] in thread_ids for m in messages))

    def test_thread_message_membership_is_consistent(self):
        messages = jsonl(ROOT / "shared/communications/messages.jsonl")
        threads = jsonl(ROOT / "shared/communications/threads.jsonl")
        by_id = {m["message_id"]: m for m in messages}
        for thread in threads:
            for message_id in thread["message_ids"]:
                self.assertIn(message_id, by_id)
                self.assertEqual(by_id[message_id]["thread_id"], thread["thread_id"])

    def test_work_dependencies_resolve(self):
        work = jsonl(ROOT / "shared/work/items.jsonl")
        ids = {x["id"] for x in work}
        for item in work:
            for dependency in item["depends_on"]:
                self.assertIn(dependency, ids)

    def test_legacy_forum_path_is_not_canonical(self):
        pointer = jsonl(ROOT / "shared/communications/forum.jsonl")
        self.assertEqual(pointer[0]["status"], "superseded")
        self.assertEqual(pointer[0]["canonical_messages"], "shared/communications/messages.jsonl")


if __name__ == "__main__":
    unittest.main()
