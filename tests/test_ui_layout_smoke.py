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


if __name__ == "__main__":
    unittest.main()