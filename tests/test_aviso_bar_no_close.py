import pathlib
import unittest


class AvisoBarNoCloseTests(unittest.TestCase):
    def test_aviso_bar_has_no_close_button_or_x_glyph(self):
        src = pathlib.Path('interfaceone.py').read_text(encoding='utf-8')
        aviso_start = src.find('class AvisoBar(tk.Frame):')
        warning_start = src.find('\nclass WarningBar(tk.Frame):')
        self.assertNotEqual(aviso_start, -1)
        self.assertNotEqual(warning_start, -1)
        trecho = src[aviso_start:warning_start]
        self.assertNotIn('btn_close', trecho)
        self.assertNotIn('✕', trecho)
        self.assertNotIn('_on_close_click', trecho)


if __name__ == '__main__':
    unittest.main()
