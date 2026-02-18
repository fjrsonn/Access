import unittest

import ui_theme


class UIThemeTokensTests(unittest.TestCase):
    def test_presets_have_design_tokens(self):
        required = {
            "font_family", "font_sm", "font_md", "font_lg", "font_xl",
            "space_1", "space_2", "space_3", "space_4", "space_5", "space_6",
            "disabled_bg", "disabled_fg", "info", "on_info", "selection_bg", "selection_fg",
            "on_surface", "on_primary",
        }
        for name, preset in ui_theme.THEME_PRESETS.items():
            missing = required.difference(preset.keys())
            self.assertFalse(missing, f"Preset {name} missing tokens: {sorted(missing)}")

    def test_contrast_snapshot_by_theme(self):
        snapshots = {}
        for name, preset in ui_theme.THEME_PRESETS.items():
            out = ui_theme.validate_theme_contrast(preset)
            snapshots[name] = out["ratios"]
            self.assertFalse(out["warnings"], f"Theme {name} has contrast warnings: {out['warnings']}")

        self.assertIn("escuro", snapshots)
        self.assertIn("claro", snapshots)
        self.assertIn("alto_contraste", snapshots)

    def test_typography_presets_exist(self):
        self.assertIn("compacto", ui_theme.TYPOGRAPHY_PRESETS)
        self.assertIn("padrao", ui_theme.TYPOGRAPHY_PRESETS)
        self.assertIn("acessivel", ui_theme.TYPOGRAPHY_PRESETS)

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_state_system_priority_and_helpers_exist(self):
        self.assertEqual(ui_theme.STATE_PRIORITY.get("danger"), 4)
        self.assertTrue(callable(ui_theme.state_colors))
        self.assertEqual(ui_theme.normalize_tone("error"), "danger")

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_state_system_priority_and_helpers_exist(self):
        self.assertEqual(ui_theme.STATE_PRIORITY.get("danger"), 4)
        self.assertTrue(callable(ui_theme.state_colors))
        self.assertEqual(ui_theme.normalize_tone("error"), "danger")

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



    def test_combobox_focus_map_includes_primary_indicator(self):
        import inspect
        source = inspect.getsource(ui_theme.apply_ttk_theme_styles)
        self.assertIn('bordercolor=[("focus", UI_THEME.get("primary"', source)
        self.assertIn('lightcolor=[("focus", UI_THEME.get("primary"', source)

    def test_state_system_priority_and_helpers_exist(self):
        self.assertEqual(ui_theme.STATE_PRIORITY.get("danger"), 4)
        self.assertTrue(callable(ui_theme.state_colors))
        self.assertEqual(ui_theme.normalize_tone("error"), "danger")

    def test_semantic_secondary_button_builders_exist(self):
        self.assertTrue(callable(ui_theme.build_secondary_warning_button))
        self.assertTrue(callable(ui_theme.build_secondary_danger_button))



if __name__ == "__main__":
    unittest.main()