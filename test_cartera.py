"""Validación offline: python -m unittest -v. Nunca consulta Yahoo."""
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

# Sustituye el proveedor antes de importar ranking, incluso sin yfinance instalado.
sys.modules['yfinance'] = types.SimpleNamespace(download=None)
import ranking
import cartera


def precios(tickers, **kwargs):
    dates = pd.bdate_range('2025-01-02', periods=100)
    return pd.concat({t: pd.DataFrame({'Close': 100 + np.arange(100) * (ranking.UNIVERSE.index(t) + 1 if t in ranking.UNIVERSE else 1)}, index=dates) for t in tickers}, axis=1)


class CarteraTest(unittest.TestCase):
    def test_confirmaciones(self):
        c = cartera.cargar_cartera()
        self.assertEqual([(p['ticker'], p['cantidad'], p['ppc'], p['ppc_provisional']) for p in c['momentum_abiertas']], [('PLTR',18,'105750.00',False),('MRVL',73,'27080.00',False),('CEG',224,'10675.04',True)])
        self.assertEqual(c['momentum_cerradas'], [{'ticker':'ANET','cantidad_vendida':200,'precio_venta':'9985.00'},{'ticker':'DELL','cantidad_vendida':187,'precio_venta':'9935.00'}])
        self.assertEqual(c['otras_tenencias'], [{'ticker':'META','cantidad':371},{'ticker':'GOOGL','cantidad':1028}])
        self.assertIn('PPC PROVISIONAL $10.675,04', '\n'.join(cartera.lineas_cartera()))

    def test_ranking_independiente_y_formula(self):
        self.assertEqual(len(set(ranking.UNIVERSE)),57)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            with patch.object(ranking.yf, 'download', side_effect=precios), contextlib.redirect_stdout(io.StringIO()):
                ranking.calc(a, end='2025-05-21')
                with patch.object(cartera, 'cargar_cartera', return_value={'fuente':'prueba','momentum_abiertas':[], 'momentum_cerradas':[], 'otras_tenencias':[]}):
                    ranking.calc(b, end='2025-05-21')
            for name in ['ranking_teorico_63_ruedas.csv','cedears_previamente_informados.csv','benchmarks.csv','sin_datos.csv']:
                self.assertEqual((Path(a)/name).read_bytes(), (Path(b)/name).read_bytes())
            df = pd.read_csv(Path(a)/'ranking_teorico_63_ruedas.csv').set_index('ticker')
            row = df.loc['ANET']
            self.assertAlmostEqual(row.score_63_pct, round(100*(199/136-1),4))
            self.assertAlmostEqual(row.sma50_usd_aj,174.5)
            self.assertTrue(row.sobre_sma50)
            for j in range(7):
                self.assertAlmostEqual(row[f'score_t_menos_{j}_pct'],round(100*((199-j)/(136-j)-1),4))
            text = (Path(a)/'informe_resumen.txt').read_text()
            self.assertIn('ANET: 200 CEDEARs vendidos',text)
            self.assertNotIn('Stops ARS iniciales',text)
            self.assertIn('META: 371 CEDEARs; no vendidos',text)


if __name__ == '__main__':
    unittest.main()
