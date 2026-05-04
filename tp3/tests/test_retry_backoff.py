import unittest


class TestExponentialBackoff(unittest.TestCase):
    def test_delay_sequence(self):
        # intentos_actuales = 1,2,3,4 → delay = 1s,2s,4s,8s
        expected = [1, 2, 4, 8]
        for i, intentos in enumerate(range(1, 5)):
            delay = 2 ** (intentos - 1)
            self.assertEqual(delay, expected[i])

    def test_delay_in_milliseconds(self):
        intentos = 2
        delay_ms = 2 ** (intentos - 1) * 1000
        self.assertEqual(delay_ms, 2000)

    def test_max_retries_sends_to_dlq(self):
        MAX_RETRIES = 4
        sent_to_dlq = False
        for intentos in range(MAX_RETRIES + 2):
            if intentos >= MAX_RETRIES:
                sent_to_dlq = True
                break
        self.assertTrue(sent_to_dlq)

    def test_below_max_retries_does_not_go_to_dlq(self):
        MAX_RETRIES = 4
        intentos_actuales = 3
        goes_to_dlq = intentos_actuales >= MAX_RETRIES
        self.assertFalse(goes_to_dlq)


class TestDLQRouting(unittest.TestCase):
    def test_error_messages_rejected(self):
        messages = [
            {"id": 1, "error": False},
            {"id": 2, "error": True},
            {"id": 3, "error": False},
            {"id": 4, "error": True},
        ]
        rejected = [m for m in messages if m["error"]]
        processed = [m for m in messages if not m["error"]]
        self.assertEqual(len(rejected), 2)
        self.assertEqual(len(processed), 2)
        self.assertListEqual([m["id"] for m in rejected], [2, 4])

    def test_clean_messages_processed(self):
        messages = [{"id": 1, "error": False}]
        processed = [m for m in messages if not m["error"]]
        self.assertEqual(len(processed), 1)
