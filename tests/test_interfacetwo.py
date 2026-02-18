import unittest

import interfacetwo


class InterfaceTwoTests(unittest.TestCase):
    def test_infer_model_color_from_text(self):
        modelo, cor = interfacetwo._infer_model_color_from_text("ABC1234 ONIX PRETO MORADOR")
        self.assertTrue(modelo.upper().startswith("ONIX"))
        self.assertTrue(cor.upper().startswith("PRETO"))

    def test_format_line_contains_core_fields(self):
        line = interfacetwo.format_line(
            {
                "DATA_HORA": "10/01/2026 10:10:10",
                "NOME": "Ana",
                "SOBRENOME": "Silva",
                "BLOCO": "A",
                "APARTAMENTO": "101",
                "PLACA": "ABC1234",
                "MODELO": "Onix",
                "COR": "Preto",
            }
        )
        self.assertIn("BLOCO A", line)
        self.assertIn("APARTAMENTO 101", line)
        self.assertIn("PLACA ABC1234", line)

    def test_filters_are_active_detection(self):
        self.assertFalse(interfacetwo._filters_are_active({"status": "Todos", "bloco": "Todos", "query": ""}))
        self.assertTrue(interfacetwo._filters_are_active({"status": "SEM CONTATO"}))
        self.assertTrue(interfacetwo._filters_are_active({"date_mode": "Específica", "date_value": "01/01/2026"}))

    def test_normalize_record_aliases_for_monitor(self):
        raw = {
            "nome": "Carlos",
            "sobrenome": "Souza",
            "bloco": "B",
            "apartamento": "202",
            "placa": "XYZ1234",
            "modelo": "Civic",
            "cor": "Prata",
            "status": "VISITANTE",
            "data_hora": "18/02/2026 11:22:33",
        }
        normalized = interfacetwo._normalize_record_for_monitor(raw)
        self.assertEqual(normalized.get("NOME"), "Carlos")
        self.assertEqual(normalized.get("SOBRENOME"), "Souza")
        self.assertEqual(normalized.get("BLOCO"), "B")
        self.assertEqual(normalized.get("APARTAMENTO"), "202")
        self.assertEqual(normalized.get("PLACA"), "XYZ1234")
        self.assertEqual(normalized.get("STATUS"), "VISITANTE")
        self.assertEqual(normalized.get("DATA_HORA"), "18/02/2026 11:22:33")

    def test_load_safe_accepts_dict_map_payload(self):
        import json, tempfile, os
        payload = {
            "1": {"nome": "ALICE", "bloco": "1", "apartamento": "101", "status": "MORADOR", "data_hora": "18/02/2026 10:00:00"},
            "2": {"nome": "BRUNO", "bloco": "2", "apartamento": "202", "status": "VISITANTE", "data_hora": "18/02/2026 10:05:00"},
        }
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0].get('NOME'), 'ALICE')
        self.assertEqual(registros[1].get('STATUS'), 'VISITANTE')

    def test_load_safe_accepts_wrapped_entries_payload(self):
        import json, tempfile, os
        payload = {
            "payload": {
                "entries": [
                    {"nome": "CARLA", "bloco": "3", "apartamento": "303", "status": "PRESTADOR", "data_hora": "18/02/2026 11:00:00"}
                ]
            }
        }
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0].get('NOME'), 'CARLA')
        self.assertEqual(registros[0].get('APARTAMENTO'), '303')

    def test_load_safe_accepts_utf8_bom_payload(self):
        import json, tempfile, os
        payload = [{"nome": "DANIEL", "bloco": "7", "apartamento": "707", "status": "MORADOR", "data_hora": "18/02/2026 12:00:00"}]
        with tempfile.NamedTemporaryFile('w', encoding='utf-8-sig', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0].get('NOME'), 'DANIEL')

    def test_load_safe_accepts_latin1_payload(self):
        import os, tempfile
        raw = '[{"nome":"JOSÉ","bloco":"8","apartamento":"808","status":"VISITANTE","data_hora":"18/02/2026 12:10:00"}]'
        with tempfile.NamedTemporaryFile('wb', suffix='.json', delete=False) as tf:
            tf.write(raw.encode('latin-1'))
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0].get('NOME'), 'JOSÉ')

    def test_load_safe_accepts_plain_string_list_payload(self):
        import json, tempfile, os
        payload = ["Visitante sem estrutura", "Entregador aguardando"]
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0].get('texto'), 'Visitante sem estrutura')

    def test_normalize_records_includes_primitive_entries(self):
        records = interfacetwo._normalize_records_for_monitor([{"nome": "ANA"}, "texto livre", 123])
        self.assertEqual(len(records), 3)
        self.assertEqual(records[1].get('texto_original'), 'texto livre')
        self.assertEqual(records[2].get('texto'), '123')

    def test_load_safe_accepts_registros_as_dict_map(self):
        import json, tempfile, os
        payload = {
            "registros": {
                "10": {"nome": "MARTA", "bloco": "9", "apartamento": "901", "status": "MORADOR", "data_hora": "18/02/2026 13:00:00"},
                "11": {"nome": "PAULO", "bloco": "9", "apartamento": "902", "status": "VISITANTE", "data_hora": "18/02/2026 13:05:00"}
            }
        }
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0].get('NOME'), 'MARTA')
        self.assertEqual(registros[1].get('APARTAMENTO'), '902')

    def test_load_safe_accepts_ndjson_payload(self):
        import os, tempfile
        raw = '\\n'.join([
            '{"nome":"LUCAS","bloco":"1","apartamento":"11","status":"MORADOR","data_hora":"18/02/2026 14:00:00"}',
            '{"nome":"RAFA","bloco":"2","apartamento":"22","status":"VISITANTE","data_hora":"18/02/2026 14:05:00"}'
        ])
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            tf.write(raw)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0].get('NOME'), 'LUCAS')


    def test_collect_status_cards_data_counts_pending_sem_contato_avisado(self):
        original_load_safe = interfacetwo._load_safe

        def fake_load_safe(path):
            if path == interfacetwo.ANALISES_ARQUIVO:
                return [{"severidade": "alta"}]
            if path == interfacetwo.AVISOS_ARQUIVO:
                return [
                    {"status": {"ativo": True, "fechado_pelo_usuario": False}},
                    {"status": {"ativo": True, "fechado_pelo_usuario": True}},
                ]
            if path == interfacetwo.ARQUIVO:
                return [{"STATUS": "SEM CONTATO"}, {"STATUS": "AVISADO"}]
            if path == interfacetwo.ENCOMENDAS_ARQUIVO:
                return [{"STATUS_ENCOMENDA": "SEM CONTATO"}, {"STATUS_ENCOMENDA": "AVISADO"}, {"STATUS_ENCOMENDA": "PENDENTE"}]
            return []

        interfacetwo._load_safe = fake_load_safe
        try:
            out = interfacetwo._collect_status_cards_data()
        finally:
            interfacetwo._load_safe = original_load_safe

        self.assertEqual(out.get('ativos'), 2)
        self.assertEqual(out.get('pendentes'), 5)
        self.assertEqual(out.get('sem_contato'), 2)
        self.assertEqual(out.get('avisado'), 2)
        self.assertEqual(out.get('alta_severidade'), 1)

    def test_filter_bar_defines_save_preset_before_button_binding(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_filter_bar)
        save_def = source.find("def _save_preset")
        save_button = source.find("build_secondary_button(actions_row, \"Salvar preset\", _save_preset)")
        self.assertNotEqual(save_def, -1)
        self.assertNotEqual(save_button, -1)
        self.assertLess(save_def, save_button)


    def test_filter_bar_uses_two_logical_rows_and_quick_group(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_filter_bar)
        self.assertIn('top_row = tk.Frame(bar', source)
        self.assertIn('actions_row = tk.Frame(bar', source)
        self.assertIn('quick_group = tk.Frame(actions_row', source)


    def test_filter_preset_lifecycle_helpers(self):
        import json, os, tempfile
        tmp = tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False)
        tmp.write('{}')
        tmp.close()
        old_prefs = interfacetwo.PREFS_FILE
        interfacetwo.PREFS_FILE = tmp.name
        try:
            interfacetwo._save_filter_presets({'turno-a': {'query': 'ana'}})
            self.assertEqual(interfacetwo._get_filter_presets().get('turno-a', {}).get('query'), 'ana')
            self.assertTrue(interfacetwo._rename_filter_preset('turno-a', 'turno-b'))
            self.assertIn('turno-b', interfacetwo._get_filter_presets())
            interfacetwo._set_filter_default_preset('controle', 'turno-b')
            self.assertEqual(interfacetwo._get_filter_default_preset('controle'), 'turno-b')
            interfacetwo._delete_filter_preset('turno-b')
            self.assertNotIn('turno-b', interfacetwo._get_filter_presets())
            self.assertEqual(interfacetwo._get_filter_default_preset('controle'), '')
        finally:
            interfacetwo.PREFS_FILE = old_prefs
            os.remove(tmp.name)

    def test_filter_bar_has_auto_apply_and_preset_management(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_filter_bar)
        self.assertIn('Aplicar automaticamente', source)
        self.assertIn('auto_apply_var.trace_add("write", _save_auto_apply_pref)', source)
        self.assertIn('Renomear preset', source)
        self.assertIn('Excluir preset', source)
        self.assertIn('Fixar preset da aba', source)

    def test_filter_feedback_uses_banner_status_without_badge_flash(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_filter_bar)
        self.assertIn('def _flash_feedback(msg, tone="info"):', source)
        start = source.find('def _flash_feedback(msg, tone="info"):')
        end = source.find('def _apply_payload', start)
        flash_block = source[start:end]
        self.assertNotIn('_update_filter_badge(transient_msg=', flash_block)

    def test_monitor_binds_f1_shortcut_help(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_monitor_ui)
        self.assertIn('root_win.bind("<F1>", _show_shortcuts, add="+")', source)


    def test_monitor_ui_has_density_toolbar_and_operation_mode_hooks(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_monitor_ui)
        self.assertIn('Densidade:', source)
        self.assertIn('values=["Compacto", "Confortável"]', source)
        self.assertIn('Exportar CSV', source)
        self.assertIn('Resetar colunas', source)
        self.assertIn('Salvar visão', source)
        self.assertIn('Registros filtrados:', source)
        self.assertIn('_runtime_refresh_ms = 1000', source)

    def test_monitor_ui_has_filter_banner_toggle_button(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_monitor_ui)
        self.assertIn('def _build_filter_banner_toggle', source)
        self.assertIn('⌄ Ocultar filtros', source)
        self.assertIn('⌃ Mostrar filtros', source)

    def test_monitor_ui_has_analytic_table_and_focus_mode_controls(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_monitor_ui)
        self.assertIn('Focus mode', source)
        self.assertIn('format_creative_entry', source)
        self.assertIn('"as_text": True', source)
        self.assertIn('Alt+E exportar', source)


    def test_control_text_mode_keeps_details_and_selection_tags(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_monitor_ui)
        self.assertIn('"controle_selected"', source)
        self.assertIn('Selecione um registro para ver detalhes.', source)

    def test_hover_supports_full_record_tag_highlight(self):
        import inspect
        source = inspect.getsource(interfacetwo._bind_hover_highlight)
        self.assertIn('"_record_" in t', source)
        self.assertIn('tag:', source)

    def test_treeview_column_menu_controls_present(self):
        import inspect
        source = inspect.getsource(interfacetwo._build_filter_bar)
        self.assertIn('if isinstance(target_widget, ttk.Treeview):', source)
        self.assertIn('control_column_order', source)
        self.assertIn('control_column_visible', source)

    def test_load_safe_accepts_concatenated_json_objects(self):
        import os, tempfile
        raw = '{"nome":"NINA","bloco":"3","apartamento":"33","status":"MORADOR","data_hora":"18/02/2026 14:10:00"}{"nome":"OTAVIO","bloco":"4","apartamento":"44","status":"VISITANTE","data_hora":"18/02/2026 14:15:00"}'
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            tf.write(raw)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[1].get('NOME'), 'OTAVIO')


if __name__ == "__main__":
    unittest.main()
