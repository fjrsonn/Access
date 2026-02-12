import unittest
from text_classifier import classificar_destino_texto


class TestClassificacaoTexto(unittest.TestCase):
    def test_observacao_com_encomenda(self):
        t = "Avisar encomendas quando chegar bloco 10 apartamento 10 no nome do Flavio"
        out = classificar_destino_texto(t, None)
        self.assertEqual(out["destino"], "observacoes")

    def test_orientacao_com_avisar(self):
        t = "Relato de ocorrencia: orientar morador e avisar sindico sobre o ocorrido"
        out = classificar_destino_texto(t, None)
        self.assertEqual(out["destino"], "orientacoes")

    def test_ambiguo(self):
        t = "registro de aviso"
        out = classificar_destino_texto(t, None)
        self.assertIn(out["destino"], {"orientacoes", "observacoes", "dados"})
        self.assertIn("ambiguo", out)

    def test_erro_ortografico_leve(self):
        t = "avisa encomendas qndo chegarr bloco 2 ap 31"
        out = classificar_destino_texto(t, None)
        self.assertIn(out["destino"], {"observacoes", "encomendas"})


if __name__ == "__main__":
    unittest.main()
