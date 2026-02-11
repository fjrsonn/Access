import unittest

import chat


class ChatPipelineTests(unittest.TestCase):
    def test_query_tokens_handles_stopwords(self):
        tokens = chat._query_tokens("qual foi a primeira encomenda do joao no bloco 4")
        self.assertIn("primeira", tokens)
        self.assertIn("encomenda", tokens)
        self.assertNotIn("qual", tokens)

    def test_partial_notice_when_recent_trimmed(self):
        notice = chat._build_partial_context_notice(
            {
                "contexto_recente": {
                    "dadosend.json__meta": {"registros_totais": 120, "registros_recentes_enviados": 30}
                }
            }
        )
        self.assertIn("recente", notice.lower())

    def test_shrink_masks_sensitive_field(self):
        data = {"telefone": "11999998888"}
        shrunk = chat._shrink_value(data)
        self.assertNotEqual(shrunk["telefone"], "11999998888")
        self.assertIn("***", shrunk["telefone"])

    def test_temporal_parse(self):
        dt = chat._parse_timestamp("09/02/2026 23:54")
        self.assertIsNotNone(dt)

    def test_low_confidence_fallback_to_audit(self):
        full_sources = {"dadosend.json": [], "encomendasend.json": [], "avisos.json": []}
        context, mode = chat._build_query_context_with_fallback("abc", full_sources, force_audit=False)
        self.assertIn("auditoria", mode)
        self.assertEqual(context.get("modo"), "auditoria_completa")


if __name__ == "__main__":
    unittest.main()
