"""Run: python tests/test_webhook.py   (needs the package deps, i.e. httpx)."""
import hashlib
import hmac
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from directsaz.webhook import handle_challenge, verify_signature  # noqa: E402


def sign(token: str, ts: int, body: str) -> str:
    mac = hmac.new(token.encode(), f"{ts}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


class ChallengeTest(unittest.TestCase):
    def test_correct_token(self):
        self.assertEqual(handle_challenge("secret-token", "secret-token")[0], 200)

    def test_missing_or_wrong_token(self):
        for p in (None, "", "secret", "secret-token-x", "توکن"):
            self.assertEqual(handle_challenge(p, "secret-token")[0], 401, p)

    def test_empty_configured_token_fails_closed(self):
        for exp in ("", None):
            self.assertEqual(handle_challenge("", exp)[0], 401)
            self.assertEqual(handle_challenge("anything", exp)[0], 401)


class SignatureTest(unittest.TestCase):
    body = '{"events":[]}'

    def test_valid_and_tampered(self):
        ts = int(time.time())
        h = sign("secret-token", ts, self.body)
        self.assertTrue(verify_signature("secret-token", self.body, str(ts), h))
        self.assertTrue(verify_signature("secret-token", self.body.encode(), str(ts), h))
        self.assertFalse(verify_signature("secret-token", self.body + " ", str(ts), h))
        self.assertFalse(verify_signature("other-token", self.body, str(ts), h))

    def test_empty_token_refuses_matching_hmac(self):
        ts = int(time.time())
        forged = sign("", ts, self.body)
        self.assertFalse(verify_signature("", self.body, str(ts), forged))
        self.assertFalse(verify_signature(None, self.body, str(ts), forged))

    def test_non_ascii_signature_is_false_not_error(self):
        ts = int(time.time())
        self.assertFalse(verify_signature("t", self.body, str(ts), f"t={ts},v1=ä"))

    def test_stale_timestamp(self):
        ts = int(time.time()) - 301
        self.assertFalse(verify_signature("t", self.body, str(ts), sign("t", ts, self.body)))


if __name__ == "__main__":
    unittest.main()
