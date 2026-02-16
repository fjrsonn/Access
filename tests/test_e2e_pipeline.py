import json
import os
import tempfile
import unittest
from unittest import mock

import interfaceone
import ia
import runtime_status


class _Entry:
    def __init__(self, text):
        self._text = text
        self.deleted = False

    def get(self):
        return self._text

    def delete(self, *_args, **_kwargs):
        self.deleted = True
        self._text = ""

    def after(self, _ms, fn):
        fn()


class _Button:
    def __init__(self):
        self.states = []

    def config(self, **kwargs):
        self.states.append(kwargs)


class E2EPipelineTests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)

        self.paths = {
            "IN_FILE": os.path.join(self.td.name, "dadosinit.json"),
            "DB_FILE": os.path.join(self.td.name, "dadosend.json"),
            "ENCOMENDAS_IN_FILE": os.path.join(self.td.name, "encomendasinit.json"),
            "ENCOMENDAS_DB_FILE": os.path.join(self.td.name, "encomendasend.json"),
            "REVIEW_QUEUE_FILE": os.path.join(self.td.name, "fila_revisao.json"),
        }
        for p in self.paths.values():
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f)

        self.events = os.path.join(self.td.name, "runtime_events.jsonl")
        self.last = os.path.join(self.td.name, "runtime_last_status.json")
        runtime_status.EVENTS_FILE = self.events
        runtime_status.LAST_STATUS_FILE = self.last

    def _patch_interface_paths(self):
        return mock.patch.multiple(interfaceone, **self.paths)

    def test_e2e_texto_portaria_normal(self):
        entry = _Entry("VISITANTE JOAO BL A AP 101 ABC1234 ONIX PRETO")
        btn = _Button()
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value={"destino": "dados", "score": 2.0, "ambiguo": False}), \
             mock.patch.object(interfaceone, "extrair_tudo_consumo", return_value={"NOME_RAW": "JOAO SILVA", "PLACA": "ABC1234", "BLOCO": "A", "APARTAMENTO": "101", "MODELOS": ["ONIX"], "COR": "PRETO", "STATUS": "MORADOR"}), \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry, btn=btn)

        with open(self.paths["IN_FILE"], "r", encoding="utf-8") as f:
            dadosinit = json.load(f)
        with open(self.paths["DB_FILE"], "r", encoding="utf-8") as f:
            dadosend = json.load(f)

        self.assertEqual(len(dadosinit["registros"]), 1)
        self.assertEqual(len(dadosend["registros"]), 1)
        self.assertTrue(entry.deleted)

    def test_e2e_texto_encomenda(self):
        entry = _Entry("PACOTE SHOPEE BLOCO A AP 101")
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value={"destino": "encomendas", "score": 3.0, "ambiguo": False}), \
             mock.patch.object(interfaceone, "_save_encomenda_init") as m_save_enc, \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry)
            self.assertTrue(m_save_enc.called)

    def test_e2e_encomenda_com_classificador_confiante_em_orientacoes_ainda_vai_para_encomendas(self):
        entry = _Entry("ENVELOP RIACHUELO BLO13 APARTAMEN109 JOAO")
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value={"destino": "orientacoes", "score": 3.0, "ambiguo": False, "confianca": 0.92}), \
             mock.patch.object(interfaceone, "extrair_tudo_consumo", return_value={}), \
             mock.patch.object(interfaceone, "_save_encomenda_init") as m_save_enc, \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry)
            self.assertTrue(m_save_enc.called)

    def test_e2e_texto_orientacao_usuario_nao_vai_para_encomendas(self):
        entry = _Entry("Registrando ocorrencia de clamacao de barulho vindo do bloco 10 aparamneto 10, morador Flavio Junior foi orientado.")
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "_save_encomenda_init") as m_save_enc, \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry)

        self.assertFalse(m_save_enc.called)
        with open(self.paths["ENCOMENDAS_IN_FILE"], "r", encoding="utf-8") as f:
            encomendas_init = json.load(f)
        self.assertEqual(len(encomendas_init["registros"]), 0)

    def test_e2e_texto_ambiguo_vai_para_fila_revisao(self):
        entry = _Entry("texto livre extremamente ambiguo")
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value={"destino": "dados", "score": 0.4, "ambiguo": True, "confianca": 0.2, "scores": {"encomendas": 0.3}}), \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry)

        with open(self.paths["REVIEW_QUEUE_FILE"], "r", encoding="utf-8") as f:
            fila = json.load(f)
        self.assertEqual(len(fila.get("registros", [])), 1)

    def test_e2e_encomenda_dispara_pipeline_mesmo_com_chat_ativo(self):
        entry = _Entry("PACOTE SHOPEE BLOCO A AP 101")
        fake_thread = mock.Mock()
        fake_ia = mock.Mock()
        fake_ia.processar = mock.Mock()
        fake_ia.is_chat_mode_active = mock.Mock(return_value=True)
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value={"destino": "encomendas", "score": 3.0, "ambiguo": False}), \
             mock.patch.object(interfaceone, "_save_encomenda_init") as m_save_enc, \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", True), \
             mock.patch.object(interfaceone, "ia_module", fake_ia), \
             mock.patch.object(interfaceone.threading, "Thread", return_value=fake_thread) as m_thread:
            interfaceone.save_text(entry_widget=entry)

        self.assertTrue(m_save_enc.called)
        m_thread.assert_called_once_with(target=fake_ia.processar, daemon=True)
        fake_thread.start.assert_called_once()

    def test_e2e_erro_preprocess_ainda_salva(self):
        entry = _Entry("texto qualquer")
        with self._patch_interface_paths(), \
             mock.patch.object(interfaceone, "extrair_tudo_consumo", side_effect=RuntimeError("boom")), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value={"destino": "dados", "score": 1.0, "ambiguo": False}), \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry)

        with open(self.paths["IN_FILE"], "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.assertEqual(len(payload["registros"]), 1)

    def test_e2e_lock_ocupado_ia(self):
        with mock.patch.object(ia, "is_chat_mode_active", return_value=False), \
             mock.patch.object(ia, "acquire_lock", return_value=False):
            ia.processar()
        events = runtime_status.read_runtime_events(self.events)
        self.assertTrue(any(e.get("stage") == "lock_not_acquired" for e in events))

    def test_e2e_erro_llm_e_recuperacao_persistencia(self):
        entrada = os.path.join(self.td.name, "dadosinit_ia.json")
        saida = os.path.join(self.td.name, "dadosend_ia.json")
        encom_i = os.path.join(self.td.name, "encom_i.json")
        encom_o = os.path.join(self.td.name, "encom_o.json")
        for p in (saida, encom_i, encom_o):
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f)
        with open(entrada, "w", encoding="utf-8") as f:
            json.dump({"registros": [{"id": 1, "texto": "JOAO BL A AP 101 ABC1234", "processado": False, "data_hora": "10/01/2026 10:00:00"}]}, f)

        save_calls = {"count": 0}

        def flaky_save(path, data):
            if path == entrada and save_calls["count"] == 0:
                save_calls["count"] += 1
                raise OSError("falha temporaria")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

        fake_client = mock.Mock()
        fake_client.chat.completions.create.side_effect = RuntimeError("llm error")

        with mock.patch.multiple(
            ia,
            ENTRADA=entrada,
            SAIDA=saida,
            ENCOMENDAS_ENTRADA=encom_i,
            ENCOMENDAS_SAIDA=encom_o,
            LOCK_FILE=os.path.join(self.td.name, "lock"),
            client=fake_client,
        ), \
            mock.patch.object(ia, "salvar_atomico", side_effect=flaky_save), \
            mock.patch.object(ia, "acquire_lock", return_value=True), \
            mock.patch.object(ia, "release_lock", return_value=None):
            ia.processar()

        events = runtime_status.read_runtime_events(self.events)
        stages = [e.get("stage") for e in events]
        self.assertIn("llm_call_failed", stages)
        self.assertIn("save_entrada_failed", stages)
        self.assertIn("save_saida_ok", stages)

    def test_e2e_replay_idempotent_por_entrada_id(self):
        saida = os.path.join(self.td.name, "dadosend_replay.json")
        with open(saida, "w", encoding="utf-8") as f:
            json.dump({"registros": []}, f)

        with mock.patch.object(ia, "SAIDA", saida):
            first = {"NOME": "ANA", "SOBRENOME": "SILVA", "PLACA": "ABC1234", "MODELO": "ONIX", "COR": "PRETO", "BLOCO": "A", "APARTAMENTO": "101", "STATUS": "VISITANTE", "DATA_HORA": "10/01/2026 10:00:00"}
            second = {"NOME": "ANA", "SOBRENOME": "SILVA", "PLACA": "ABC1234", "MODELO": "ONIX", "COR": "PRETO", "BLOCO": "A", "APARTAMENTO": "101", "STATUS": "VISITANTE", "DATA_HORA": "10/01/2026 09:50:00"}
            ia.append_or_update_saida(first, entrada_id=77)
            ia.append_or_update_saida(second, entrada_id=77)

        with open(saida, "r", encoding="utf-8") as f:
            registros = (json.load(f) or {}).get("registros") or []
        self.assertEqual(len(registros), 1)
        self.assertEqual(str(registros[0].get("_entrada_id")), "77")

    def test_e2e_encomenda_so_marca_processado_apos_saida(self):
        entrada = os.path.join(self.td.name, "dadosinit_encomenda_fail.json")
        saida = os.path.join(self.td.name, "dadosend_encomenda_fail.json")
        encom_i = os.path.join(self.td.name, "encom_i_fail.json")
        encom_o = os.path.join(self.td.name, "encom_o_fail.json")

        with open(entrada, "w", encoding="utf-8") as f:
            json.dump({"registros": []}, f)
        with open(saida, "w", encoding="utf-8") as f:
            json.dump({"registros": []}, f)
        with open(encom_o, "w", encoding="utf-8") as f:
            json.dump({"registros": []}, f)
        with open(encom_i, "w", encoding="utf-8") as f:
            json.dump({"registros": [{"id": 99, "texto": "PACOTE SHOPEE BLOCO A AP 101", "processado": False, "data_hora": "10/01/2026 10:00:00"}]}, f)

        with mock.patch.multiple(
            ia,
            ENTRADA=entrada,
            SAIDA=saida,
            ENCOMENDAS_ENTRADA=encom_i,
            ENCOMENDAS_SAIDA=encom_o,
            LOCK_FILE=os.path.join(self.td.name, "lock_encomenda_fail"),
        ),             mock.patch.object(ia, "append_or_update_encomendas", return_value=False),             mock.patch.object(ia, "acquire_lock", return_value=True),             mock.patch.object(ia, "release_lock", return_value=None):
            ia.processar()

        with open(encom_i, "r", encoding="utf-8") as f:
            init_regs = (json.load(f) or {}).get("registros") or []
        self.assertEqual(len(init_regs), 1)
        self.assertFalse(bool(init_regs[0].get("processado")))

        events = runtime_status.read_runtime_events(self.events)
        stages = [e.get("stage") for e in events]
        self.assertIn("save_encomendas_saida_failed", stages)

    def test_e2e_evento_atrasado_nao_quebra_ordem_temporal(self):
        saida = os.path.join(self.td.name, "dadosend_temporal.json")
        with open(saida, "w", encoding="utf-8") as f:
            json.dump({"registros": []}, f)

        with mock.patch.object(ia, "SAIDA", saida):
            recente = {"NOME": "JOAO", "SOBRENOME": "LIMA", "PLACA": "AAA1111", "MODELO": "GOL", "COR": "PRATA", "BLOCO": "B", "APARTAMENTO": "201", "STATUS": "VISITANTE", "DATA_HORA": "10/01/2026 10:10:00"}
            atrasado = {"NOME": "MARIA", "SOBRENOME": "LIMA", "PLACA": "BBB2222", "MODELO": "ARGO", "COR": "BRANCO", "BLOCO": "B", "APARTAMENTO": "202", "STATUS": "VISITANTE", "DATA_HORA": "10/01/2026 09:00:00"}
            ia.append_or_update_saida(recente, entrada_id=88)
            ia.append_or_update_saida(atrasado, entrada_id=89)

        with open(saida, "r", encoding="utf-8") as f:
            registros = (json.load(f) or {}).get("registros") or []
        self.assertEqual(len(registros), 2)
        horas = sorted(r.get("DATA_HORA") for r in registros)
        self.assertEqual(horas, ["10/01/2026 09:00:00", "10/01/2026 10:10:00"])


if __name__ == "__main__":
    unittest.main()
