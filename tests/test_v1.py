import json
import tempfile
import unittest
from pathlib import Path

from backend import database, pipeline
from backend.filtros.keywords import filtrar_vacante
from backend.filtros.texto import canonicalizar_link, generar_dedupe_key, normalizar_texto


PERFIL = {
    "nombre": "Prueba",
    "keywords_incluir": json.dumps(["react", "typescript"]),
    "keywords_excluir": json.dumps(["java"]),
}


class TextoTests(unittest.TestCase):
    def test_normaliza_unicode_y_tildes(self):
        self.assertEqual(normalizar_texto("𝐑𝐞𝐚𝐜𝐭  Ágil"), "react agil")

    def test_canonicaliza_linkedin_y_tracking(self):
        link = "https://www.linkedin.com/jobs/view/12345/?utm_source=x#detalle"
        self.assertEqual(canonicalizar_link(link), "https://www.linkedin.com/jobs/view/12345")

    def test_identidad_sin_link_es_estable(self):
        vacante = {"fuente": "linkedin_feed", "titulo": "React", "empresa": "", "descripcion": "Buscamos React"}
        self.assertEqual(generar_dedupe_key(vacante), generar_dedupe_key(vacante))


class FiltroTests(unittest.TestCase):
    def test_veto_deseable_despues_de_beneficios_no_es_duro(self):
        vacante = {
            "titulo": "Frontend React",
            "ubicacion": "Remoto Colombia",
            "descripcion": "Requisitos: React y TypeScript. Beneficios: seguro. Deseable: Kubernetes.",
        }
        resultado = filtrar_vacante(vacante, PERFIL)
        self.assertTrue(resultado["pasa"])
        self.assertIn("kubernetes", [gap["keyword"] for gap in resultado["detalle"]["gaps_blandos"]])

    def test_veto_duro_posterior_prevalece_sobre_deseable(self):
        vacante = {
            "titulo": "Frontend React",
            "ubicacion": "Remoto Colombia",
            "descripcion": "Deseable: Kubernetes. Requisitos: React, TypeScript y Kubernetes.",
        }
        resultado = filtrar_vacante(vacante, PERFIL)
        self.assertFalse(resultado["pasa"])
        self.assertEqual(resultado["razon"], "veto_stack")

    def test_alias_next_suma_una_vez(self):
        vacante = {
            "titulo": "Next.js Nextjs Frontend",
            "ubicacion": "Remoto Colombia",
            "descripcion": "Requisitos: React y TypeScript.",
        }
        resultado = filtrar_vacante(vacante, PERFIL)
        next_entries = [item for item in resultado["detalle"]["positivos"] if item["keyword"] == "next"]
        self.assertEqual(len(next_entries), 1)


class PersistenciaTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temporal.name) / "tracker.db")
        self.original_db = database.DB_PATH
        database.DB_PATH = self.db_path
        database.init_db()

    def tearDown(self):
        database.DB_PATH = self.original_db
        self.temporal.cleanup()

    def test_guardar_sin_link_y_evitar_duplicado(self):
        vacante = {
            "dedupe_key": "contenido:uno",
            "titulo": "Vacante feed",
            "descripcion": "Buscamos frontend",
            "link": "",
            "fuente": "linkedin_feed",
            "estado_inicial": "pendiente",
        }
        creada = database.create_aplicacion(vacante)
        self.assertEqual(creada["estado"], "pendiente")
        self.assertEqual(database.create_aplicacion(vacante), None)

    def test_aplicar_registra_fecha_y_notas(self):
        creada = database.create_aplicacion({
            "dedupe_key": "link:dos",
            "titulo": "Frontend",
            "descripcion": "React",
            "link": "https://example.com/job",
            "fuente": "prueba",
            "estado_inicial": "aplicado",
        })
        self.assertIsNotNone(creada["fecha_aplicacion"])
        actualizada = database.update_notas(creada["id"], "Enviar seguimiento el viernes")
        self.assertEqual(actualizada["notas"], "Enviar seguimiento el viernes")


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        raiz = Path(self.temporal.name)
        self.raw = raiz / "raw"
        self.raw.mkdir()
        self.salida = raiz / "filtradas.json"
        self.db = raiz / "tracker.db"
        self.original = (database.DB_PATH, pipeline.RAW_DATA_PATH, pipeline.FILTRADAS_PATH)
        database.DB_PATH = str(self.db)
        pipeline.RAW_DATA_PATH = str(self.raw)
        pipeline.FILTRADAS_PATH = str(self.salida)
        database.init_db()

    def tearDown(self):
        database.DB_PATH, pipeline.RAW_DATA_PATH, pipeline.FILTRADAS_PATH = self.original
        self.temporal.cleanup()

    def test_deduplica_y_separa_feed(self):
        estructurada = {
            "titulo": "Frontend React",
            "empresa": "Acme",
            "ubicacion": "Remoto Colombia",
            "descripcion": "Requisitos: React, TypeScript, Tailwind y 4 años.",
            "link": "https://example.com/jobs/1?utm_source=uno",
        }
        feed = {
            "descripcion": "Estamos buscando Frontend React con TypeScript. Envía tu CV a jobs@example.com",
            "autor_perfil": "",
        }
        (self.raw / "linkedin_a.json").write_text(json.dumps([estructurada, estructurada]), encoding="utf-8")
        (self.raw / "linkedin_feed_a.json").write_text(json.dumps([feed]), encoding="utf-8")

        resultado = pipeline.filtrar_raw_data()
        self.assertTrue(resultado["ok"])
        documento = pipeline.leer_filtradas()
        self.assertEqual(len(documento["vacantes"]), 1)
        self.assertEqual(len(documento["feed"]), 1)
        self.assertEqual(resultado["stats"]["duplicadas"], 1)


if __name__ == "__main__":
    unittest.main()
