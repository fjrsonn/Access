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

    def test_decidir_destino_com_campos_acesso_forca_dados(self):
        def fake_classifier(_txt, _parsed):
            return {"destino": "encomendas", "score": 0.9}

        out = core.decidir_destino(
            "ENTREGA AP 101",
            {"PLACA": "ABC1234", "BLOCO": "A"},
            classificar_fn=fake_classifier,
            is_encomenda_fn=lambda *_: True,
        )
        self.assertEqual(out.get("destino_final"), "dados")

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
