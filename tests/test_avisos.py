import unittest

import avisos


class AvisosModuleTests(unittest.TestCase):
    def test_registro_event_id_priority(self):
        rec = {"id": 1, "ID": 2, "_entrada_id": "x-9"}
        self.assertEqual(avisos._registro_event_id(rec), "x-9")

    def test_aviso_exists_and_reactivate(self):
        existing = [
            {
                "identidade": "ANA|SILVA|A|10",
                "tipo": "TIPO_1",
                "ultimo_registro": {"ID": 8},
                "status": {"ativo": False, "fechado_pelo_usuario": True},
                "timestamps": {"fechado_em": "10/01/2026 10:00:00"},
            }
        ]

        self.assertTrue(avisos._aviso_exists(existing, "ANA|SILVA|A|10", 8, "TIPO_1"))
        changed = avisos._reactivate_existing_aviso(existing, "ANA|SILVA|A|10", 8, "TIPO_1")
        self.assertTrue(changed)
        self.assertTrue(existing[0]["status"]["ativo"])
        self.assertFalse(existing[0]["status"]["fechado_pelo_usuario"])
        self.assertIsNone(existing[0]["timestamps"]["fechado_em"])

    def test_vehicles_considered_same_with_plate(self):
        a = {"PLACA": "ABC1234", "MODELO": "ONIX", "COR": "PRETO"}
        b = {"PLACA": "ABC1234", "MODELO": "ONIX", "COR": "PRETO"}
        c = {"PLACA": "XYZ1234", "MODELO": "ONIX", "COR": "PRETO"}
        self.assertTrue(avisos.vehicles_considered_same(a, b))
        self.assertFalse(avisos.vehicles_considered_same(a, c))

    def test_reactivate_sem_tag_por_entrada_id_ignora_identidade(self):
        existing = [
            {
                "identidade": "SEMNOME||A|1",
                "tipo": "MORADOR_SEM_TAG",
                "ultimo_registro": {"_entrada_id": 55},
                "status": {"ativo": False, "fechado_pelo_usuario": True},
                "timestamps": {"fechado_em": "10/01/2026 10:00:00"},
            }
        ]
        changed = avisos._reactivate_existing_aviso(existing, "ANA|SILVA|A|1", 55, "MORADOR_SEM_TAG")
        self.assertTrue(changed)
        self.assertTrue(existing[0]["status"]["ativo"])


if __name__ == "__main__":
    unittest.main()
