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


if __name__ == "__main__":
    unittest.main()