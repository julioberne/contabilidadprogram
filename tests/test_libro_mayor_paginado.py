# -*- coding: utf-8 -*-
"""Libro mayor por páginas (estándar H6.3, 27-oct-2026). SOLO LECTURA contra la BD
(se salta sin DB_HOST): juntando las páginas sale exactamente el mayor completo
(mismos movimientos, mismo saldo acumulado) y los totales son los del período.

    python -m unittest tests.test_libro_mayor_paginado
"""
import os
import sys
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import tests  # noqa: F401,E402


@unittest.skipUnless(os.environ.get("DB_HOST"), "requiere BD")
class TestPaginasIgualAlCompleto(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fin_sys_core.db_pool import get_conn, put_conn
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""SELECT portfolio_id, cuenta_codigo, COUNT(*) FROM kernel_journal_entries
                            GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 1""")
            fila = cur.fetchone()
        finally:
            put_conn(conn)
        if not fila or fila[2] < 3:
            raise unittest.SkipTest("ninguna cuenta con al menos 3 movimientos")
        cls.pid, cls.cuenta = fila[0], fila[1]

    def _comparar(self, desde=None):
        from kernel import kernel_reports as rep
        completo = rep.libro_mayor(self.pid, self.cuenta, desde)
        movs, despues, paginas = [], None, 0
        while True:
            pag = rep.libro_mayor(self.pid, self.cuenta, desde, limite=2, despues=despues)
            paginas += 1
            self.assertEqual((pag["total_debito"], pag["total_credito"], pag["saldo_final"]),
                             (completo["total_debito"], completo["total_credito"], completo["saldo_final"]))
            self.assertEqual(pag["total_movimientos"], len(completo["movimientos"]))
            movs += pag["movimientos"]
            if not pag["siguiente"]:
                break
            despues = (pag["siguiente"]["fecha"], pag["siguiente"]["id"])
        self.assertEqual(movs, completo["movimientos"], "mismos movimientos y mismo saldo acumulado")
        self.assertGreater(paginas, 1)

    def test_sin_desde(self):
        self._comparar()

    def test_con_desde(self):
        from kernel import kernel_reports as rep
        todo = rep.libro_mayor(self.pid, self.cuenta)["movimientos"]
        self._comparar(desde=todo[len(todo) // 2]["fecha"])


if __name__ == "__main__":
    unittest.main()
