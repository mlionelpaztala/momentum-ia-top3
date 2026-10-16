# Momentum IA Top 3

El ranking teórico y el registro de cartera son independientes. Tener o vender un CEDEAR no agrega, quita ni prioriza empresas en el ranking.

- `cartera.json`: fuente del registro de Bull Market confirmado por el usuario; cantidades de CEDEARs e importes unitarios en ARS. CEG tiene PPC provisional. META y GOOGL siguen acreditadas fuera de la cartera Momentum; no están vendidas. No se infieren fechas, comisiones ni PPC faltantes.
- `cartera.py`: muestra el registro sin Internet: `python cartera.py`. Para guardarlo: `python cartera.py --out resultados/cartera_confirmada.txt`.
- `ranking.py`: calcula el ranking y agrega al informe una sección separada con ese registro. Conserva las 57 empresas, retorno de 63 ruedas, SMA50 y siete cierres. Las tenencias no determinan el Top 3 calculado. El indicador histórico de CEDEAR previamente informado tampoco equivale a tenencia actual.

Validación sin cotizaciones reales: con pandas y numpy disponibles, ejecutar `python -m unittest -v`. El proveedor de precios se sustituye por datos sintéticos; no requiere yfinance instalado ni conexión a Yahoo. Comprueba cantidades y precios, PPC provisional, fórmula, SMA50, siete scores e independencia del ranking frente a cambios en la cartera.

`resultados/informe_resumen.txt` conserva la sección bursátil previamente guardada y actualiza solamente el registro de cartera; no se recalcularon ni verificaron sus cotizaciones. Los CSV existentes conservan su fecha original. Una ejecución normal requiere las dependencias de `requirements.txt` e Internet. GitHub Actions no se modifica.
