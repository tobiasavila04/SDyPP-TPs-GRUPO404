import base64
import unittest

import cv2
import numpy as np


class TestSobelProcessing(unittest.TestCase):
    def _apply_sobel(self, img):
        sx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=3)
        sy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=3)
        return np.uint8(np.absolute(cv2.magnitude(sx, sy)))

    def test_output_shape_preserved(self):
        img = np.zeros((100, 80), dtype=np.uint8)
        result = self._apply_sobel(img)
        self.assertEqual(result.shape, img.shape)

    def test_blank_image_produces_no_edges(self):
        img = np.zeros((50, 50), dtype=np.uint8)
        result = self._apply_sobel(img)
        self.assertEqual(result.sum(), 0)

    def test_vertical_edge_detected(self):
        img = np.zeros((50, 50), dtype=np.uint8)
        img[:, 25:] = 200
        result = self._apply_sobel(img)
        self.assertGreater(int(result[:, 24].max()), 0)

    def test_horizontal_edge_detected(self):
        img = np.zeros((50, 50), dtype=np.uint8)
        img[25:, :] = 200
        result = self._apply_sobel(img)
        self.assertGreater(int(result[24, :].max()), 0)

    def test_base64_encode_decode_roundtrip(self):
        img = np.random.randint(0, 256, (80, 80), dtype=np.uint8)
        _, buffer = cv2.imencode(".jpg", img)
        b64 = base64.b64encode(buffer).decode("utf-8")
        decoded = cv2.imdecode(np.frombuffer(base64.b64decode(b64), np.uint8), cv2.IMREAD_GRAYSCALE)
        self.assertEqual(decoded.shape, (80, 80))

    def test_chunk_assembly_preserves_dimensions(self):
        img = np.random.randint(0, 256, (100, 80), dtype=np.uint8)
        n = 4
        alto_chunk = 100 // n
        chunks = [img[i * alto_chunk : (i + 1) * alto_chunk, :] for i in range(n)]
        assembled = np.vstack(chunks)
        self.assertEqual(assembled.shape, img.shape)
        np.testing.assert_array_equal(assembled, img)

    def test_chunk_count_matches_total(self):
        img = np.zeros((120, 60), dtype=np.uint8)
        n = 4
        alto_chunk = 120 // n
        chunks = []
        for i in range(n):
            y_ini = i * alto_chunk
            y_fin = 120 if i == n - 1 else (i + 1) * alto_chunk
            chunks.append(img[y_ini:y_fin, :])
        self.assertEqual(len(chunks), n)
        total_rows = sum(c.shape[0] for c in chunks)
        self.assertEqual(total_rows, 120)
