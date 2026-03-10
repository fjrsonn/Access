import pathlib
import unittest


class UILayoutSmokeTests(unittest.TestCase):
    def test_monitor_filter_has_accessibility_shortcuts(self):
        src = pathlib.Path("interfacetwo.py").read_text(encoding="utf-8")
        self.assertIn("<Control-Return>", src)
        self.assertIn("<Control-Shift-L>", src)
        self.assertIn("<Alt-Key-1>", src)
        self.assertIn("<Alt-Key-4>", src)

    def test_selection_tokens_are_used_in_styles(self):
        src1 = pathlib.Path("interfaceone.py").read_text(encoding="utf-8")
        src2 = pathlib.Path("interfacetwo.py").read_text(encoding="utf-8")
        self.assertIn('UI_THEME.get("selection_bg"', src1)
        self.assertIn('UI_THEME.get("selection_fg"', src1)
        self.assertIn('UI_THEME.get("selection_bg"', src2)
        self.assertIn('UI_THEME.get("selection_fg"', src2)

    def test_contextual_refresh_theme_uses_context_switch(self):
        src = pathlib.Path("ui_theme.py").read_text(encoding="utf-8")
        self.assertIn('if ctx in {"interfacetwo", "monitor"}', src)
        self.assertIn('container_bg = UI_THEME.get("bg"', src)
        self.assertIn('container_bg = UI_THEME.get("light_bg"', src)


    def test_main_window_uses_responsive_height_constraints(self):
        src = pathlib.Path("interfaceone.py").read_text(encoding="utf-8")
        self.assertIn('window.minsize(900, min(320, max(220, int(screen_h * 0.24))))', src)
        self.assertIn('height = min(max(220, requested_h), max(220, int(screen_h * 0.46)))', src)


    def test_monitor_layout_adaptation_is_debounced(self):
        src = pathlib.Path("interfacetwo.py").read_text(encoding="utf-8")
        self.assertIn('_layout_adapt_state = {"scheduled": False, "running": False}', src)
        self.assertIn('def _queue_monitor_layout_adapt(_event=None):', src)
        self.assertIn('container.bind("<Configure>", _queue_monitor_layout_adapt, add="+")', src)

    def test_monitor_details_panel_is_allocated_and_scrollable(self):
        src = pathlib.Path("interfacetwo.py").read_text(encoding="utf-8")
        self.assertIn('control_split.add(details_host, minsize=120, stretch="always")', src)
        self.assertIn('details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)', src)
        self.assertIn('details_scroll.pack(side=tk.RIGHT, fill=tk.Y', src)

    def test_aviso_bar_keeps_compact_height_without_overlap_padding(self):
        src = pathlib.Path("interfaceone.py").read_text(encoding="utf-8")
        self.assertIn('self._bar_height = max(26, self.font.metrics("linespace") + 8)', src)
        self.assertIn('self.pack(in_=container, before=parent_frame, fill=tk.X, pady=(0,2))', src)


    def test_metric_card_compact_mode_hides_meta_line(self):
        src = pathlib.Path("ui_components.py").read_text(encoding="utf-8")
        self.assertIn('if compact:', src)
        self.assertIn('self.meta_lbl.pack_forget()', src)

    def test_monitor_has_presets_and_status_cards(self):
        src = pathlib.Path("interfacetwo.py").read_text(encoding="utf-8")
        self.assertIn("Salvar preset", src)
        self.assertIn("Preset (opcional)", src)
        self.assertIn("AppMetricCard", src)
        self.assertIn("AppStatusBar", src)
        self.assertIn("Modo Operação", src)
        self.assertIn("Desfazer", src)
        self.assertIn("Hoje", src)
        self.assertIn("Sem contato", src)
        self.assertIn("_apply_payload(_filter_state.get(filter_key)", src)
        self.assertIn("filters_auto_reset", src)


if __name__ == "__main__":
    unittest.main()