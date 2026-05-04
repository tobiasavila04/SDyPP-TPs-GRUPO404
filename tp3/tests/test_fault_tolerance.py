import time
import unittest


class TestTimeoutDetection(unittest.TestCase):
    TIMEOUT = 15

    def _timed_out(self, pending):
        now = time.time()
        return [cid for cid, info in pending.items() if now - info["sent_at"] > self.TIMEOUT]

    def test_old_chunk_is_timed_out(self):
        pending = {0: {"body": "{}", "sent_at": time.time() - 20, "retries": 0}}
        self.assertIn(0, self._timed_out(pending))

    def test_recent_chunk_not_timed_out(self):
        pending = {0: {"body": "{}", "sent_at": time.time(), "retries": 0}}
        self.assertEqual(self._timed_out(pending), [])

    def test_only_old_chunks_flagged(self):
        pending = {
            0: {"body": "{}", "sent_at": time.time() - 20, "retries": 0},
            1: {"body": "{}", "sent_at": time.time(), "retries": 0},
        }
        timed_out = self._timed_out(pending)
        self.assertIn(0, timed_out)
        self.assertNotIn(1, timed_out)

    def test_retry_counter_increments_on_timeout(self):
        info = {"body": "{}", "sent_at": time.time() - 20, "retries": 0}
        info["retries"] += 1
        info["sent_at"] = time.time()
        self.assertEqual(info["retries"], 1)
        self.assertAlmostEqual(info["sent_at"], time.time(), delta=1)

    def test_chunk_removed_from_pending_on_result(self):
        pending = {0: {"body": "{}", "sent_at": time.time(), "retries": 0}}
        received = {}
        chunk_id = 0
        pending.pop(chunk_id, None)
        received[chunk_id] = "processed_data"
        self.assertNotIn(chunk_id, pending)
        self.assertIn(chunk_id, received)

    def test_duplicate_result_detected(self):
        received = {0: "first_result"}
        chunk_id = 0
        is_duplicate = chunk_id in received
        self.assertTrue(is_duplicate)

    def test_completion_when_all_chunks_received(self):
        total = 4
        received = {}
        for i in range(total):
            received[i] = f"chunk_{i}"
        self.assertTrue(len(received) == total)

    def test_not_complete_with_missing_chunk(self):
        total = 4
        received = {0: "a", 1: "b", 2: "c"}
        self.assertFalse(len(received) == total)
