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
