import unittest

import chat


class ChatModuleTests(unittest.TestCase):
    def test_normalize_and_mask(self):
        self.assertEqual(chat._normalize_text("Árvore 123"), "arvore 123")
        masked = chat._mask_sensitive_text("gsk_1234567890")
        self.assertNotEqual(masked, "gsk_1234567890")

    def test_to_records(self):
        self.assertEqual(chat._to_records([{"a": 1}]), [{"a": 1}])
        # contrato atual: dict vira registro único
        self.assertEqual(chat._to_records({"registros": [{"a": 1}]}), [{"registros": [{"a": 1}]}])
        self.assertEqual(chat._to_records(None), [])


if __name__ == "__main__":
    unittest.main()
