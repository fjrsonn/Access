import os
import unittest

import ia


class IAModuleTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
