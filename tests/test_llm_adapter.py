import unittest
from unittest.mock import patch

from demo_agent.llm_agent import parse_text_tool_call
from demo_agent.input_classifier import classify_untrusted_text


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class LlmAdapterTests(unittest.TestCase):
    def test_parses_only_a_known_json_tool_envelope(self):
        result = parse_text_tool_call(
            '```json\n{"name":"read_document","arguments":{"document_id":"report-alice-001"}}\n```'
        )
        self.assertEqual(result["function"]["name"], "read_document")
        self.assertEqual(result["function"]["arguments"]["document_id"], "report-alice-001")

    def test_rejects_unknown_tools_and_extra_fields(self):
        self.assertIsNone(parse_text_tool_call('{"name":"shell","arguments":{}}'))
        self.assertIsNone(parse_text_tool_call('{"name":"read_document","arguments":{},"token":"secret"}'))

    def test_rejects_malformed_oversized_and_done_responses(self):
        self.assertIsNone(parse_text_tool_call('{{"name":"read_document"}}'))
        self.assertIsNone(parse_text_tool_call("x" * 12001))
        self.assertIsNone(parse_text_tool_call('{"name":"done","arguments":{}}'))

    def test_optional_classifier_accepts_only_well_formed_labels(self):
        response = _Response(b'{"message":{"content":"{\\"label\\": \\"benign\\"}"}}')
        with patch("demo_agent.input_classifier.urllib.request.urlopen", return_value=response):
            label, elapsed, error = classify_untrusted_text("http://ollama", "local", "safe", 3)
        self.assertEqual(label, "benign")
        self.assertIsNone(error)
        self.assertGreaterEqual(elapsed, 0)

    def test_optional_classifier_malicious_and_malformed_labels(self):
        for content, expected_label in ((b'{"message":{"content":"{\\"label\\": \\"malicious\\"}"}}', "malicious"),
                                        (b'{"message":{"content":"not-json"}}', None),
                                        (b'{"message":{"content":"{\\"label\\": \\"unknown\\"}"}}', None)):
            with self.subTest(expected_label=expected_label):
                with patch("demo_agent.input_classifier.urllib.request.urlopen", return_value=_Response(content)):
                    label, _elapsed, error = classify_untrusted_text("http://ollama", "local", "text", 3)
                self.assertEqual(label, expected_label)
                self.assertEqual(error is None, expected_label is not None)

    def test_optional_classifier_transport_failure_fails_closed(self):
        with patch("demo_agent.input_classifier.urllib.request.urlopen", side_effect=TimeoutError()):
            label, _elapsed, error = classify_untrusted_text("http://ollama", "local", "text", 3)
        self.assertIsNone(label)
        self.assertEqual(error, "TimeoutError")


if __name__ == "__main__":
    unittest.main()
