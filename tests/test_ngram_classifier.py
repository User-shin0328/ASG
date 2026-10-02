import math
import unittest
from unittest.mock import patch

from demo_agent.input_classifier import classify_untrusted_text_with_ngram
from demo_agent.ngram_classifier import load_model, score_text


class NgramClassifierTests(unittest.TestCase):
    def test_packaged_model_integrity_provenance_and_score(self):
        model, recorded_hash = load_model()
        self.assertEqual(recorded_hash, model["model_sha256"])
        self.assertEqual(model["source_revision"], "e658d94")
        self.assertEqual(model["threshold_selection"]["split"], "validation")
        self.assertTrue(math.isfinite(score_text("ordinary assigned report", model)))

    def test_combined_verdict_flags_when_ngram_detects_and_semantic_is_benign(self):
        with patch("demo_agent.input_classifier.classify_untrusted_text", return_value=("benign", 1.0, None)), \
             patch("demo_agent.ngram_classifier.classify_untrusted_text_ngram", return_value=("malicious", 200.0, "hash")):
            label, elapsed, error, detected, semantic, semantic_elapsed = classify_untrusted_text_with_ngram(
                "http://unused", "unused", "untrusted text", 10, ngram_enabled=True)
        self.assertEqual(label, "malicious")
        self.assertEqual(semantic, "benign")
        self.assertTrue(detected)
        self.assertIsNone(error)
        self.assertGreaterEqual(elapsed, semantic_elapsed)

    def test_combined_verdict_preserves_semantic_detection(self):
        with patch("demo_agent.input_classifier.classify_untrusted_text", return_value=("malicious", 1.0, None)), \
             patch("demo_agent.ngram_classifier.classify_untrusted_text_ngram", return_value=("benign", 0.0, "hash")):
            label, _elapsed, error, detected, semantic, _semantic_elapsed = classify_untrusted_text_with_ngram(
                "http://unused", "unused", "untrusted text", 10, ngram_enabled=True)
        self.assertEqual(label, "malicious")
        self.assertEqual(semantic, "malicious")
        self.assertFalse(detected)
        self.assertIsNone(error)

    def test_model_failure_is_reported_for_fail_closed_adapter(self):
        with patch("demo_agent.input_classifier.classify_untrusted_text", return_value=("benign", 1.0, None)), \
             patch("demo_agent.ngram_classifier.classify_untrusted_text_ngram", side_effect=ValueError("bad model")):
            label, _elapsed, error, _detected, _semantic, _semantic_elapsed = classify_untrusted_text_with_ngram(
                "http://unused", "unused", "untrusted text", 10, ngram_enabled=True)
        self.assertIsNone(label)
        self.assertEqual(error, "ngram_ValueError")

    def test_ngram_mode_cannot_be_enabled_without_semantic_classifier(self):
        with patch.dict("os.environ", {"AGENT_ALICE_TOKEN": "a" * 40,
                                      "INPUT_CLASSIFIER_ENABLED": "false",
                                      "INPUT_CLASSIFIER_NGRAM_ENABLED": "true"}), \
             patch("sys.argv", ["llm_agent"]):
            from demo_agent.llm_agent import main

            with self.assertRaisesRegex(SystemExit, "requires INPUT_CLASSIFIER_ENABLED=true"):
                main()

    def test_enabling_optional_classifier_defaults_to_hybrid(self):
        from demo_agent.llm_agent import main

        with patch.dict("os.environ", {"AGENT_ALICE_TOKEN": "a" * 40,
                                      "INPUT_CLASSIFIER_ENABLED": "true"}, clear=True), \
             patch("sys.argv", ["llm_agent"]), \
             patch("demo_agent.llm_agent.gateway_call", return_value={"verdict": "CLEAR"}), \
             patch("demo_agent.llm_agent.classify_untrusted_text_with_ngram",
                   return_value=("benign", 0.01, None, False, "benign", 0.01)) as classifier, \
             patch("demo_agent.llm_agent.model_chat", return_value={"message": {"content": "done", "tool_calls": []}}):
            main()
        self.assertTrue(classifier.call_args.kwargs["ngram_enabled"])


if __name__ == "__main__":
    unittest.main()
