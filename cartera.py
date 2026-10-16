"""Registro de CEDEARs confirmado por usuario; no calcula señales ni consulta precios."""
import argparse
import json
from decimal import Decimal
from pathlib import Path

REGISTRO = Path(__file__).with_name('cartera.json')


def cargar_cartera():
    return json.loads(REGISTRO.read_text(encoding='utf-8'))


def ars(valor):
    return f'{Decimal(valor):,.2f}'.translate(str.maketrans(',.', '.,'))


def lineas_cartera():
    cartera = cargar_cartera()
    lines = [f"Bull Market — {cartera['fuente']}. Importes en ARS por CEDEAR.",
             'MOMENTUM IA — POSICIONES ABIERTAS (no es el ranking calculado):']
    for p in cartera['momentum_abiertas']:
        provisional = ' PROVISIONAL' if p['ppc_provisional'] else ''
        lines.append(f"  {p['ticker']}: {p['cantidad']} CEDEARs; PPC{provisional} ${ars(p['ppc'])}.")
    lines.append('MOMENTUM IA — POSICIONES CERRADAS:')
    for p in cartera['momentum_cerradas']:
        lines.append(f"  {p['ticker']}: {p['cantidad_vendida']} CEDEARs vendidos a ${ars(p['precio_venta'])}.")
    lines.append('OTRAS TENENCIAS ACREDITADAS — abiertas, fuera de la cartera Top 3:')
    for p in cartera['otras_tenencias']:
        lines.append(f"  {p['ticker']}: {p['cantidad']} CEDEARs; no vendidos; PPC no informado.")
    lines.append('Sin fechas de operación ni comisiones informadas. Este registro no ejecuta órdenes ni modifica el ranking.')
    return lines


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', help='Guardar registro legible sin consultar cotizaciones')
    args = parser.parse_args()
    texto = '\n'.join(lineas_cartera()) + '\n'
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(texto, encoding='utf-8')
    print(texto, end='')
