import json
import tempfile
import unittest
from pathlib import Path

from evaluation.run import ROOT, load_dataset


class HeldoutDatasetTests(unittest.TestCase):
    def test_heldout_datasets_are_balanced_and_family_separated(self):
        for name in ("heldout-v1.jsonl", "heldout-v2.jsonl", "heldout-v3.jsonl", "heldout-v4.jsonl", "heldout-v5.jsonl"):
            with self.subTest(dataset=name):
                rows = load_dataset(ROOT / "evaluation/datasets" / name, "heldout")
                self.assertEqual(len(rows), 100)
                self.assertEqual(sum(row["label"] == "normal" for row in rows), 50)
                self.assertEqual(sum(row["label"] == "malicious" for row in rows), 50)
                self.assertEqual(len({row["family"] for row in rows}), 20)
                self.assertEqual(len({row["text"].casefold() for row in rows}), 100)

    def test_heldout_rejects_duplicate_case_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "duplicate.jsonl"
            row = {"case_id": "same", "label": "normal", "source": "test", "text": "A harmless example."}
            dataset.write_text("\n".join(json.dumps(row) for _ in range(2)), encoding="utf-8")
            with self.assertRaises(SystemExit):
                load_dataset(dataset, "development")


if __name__ == "__main__":
    unittest.main()
