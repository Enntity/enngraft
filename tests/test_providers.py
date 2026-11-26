import io
import json
import unittest
from unittest.mock import patch

from enngraft import Model


class Transports(unittest.TestCase):
    def test_provider_contracts(self):
        text = '{"edits":{"main.c":"ok"}}'
        cases = [
            ("openai", "/v1/chat/completions", "Authorization", "Bearer secret", "messages",
             {"choices": [{"message": {"content": text}}]}),
            ("messages", "/v1/messages", "x-api-key", "secret", "system",
             {"content": [{"type": "text", "text": text}]}),
            ("gemini", "/v1beta/models/m:generateContent", "x-goog-api-key", "secret", "systemInstruction",
             {"candidates": [{"content": {"parts": [{"thought": True, "text": "ignore"}, {"text": text}]}}]})
        ]
        for protocol, path, header, auth, field, envelope in cases:
            with self.subTest(protocol=protocol), patch("urllib.request.build_opener") as opener:
                model = Model(protocol, "https://example.org" + path, "m", "secret", timeout=135)
                transport = opener.return_value
                transport.open.return_value = io.BytesIO(json.dumps(envelope).encode())
                self.assertEqual(model.propose({"facts": "abc"}), json.loads(text))
                self.assertEqual(transport.open.call_args.kwargs["timeout"], 135)
                req = transport.open.call_args.args[0]
                self.assertEqual(dict((k.lower(), v) for k, v in req.header_items())[header.lower()], auth)
                self.assertIn(field, json.loads(req.data))
                self.assertNotIn(b"secret", req.data)

    def test_endpoint_policy(self):
        for url in ("http://public.test/v1", "https://user:pass@test/v1", "https://test/v1?key=secret"):
            with self.assertRaises(ValueError):
                Model("openai", url, "test", "private")
        local = Model("openai", "http://127.0.0.1:8080/v1/chat/completions", "test")
        self.assertNotIn("Authorization", local.request({}).headers)

    def test_malformed_response(self):
        with patch("urllib.request.build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(b'{}')
            with self.assertRaisesRegex(ValueError, "invalid proposal"):
                Model("messages", "https://example.org/v1/messages", "m").propose({})
