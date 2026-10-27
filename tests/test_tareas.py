# -*- coding: utf-8 -*-
"""Tareas periódicas en el worker (estándar H5.5, 25-oct-2026). Sin BD ni Telegram.

- correr_vencidas: cada tarea a su ritmo; el error de una no frena a las demás.
- arrancar: solo con FINSYS_WORKER_PRODUCCION=1 y `tareas` en FINSYS_EN_COLA.
- _ticks del poller (sin `tareas`): lo mismo que antes, al mismo ritmo.
- bot_sms: un SMS ya reservado por otro proceso se salta (nunca dos borradores).
- cola.purgar: borra solo lo terminado de más de N días y el archivo de pgmq.

    python -m unittest tests.test_tareas
"""
import os
import sys
import threading
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "fin_sys_core"))

import bot_telegram  # noqa: E402
from fin_sys_core import cola, tareas  # noqa: E402


class TestProgramador(unittest.TestCase):
    def test_cada_tarea_a_su_ritmo_y_errores_aislados(self):
        hechas = []
        lista = [tareas.Tarea("rapida", 5, lambda: hechas.append("rapida")),
                 tareas.Tarea("rota", 5, lambda: 1 / 0),
                 tareas.Tarea("lenta", 900, lambda: hechas.append("lenta"))]
        prox = {}
        self.assertEqual(tareas.correr_vencidas(prox, 100.0, lista), ["rapida", "rota", "lenta"])
        self.assertEqual(tareas.correr_vencidas(prox, 103.0, lista), [], "nada vencido aún")
        self.assertEqual(tareas.correr_vencidas(prox, 105.0, lista), ["rapida", "rota"])
        self.assertEqual(hechas, ["rapida", "lenta", "rapida"], "la rota no frena a las demás")

    def test_las_tareas_reales_y_sus_ritmos(self):
        ritmos = {t.nombre: t.cada_s for t in tareas.TAREAS}
        self.assertEqual(ritmos, {"sms": 5, "avisos_mini_app": 5, "resumen": 900, "retencion": 3600,
                                  "limpieza_cola": 3600, "fotos_saldo": 300, "descuadres": 86400})

    def test_arrancar_solo_en_produccion_y_con_la_variable(self):
        parar = threading.Event()
        with mock.patch.object(tareas, "bucle") as bucle:
            with mock.patch.dict(os.environ, {"FINSYS_WORKER_PRODUCCION": "", "FINSYS_EN_COLA": "tareas"}):
                self.assertIsNone(tareas.arrancar(parar), "un worker local jamás corre tareas reales")
            with mock.patch.dict(os.environ, {"FINSYS_WORKER_PRODUCCION": "1", "FINSYS_EN_COLA": "bot"}):
                self.assertIsNone(tareas.arrancar(parar))
            with mock.patch.dict(os.environ, {"FINSYS_WORKER_PRODUCCION": "1", "FINSYS_EN_COLA": "bot,tareas"}):
                hilo = tareas.arrancar(parar)
                hilo.join(timeout=2)
        bucle.assert_called_once()

    def test_activas_lee_la_misma_variable(self):
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "exportacion,tareas"}):
            self.assertTrue(tareas.activas())
        with mock.patch.dict(os.environ, {"FINSYS_EN_COLA": "exportacion"}):
            self.assertFalse(tareas.activas())


class TestTicksDelPoller(unittest.TestCase):
    """Sin `tareas`, el poller sigue corriendo lo mismo que antes de H5.5."""

    def test_mismo_ritmo_que_antes(self):
        driver = mock.Mock()
        driver.avisar_chat_pendientes.return_value = 0
        import bot_anomalias
        import bot_retencion
        import bot_sms
        import insight_engine
        with mock.patch.object(insight_engine, "tick_resumen_telegram", return_value=False) as resumen, \
             mock.patch.object(bot_sms, "procesar_pendientes", return_value=0) as sms, \
             mock.patch.object(bot_retencion, "purgar", return_value={}) as ret, \
             mock.patch.object(bot_anomalias, "purgar", return_value=0), \
             mock.patch.object(bot_telegram.time, "monotonic", side_effect=[100.0, 100.0, 100.0, 100.0, 101.0, 101.0]):
            t, p = bot_telegram._ticks(driver, 0.0, 0.0)
            self.assertEqual((t, p), (1000.0, 3700.0))
            bot_telegram._ticks(driver, t, p)
        self.assertEqual(resumen.call_count, 1, "el resumen no vuelve a correr al segundo")
        self.assertEqual(ret.call_count, 1)
        self.assertEqual(sms.call_count, 2, "los SMS corren en cada vuelta")
        self.assertEqual(driver.avisar_chat_pendientes.call_count, 2)


class _Cur:
    def __init__(self, reservable):
        self.reservable, self.sqls, self._fila = reservable, [], None

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        self._fila = (1,) if ("FOR UPDATE SKIP LOCKED" in sql and self.reservable) else None

    def fetchone(self):
        return self._fila


class TestReservaDelSms(unittest.TestCase):
    def test_sms_tomado_por_otro_proceso_se_salta(self):
        import bot_sms
        conn, cur = mock.Mock(), _Cur(reservable=False)
        fila = (7, '{"text": "Bancolombia: pagaste $1"}', 3, "c1", "e7")
        self.assertFalse(bot_sms._procesar_uno(conn, cur, fila, mock.Mock()))
        self.assertEqual(len(cur.sqls), 1, "ni siquiera mira el chat: no toca nada")
        self.assertIn("draft_id IS NULL", cur.sqls[0])
        conn.commit.assert_called_once()


class TestPurgaDeLaCola(unittest.TestCase):
    def test_borra_lo_terminado_y_el_archivo(self):
        cur = mock.MagicMock()
        cur.rowcount = 2
        conn = mock.Mock()
        conn.cursor.return_value.__enter__ = mock.Mock(return_value=cur)
        conn.cursor.return_value.__exit__ = mock.Mock(return_value=False)
        with mock.patch.object(cola, "get_conn", return_value=conn), mock.patch.object(cola, "put_conn"):
            r = cola.purgar(30, colas=("trabajos", "trabajos_prueba", "mala;DROP"))
        sqls = [c[0][0] for c in cur.execute.call_args_list]
        self.assertIn("estado IN ('HECHA', 'FALLIDA')", sqls[0], "lo que sigue en vuelo no se toca")
        self.assertEqual([s.split()[2] for s in sqls[1:]], ["pgmq.a_trabajos", "pgmq.a_trabajos_prueba"],
                         "un nombre raro de cola no llega al SQL")
        self.assertEqual(r, {"operaciones": 2, "archivo": 4})
        conn.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
