import os
import tempfile
import unittest
from unittest import mock

import ia


class IAModuleTests(unittest.TestCase):
    def tearDown(self):
        ia._RETRY_SCHEDULED = False

    def test_uppercase_dict_values(self):
        data = {"nome": "ana", "nested": {"sobrenome": "silva"}, "arr": ["x", "y"]}
        out = ia.uppercase_dict_values(data)
        self.assertEqual(out["nome"], "ANA")
        self.assertEqual(out["nested"]["sobrenome"], "SILVA")
        self.assertEqual(out["arr"], ["X", "Y"])

    def test_apply_agent_prompt_template(self):
        old = os.environ.get("USE_AGENT_PROMPT")
        try:
            os.environ["USE_AGENT_PROMPT"] = "1"
            ia._AGENT_PROMPT_ATIVO = "Template\n<<TEMPLATE_RESPOSTA>>\nRESPOSTA: {RESPOSTA_BASE}"
            out = ia._apply_agent_prompt_template("OK")
            self.assertIn("RESPOSTA:", out)
            self.assertIn("OK", out)
        finally:
            if old is None:
                os.environ.pop("USE_AGENT_PROMPT", None)
            else:
                os.environ["USE_AGENT_PROMPT"] = old
            ia._AGENT_PROMPT_ATIVO = ""

    def test_handle_input_text_commands(self):
        ia.IN_IA_MODE = False
        changed, msg = ia.handle_input_text("IA")
        self.assertTrue(changed)
        self.assertTrue(ia.IN_IA_MODE)
        self.assertTrue(isinstance(msg, str) and msg)

        changed, msg = ia.handle_input_text("SAIR")
        self.assertTrue(changed)
        self.assertFalse(ia.IN_IA_MODE)
        self.assertTrue(isinstance(msg, str) and msg)


    def test_parse_encomenda_nome_sem_ruido_de_endereco(self):
        txt = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["NOME"], "JOÃO")
        self.assertEqual(out["SOBRENOME"], "PEREIRA")
        self.assertEqual(out["BLOCO"], "13")
        self.assertEqual(out["APARTAMENTO"], "111")

    def test_parse_encomenda_identificacao_alfanumerica_sem_digitos(self):
        txt = "JADLOG BL13 CAIX APARTAMEN11 BRUNO SOUZA OSIJEVXTKTOTI"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["IDENTIFICACAO"], "OSIJEVXTKTOTI")
        self.assertEqual(out["LOJA"], "JADLOG")
        self.assertEqual(out["TIPO"], "CAIXA")

    def test_parse_encomenda_with_aliases(self):
        txt = "SED 9C3R4DUHASD BEATRIZ LOPES BLCO7 APARTAMENTO86 ENVELOP"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["TIPO"], "ENVELOPE")
        self.assertEqual(out["LOJA"], "CORREIOS")
        self.assertEqual(out["BLOCO"], "7")
        self.assertEqual(out["APARTAMENTO"], "86")
        self.assertEqual(out["IDENTIFICACAO"], "9C3R4DUHASD")

    def test_parse_encomenda_loja_composta_com_espaco(self):
        txt = "BLCO8 101721960326BR RAFAEL LIMA MERC LIVR SAOLA AP93"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["LOJA"], "MERCADO LIVRE")
        self.assertEqual(out["TIPO"], "SACOLA")

    def test_parse_encomenda_loja_com_caractere_especial(self):
        txt = "PACOT BLO14 CARLOS SANTOS C&A AP125 QDD0VNQNBIYL0"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["LOJA"], "CEA")
        self.assertEqual(out["TIPO"], "PACOTE")

    def test_parse_encomenda_texto_orientacao_nao_inventa_loja_tipo(self):
        txt = "Registrando ocorrencia de clamacao de barulho vindo do bloco 10 aparamneto 10, morador Flavio Junior foi orientado"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["LOJA"], "-")
        self.assertEqual(out["TIPO"], "-")

    def test_append_or_update_encomendas_falha_quando_save_falha(self):
        with mock.patch.object(ia, "_load_encomendas_saida", return_value=[]), \
            mock.patch.object(ia, "_save_encomendas_saida", return_value=False):
            ok = ia.append_or_update_encomendas({"NOME": "ANA", "BLOCO": "A", "APARTAMENTO": "101"}, entrada_id=123)
        self.assertFalse(ok)

    def test_processar_agenda_retry_quando_lock_ocupado(self):
        with mock.patch.object(ia, "is_chat_mode_active", return_value=False), \
             mock.patch.object(ia, "acquire_lock", return_value=False), \
             mock.patch.object(ia, "_schedule_process_retry", return_value=True) as m_retry:
            ia.processar()
        m_retry.assert_called_once_with("lock_not_acquired")

    def test_schedule_process_retry_evita_agendamento_duplicado(self):
        fake_timer = mock.Mock()
        with mock.patch.object(ia.threading, "Timer", return_value=fake_timer) as m_timer:
            first = ia._schedule_process_retry("test")
            second = ia._schedule_process_retry("test")

        self.assertTrue(first)
        self.assertFalse(second)
        m_timer.assert_called_once()
        fake_timer.start.assert_called_once()

    def test_acquire_lock_remove_stale_lock_e_adquire(self):
        with tempfile.TemporaryDirectory() as td:
            lock_path = os.path.join(td, "process.lock")
            with open(lock_path, "w", encoding="utf-8") as f:
                f.write("stale")
            old_ts = 1000.0
            os.utime(lock_path, (old_ts, old_ts))

            with mock.patch.object(ia, "LOCK_FILE", lock_path), \
                 mock.patch.object(ia, "LOCK_STALE_SECONDS", 0.01):
                ok = ia.acquire_lock(timeout=0.2)
                self.assertTrue(ok)
                ia.release_lock()



if __name__ == "__main__":
    unittest.main()
