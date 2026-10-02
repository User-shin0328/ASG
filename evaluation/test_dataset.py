import json
import tempfile
import unittest
from pathlib import Path

from evaluation.run import ROOT, load_dataset


class HeldoutDatasetTests(unittest.TestCase):
    def test_development_dataset_has_planned_30_per_label(self):
        rows = load_dataset(ROOT / "evaluation/datasets/dev.jsonl", "development")
        self.assertEqual(len(rows), 60)
        self.assertEqual(sum(row["label"] == "normal" for row in rows), 30)
        self.assertEqual(sum(row["label"] == "malicious" for row in rows), 30)
        family_labels = {}
        family_sizes = {}
        for row in rows:
            family_labels.setdefault(row["family"], set()).add(row["label"])
            family_sizes[row["family"]] = family_sizes.get(row["family"], 0) + 1
        self.assertEqual(len(family_sizes), 20)
        self.assertEqual(set(family_sizes.values()), {3})
        self.assertTrue(all(len(labels) == 1 for labels in family_labels.values()))
        heldout_v7 = load_dataset(ROOT / "evaluation/datasets/heldout-v7.jsonl", "heldout")
        self.assertFalse(set(family_sizes) & {row["family"] for row in heldout_v7})

    def test_heldout_datasets_are_balanced_and_family_separated(self):
        for name in ("heldout-v1.jsonl", "heldout-v2.jsonl", "heldout-v3.jsonl", "heldout-v4.jsonl", "heldout-v5.jsonl", "heldout-v6.jsonl", "heldout-v7.jsonl"):
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
