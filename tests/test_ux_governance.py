import json
import pathlib
import tempfile
import unittest

import runtime_status


class UXGovernanceTests(unittest.TestCase):
    def test_design_system_playbook_exists_with_required_sections(self):
        content = pathlib.Path("DESIGN_SYSTEM.md").read_text(encoding="utf-8")
        self.assertIn("## Tokens e quando usar", content)
        self.assertIn("## A11y (AA operacional) checklist por tela", content)
        self.assertIn("## Guia de microcopy", content)
        self.assertIn("## Regra de PR (obrigatória)", content)

    def test_runtime_ux_metrics_dashboard_keys(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as f:
            path = f.name
            f.write(json.dumps({"timestamp": "2026-01-10 10:00:00", "action": "ux_metrics", "status": "STARTED", "stage": "filter_apply_started", "details": {}}) + "\n")
            f.write(json.dumps({"timestamp": "2026-01-10 10:00:01", "action": "ux_metrics", "status": "OK", "stage": "filter_apply", "details": {}}) + "\n")
            f.write(json.dumps({"timestamp": "2026-01-10 10:00:02", "action": "ux_metrics", "status": "OK", "stage": "edit_save", "details": {}}) + "\n")
            f.write(json.dumps({"timestamp": "2026-01-10 10:00:03", "action": "ux_metrics", "status": "OK", "stage": "theme_switch", "details": {}}) + "\n")
            f.write(json.dumps({"timestamp": "2026-01-10 10:00:04", "action": "ux_metrics", "status": "OK", "stage": "shortcut_used", "details": {}}) + "\n")

        out = runtime_status.analisar_metricas_ux(path)
        self.assertIn("time_to_apply_filter_ms", out)
        self.assertIn("edit_save_success_rate", out)
        self.assertIn("theme_switch_count", out)
        self.assertIn("keyboard_shortcut_adoption", out)


if __name__ == "__main__":
    unittest.main()
