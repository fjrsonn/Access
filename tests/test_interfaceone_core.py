import unittest

import interfaceone_core as core


class InterfaceOneCoreTests(unittest.TestCase):
    def test_decidir_destino_encomenda_override(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "dados", "score": 0.5}

        out = core.decidir_destino(
            "PACOTE SHOPEE BLOCO A AP 1",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: True,
        )
        self.assertEqual(out.get("destino_final"), "encomendas")

    def test_decidir_destino_preserva_orientacoes_sem_sinal_encomenda(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "orientacoes", "score": 4.0, "confianca": 0.92, "ambiguo": False}

        out = core.decidir_destino(
            "Registrando ocorrencia de barulho no bloco 10 apartamento 10, morador foi orientado",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: False,
        )
        self.assertEqual(out.get("destino_final"), "orientacoes")

    def test_decidir_destino_forca_encomendas_quando_heuristica_detecta(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "orientacoes", "score": 3.2, "confianca": 0.9, "ambiguo": False, "scores": {"encomendas": 2.4}}

        out = core.decidir_destino(
            "ENVELOP RIACHUELO BLO13 APARTAMEN109 JOAO",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: True,
        )
        self.assertEqual(out.get("destino_final"), "encomendas")

    def test_decidir_destino_preserva_observacoes_confiavel_sem_sinal_forte_encomenda(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "observacoes", "score": 4.0, "confianca": 0.85, "ambiguo": False, "scores": {"encomendas": 0.8}}

        out = core.decidir_destino(
            "Avisar o morador do bloco A apartamento 101 quando chegar a entrega da farmacia.",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: True,
        )
        self.assertEqual(out.get("destino_final"), "observacoes")

    def test_decidir_destino_prioriza_pessoas_com_sinal_forte(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "encomendas", "score": 3.0, "confianca": 0.9, "ambiguo": False, "scores": {"encomendas": 3.0}}

        parsed = {"PLACA": "ABC1234", "MODELOS": ["ONIX"], "STATUS": "VISITANTE", "BLOCO": "A", "APARTAMENTO": "101"}
        out = core.decidir_destino(
            "VISITANTE JOAO ABC1234 ONIX BLOCO A AP 101",
            parsed,
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: True,
        )
        self.assertEqual(out.get("destino_final"), "dados")

    def test_decidir_destino_ambiguo_vai_para_revisao(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "dados", "score": 0.5, "confianca": 0.2, "ambiguo": True, "scores": {"encomendas": 0.4}}

        out = core.decidir_destino(
            "texto confuso",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: False,
        )
        self.assertEqual(out.get("destino_final"), "revisao")

    def test_decidir_destino_rotulo_explicito_encomenda(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "observacoes", "score": 2.0, "confianca": 0.8, "ambiguo": False, "scores": {"encomendas": 0.4}}

        out = core.decidir_destino(
            "LOJA: SHOPEE | TIPO: ENVELOPE | IDENTIFICACAO: BR123456789",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: False,
        )
        self.assertEqual(out.get("destino_final"), "encomendas")

    def test_decidir_destino_rotulo_explicito_orientacao(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "dados", "score": 1.0, "confianca": 0.4, "ambiguo": False, "scores": {"encomendas": 0.0}}

        out = core.decidir_destino(
            "ORIENTACAO: morador orientado sobre conduta",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: False,
        )
        self.assertEqual(out.get("destino_final"), "orientacoes")

    def test_decidir_destino_rotulo_explicito_observacao(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "dados", "score": 1.0, "confianca": 0.4, "ambiguo": False, "scores": {"encomendas": 0.0}}

        out = core.decidir_destino(
            "OBSERVACAO: avisar morador quando chegar entrega",
            {},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: False,
        )
        self.assertEqual(out.get("destino_final"), "observacoes")

    def test_montar_registro_acesso(self):
        parsed = {
            "NOME_RAW": "joao silva",
            "BLOCO": "A",
            "APARTAMENTO": "1",
            "PLACA": "abc1234",
            "MODELOS": ["onix"],
            "COR": "preto",
            "STATUS": "morador",
        }
        rec = core.montar_registro_acesso(parsed, corrigir_nome_fn=lambda x: x, now_str="10/01/2026 10:00:00")
        self.assertEqual(rec["NOME"], "JOAO")
        self.assertEqual(rec["SOBRENOME"], "SILVA")
        self.assertEqual(rec["MODELO"], "ONIX")

    def test_montar_entrada_bruta(self):
        out = core.montar_entrada_bruta(1, "texto", "10/01/2026 10:00:00", {"HAS_PLACA": True})
        self.assertEqual(out["id"], 1)
        self.assertTrue(out["HAS_PLACA"])


if __name__ == "__main__":
    unittest.main()
