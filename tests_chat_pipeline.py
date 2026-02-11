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

    def test_consolidated_context_tracks_ambiguous_names(self):
        full_sources = {
            "dadosend.json": [
                {"NOME": "Joao", "SOBRENOME": "Silva", "BLOCO": "2", "APARTAMENTO": "10", "DATA_HORA": "09/02/2026 10:00"},
                {"NOME": "Joao", "SOBRENOME": "Silva", "BLOCO": "5", "APARTAMENTO": "3", "DATA_HORA": "09/02/2026 11:00"},
            ],
            "encomendasend.json": [],
            "avisos.json": [],
        }
        consolidated = chat._build_consolidated_context(full_sources)
        self.assertIn("joao silva", consolidated.get("nomes_ambiguos", {}))

    def test_person_identity_changes_by_location(self):
        r1 = {"NOME": "Joao", "SOBRENOME": "Silva", "BLOCO": "2", "APARTAMENTO": "10"}
        r2 = {"NOME": "Joao", "SOBRENOME": "Silva", "BLOCO": "5", "APARTAMENTO": "3"}
        self.assertNotEqual(chat._person_identity(r1), chat._person_identity(r2))


if __name__ == "__main__":
    unittest.main()
