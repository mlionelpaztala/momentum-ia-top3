# Backtest sin anticipación: requisitos para resultados válidos

El backtest_vigente.py actual **NO** es una prueba histórica libre de sesgo retrospectivo. No publicar su CAGR como retorno defendible.

## Datos necesarios

- Precios diarios OPEN/CLOSE consistentes por ticker, con series ajustadas y empresas retiradas de cotización.
- Universo histórico fechado, incluyendo altas, bajas, quiebras y cambios de ticker.
- Evidencia de procedencia y cobertura de datos de 2016 a 2026.
- Lista de elegibilidad IA definida con criterios observables entonces, no con empresas ganadoras de 2026.

## Reglas que deben conservarse

Score retorno 63 ruedas; Top 3 equiponderado; revisión cada 5 ruedas; sustitución al superar por >=5 puntos porcentuales durante 7 cierres consecutivos, con SMA50; sin stops ni caución. Ejecutar en apertura siguiente, con costos de comisión y deslizamiento.

**Bloqueo**: un dataset de constituyentes S&P 500 es un universo histórico real, pero **no** es el universo IA original. Yahoo Finance no garantiza cobertura histórica de delistings. Hasta obtener precios + elegibilidad íntegros, declarar resultados exploratorios, nunca validados.

Fuentes candidatas para membresía S&P 500 *como prueba proxy separada*: https://github.com/shardul0701/SP500-Survivorship-bias-data-2004-2026 ; precios incompletos y advertencias: https://github.com/Johnbrick123/sp500-data .


## Plan de ejecución (19-10-2026)

**Fase A — auditoría de cobertura (sin publicar rentabilidad)**

1. Congelar criterios **ex ante** de elegibilidad del ecosistema IA. No utilizar la lista actual de tickers como filtro histórico y no clasificar empresas a partir de su desempeño posterior. Guardar evidencia fechada.
2. Elaborar universo completo por fecha con altas/bajas, fusiones y exclusiones; registrar no solamente las supervivientes. Si un nombre salió, mantener su rentabilidad hasta salida, incluyendo precio terminal o delisting return.
3. Contratar/obtener precios diarios, eventos corporativos, OPEN y CLOSE de tickers activos y deslistados, junto con SPY/QQQ. Preferencia: fuente point-in-time con identificador persistente como CRSP; auditar huecos antes de cualquier cálculo.
4. Hacer un **proxy S&P 500 histórico separado** si los datos IA no están disponibles; jamás etiquetarlo como estrategia IA Top3. Comparar conjuntos de membresía de al menos dos fuentes.
5. Integrar backtest_sin_anticipacion.py en un workflow de entrada controlada, con ejecuciones de 5 y 10 años, señales de cierre y llenado en apertura siguiente. Pruebas unitarias de las siete ruedas, cinco ruedas, IPO y delisting.
6. Bloquear cualquier CAGR 'validado' si falta información, hay relleno hacia atrás, faltan tickers delistados, cambia el universo ex ante o no se puede reproducir el calendario.

Fuentes exploradas: https://github.com/shardul0701/SP500-Survivorship-bias-data-2004-2026 (membresía, S&P 500 solamente), https://github.com/coiltrade/point-in-time-sp500 (membresía, sin precios incluidos), https://www.crsp.org/research__trashed/crsp-us-stock-databases/ (datos activos e inactivos, acceso/licencia por verificar).

**Estado hoy:** fuente histórica completa para universo IA original NO disponible, validación pendiente. No hay estimación nueva de CAGR.
