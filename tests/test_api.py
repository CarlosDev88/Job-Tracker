"""Tests de los endpoints HTTP.

Complementan a test_v1.py, que cubre la lógica pura. Acá se ejercita la capa
que el frontend consume de verdad: validación de parámetros, códigos de estado
y la forma exacta de las respuestas.
"""

import importlib
import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend import database, main, pipeline


VACANTE = {
    "titulo": "Frontend React",
    "empresa": "Acme",
    "ubicacion": "Remoto Colombia",
    "descripcion": "Requisitos: React, TypeScript, Tailwind y 4 anios.",
    "link": "https://example.com/jobs/1",
}
REVISAR = {
    "titulo": "Oportunidad",
    "empresa": "Ambigua",
    "ubicacion": "",
    "descripcion": "Escribeme por interno si te interesa el tema del rol.",
    "link": "https://example.com/jobs/2",
}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        raiz = Path(self.temporal.name)
        self.raw = raiz / "raw"
        self.raw.mkdir()
        self.original = (database.DB_PATH, pipeline.RAW_DATA_PATH, pipeline.FILTRADAS_PATH)
        database.DB_PATH = str(raiz / "tracker.db")
        pipeline.RAW_DATA_PATH = str(self.raw)
        pipeline.FILTRADAS_PATH = str(raiz / "filtradas.json")
        database.init_db()
        self.cliente = TestClient(main.app)

    def tearDown(self):
        database.DB_PATH, pipeline.RAW_DATA_PATH, pipeline.FILTRADAS_PATH = self.original
        self.temporal.cleanup()

    def _sembrar(self, items, nombre="linkedin_a.json"):
        (self.raw / nombre).write_text(json.dumps(items), encoding="utf-8")
        respuesta = self.cliente.post("/pipeline/filtrar")
        self.assertEqual(respuesta.status_code, 200, respuesta.text)
        return respuesta.json()

    # --- salud y perfil ---------------------------------------------------

    def test_health(self):
        self.assertEqual(self.cliente.get("/health").json(), {"status": "ok"})

    def test_perfil_se_lee_y_se_actualiza(self):
        self.assertEqual(self.cliente.get("/perfil").status_code, 200)
        respuesta = self.cliente.put("/perfil", json={"empresas_bloqueadas": ["BairesDev"]})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(json.loads(respuesta.json()["empresas_bloqueadas"]), ["BairesDev"])

    # --- pipeline ---------------------------------------------------------

    def test_filtrar_sin_archivos_da_400_no_500(self):
        self.assertEqual(self.cliente.post("/pipeline/filtrar").status_code, 400)

    def test_un_item_invalido_no_tumba_la_corrida(self):
        # El scraper emite null en campos de texto; antes, un solo item asi
        # devolvia 500 y no se procesaba ningun archivo.
        stats = self._sembrar([{"titulo": "X", "descripcion": None}, VACANTE])["stats"]
        self.assertEqual(stats["filtradas"], 1)

    def test_estado_no_arrastra_las_listas_completas(self):
        self._sembrar([VACANTE])
        cuerpo = self.cliente.get("/pipeline/estado").json()
        self.assertIn("stats", cuerpo)
        self.assertNotIn("vacantes", cuerpo)

    def test_estado_tolera_json_corrupto(self):
        Path(pipeline.FILTRADAS_PATH).write_text('{"vacantes": [1,2,', encoding="utf-8")
        self.assertEqual(self.cliente.get("/pipeline/estado").status_code, 200)
        self.assertEqual(self.cliente.get("/pipeline/filtradas").status_code, 200)

    # --- resultados -------------------------------------------------------

    def test_conteos(self):
        self._sembrar([VACANTE])
        self.assertEqual(self.cliente.get("/resultados/conteos").json()["vacantes"], 1)

    def test_filtros_y_paginacion(self):
        self._sembrar([VACANTE])
        cuerpo = self.cliente.get("/resultados", params={"tipo_resultado": "vacante"}).json()
        self.assertEqual(cuerpo["total"], 1)
        self.assertEqual(cuerpo["items"][0]["empresa"], "Acme")
        self.assertIn("tracking", cuerpo["items"][0])

        vacio = self.cliente.get("/resultados", params={"busqueda": "cobol"}).json()
        self.assertEqual(vacio["total"], 0)

    def test_por_pagina_se_acota(self):
        self._sembrar([VACANTE])
        cuerpo = self.cliente.get("/resultados", params={"por_pagina": 999999}).json()
        self.assertLessEqual(cuerpo["por_pagina"], 100)

    def test_pagina_no_numerica_da_422(self):
        self.assertEqual(self.cliente.get("/resultados", params={"pagina": "abc"}).status_code, 422)

    def test_solo_revisar_ignora_el_rango_de_score(self):
        # Ambos filtros juntos daban una condicion imposible y la lista salia
        # vacia siempre; manda el checkbox.
        self._sembrar([VACANTE, REVISAR], nombre="linkedin_publicaciones_a.json")
        pendientes = self.cliente.get("/resultados/conteos").json()["pendientes_revisar"]
        if pendientes == 0:
            self.skipTest("el fixture no produjo items sin puntuar")
        cuerpo = self.cliente.get("/resultados", params={
            "tipo_resultado": "vacante", "solo_revisar": "true",
            "score_min": 20, "score_max": 100,
        }).json()
        self.assertEqual(cuerpo["total"], pendientes)
        self.assertTrue(all(item["score"] is None for item in cuerpo["items"]))

    def test_busqueda_escapa_comodines_de_like(self):
        self._sembrar([VACANTE])
        # "%" sin escapar hacia match con toda la tabla.
        self.assertEqual(self.cliente.get("/resultados", params={"busqueda": "100%"}).json()["total"], 0)
        self.assertEqual(self.cliente.get("/resultados", params={"busqueda": "a_me"}).json()["total"], 0)

    # --- aplicaciones -----------------------------------------------------

    def _payload(self):
        return {
            "dedupe_key": "clave-uno", "titulo": "Frontend", "empresa": "Acme",
            "descripcion": "React y TypeScript", "link": "https://example.com/j/1",
            "fuente": "prueba", "score": 80, "estado_inicial": "pendiente",
        }

    def test_guardar_y_duplicado_da_409(self):
        self.assertEqual(self.cliente.post("/aplicaciones", json=self._payload()).status_code, 201)
        # Repetir no debe dar 500 aunque el INSERT choque con la restriccion.
        self.assertEqual(self.cliente.post("/aplicaciones", json=self._payload()).status_code, 409)

    def test_descripcion_vacia_da_422(self):
        payload = {**self._payload(), "descripcion": ""}
        self.assertEqual(self.cliente.post("/aplicaciones", json=payload).status_code, 422)

    def test_estado_invalido_da_400_y_valido_registra_fecha(self):
        creada = self.cliente.post("/aplicaciones", json=self._payload()).json()
        self.assertEqual(self.cliente.put(
            f"/aplicaciones/{creada['id']}/estado", json={"estado": "inventado"}).status_code, 400)
        actualizada = self.cliente.put(
            f"/aplicaciones/{creada['id']}/estado", json={"estado": "aplicado"}).json()
        self.assertIsNotNone(actualizada["fecha_aplicacion"])

    def test_endpoints_de_aplicacion_inexistente_dan_404(self):
        self.assertEqual(self.cliente.get("/aplicaciones/9999").status_code, 404)
        self.assertEqual(self.cliente.delete("/aplicaciones/9999").status_code, 404)
        self.assertEqual(self.cliente.put(
            "/aplicaciones/9999/notas", json={"notas": "x"}).status_code, 404)

    def test_tracking_aparece_en_resultados(self):
        self._sembrar([VACANTE])
        item = self.cliente.get("/resultados", params={"tipo_resultado": "vacante"}).json()["items"][0]
        self.assertIsNone(item["tracking"])
        payload = {**self._payload(), "dedupe_key": item["dedupe_key"]}
        self.assertEqual(self.cliente.post("/aplicaciones", json=payload).status_code, 201)
        item = self.cliente.get("/resultados", params={"tipo_resultado": "vacante"}).json()["items"][0]
        self.assertEqual(item["tracking"]["estado"], "pendiente")


if __name__ == "__main__":
    unittest.main()
