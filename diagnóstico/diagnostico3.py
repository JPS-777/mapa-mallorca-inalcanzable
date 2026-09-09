#!/usr/bin/env python3
# =============================================================================
#  diagnostico3.py
#  Pregunta muy concreta: EMT aparece en agency.txt, pero TIENE VIAJES REALES
#  (trips.txt / stop_times.txt) en este fichero, o solo esta listada de nombre?
#  USO:  python diagnostico3.py
# =============================================================================

import zipfile
from pathlib import Path

import pandas as pd

GTFS = Path("datos/tib_gtfs.zip")


def leer(z, nombre):
    try:
        with z.open(nombre) as f:
            return pd.read_csv(f, dtype=str, low_memory=False)
    except KeyError:
        return None


z = zipfile.ZipFile(GTFS)
ag = leer(z, "agency.txt")
routes = leer(z, "routes.txt")
trips = leer(z, "trips.txt")

emt_id = ag[ag["agency_name"].str.upper() == "EMT"]["agency_id"].iloc[0]
print(f"agency_id de EMT: {emt_id!r}")

print("\n=========== RUTAS con agency_id de EMT ===========")
if "agency_id" in routes.columns:
    r_emt = routes[routes["agency_id"] == emt_id]
    print(f"   Rutas de EMT en routes.txt: {len(r_emt)}")
    if len(r_emt):
        cols = [c for c in ("route_id", "route_short_name", "route_long_name") if c in r_emt.columns]
        print(r_emt[cols].to_string(index=False))
else:
    print("   routes.txt no tiene columna agency_id")

print("\n=========== VIAJES (trips) de esas rutas ===========")
if "agency_id" in routes.columns and len(r_emt):
    ids_rutas_emt = set(r_emt["route_id"])
    t_emt = trips[trips["route_id"].isin(ids_rutas_emt)]
    print(f"   Expediciones (trips) de EMT en trips.txt: {len(t_emt)}")
else:
    print("   (no hay rutas EMT que comprobar)")

print("\n=========== TODAS las rutas, agrupadas por agencia (verificacion cruzada) ===========")
if "agency_id" in routes.columns:
    print(routes.groupby("agency_id").size().to_string())

print("\nCONCLUSION:")
if "agency_id" in routes.columns and len(r_emt) == 0:
    print("   EMT esta en agency.txt pero NO tiene ninguna ruta propia en este feed.")
    print("   Es decir: este GTFS es SOLO la red interurbana (TIB/CTM).")
    print("   Los autobuses urbanos de Palma (incluida la linea A1 aeropuerto-centro)")
    print("   NO estan incluidos, aunque EMT aparezca nombrada.")
    print("   -> Hace falta el GTFS propio de EMT Palma como fichero adicional.")
elif "agency_id" in routes.columns and len(t_emt) == 0:
    print("   EMT tiene rutas nombradas pero SIN viajes (trips) reales.")
    print("   Mismo diagnostico: faltan los datos operativos de EMT.")
else:
    print("   EMT SI tiene viajes reales en este feed. Revisar por que A1 no")
    print("   aparecio en la busqueda anterior (puede llamarse distinto).")

print("\nFIN. Pega esta salida completa.")
