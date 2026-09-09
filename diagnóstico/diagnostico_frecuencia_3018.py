#!/usr/bin/env python3
# =============================================================================
#  diagnostico_frecuencia_3018.py
#  Cuantas veces al dia pasa el autobus 3018 (el que conecta con Sencelles,
#  Costitx, Santa Eugenia)? Si son pocas expediciones y muy espaciadas,
#  confirma por que una ventana de calculo de 60 min puede dar medianas
#  muy altas aunque exista una conexion razonable si se coge el bus correcto.
#  USO:  python diagnostico_frecuencia_3018.py
# =============================================================================
import zipfile
from pathlib import Path

import pandas as pd

GTFS = Path("datos/tib_gtfs.zip")


def leer(z, nombre):
    with z.open(nombre) as f:
        return pd.read_csv(f, dtype=str, low_memory=False)


z = zipfile.ZipFile(GTFS)
routes = leer(z, "routes.txt")
trips = leer(z, "trips.txt")
stimes = leer(z, "stop_times.txt")
cal = leer(z, "calendar.txt")

for route_id in ("3018", "L034"):
    print(f"\n=========== RUTA {route_id} ===========")
    r = routes[routes["route_id"] == route_id]
    if r.empty:
        print("   No encuentro esta ruta en routes.txt")
        continue
    print(r[[c for c in ("route_id","route_short_name","route_long_name") if c in r.columns]].to_string(index=False))

    tr = trips[trips["route_id"] == route_id]
    print(f"   Expediciones (trips) totales en el GTFS: {len(tr)}")

    # cuantas de esas circulan un miercoles (mismo dia que usamos: 5 agosto 2026)
    activos_mie = cal[(cal["wednesday"] == "1")
                       & (cal["start_date"] <= "20260805")
                       & (cal["end_date"] >= "20260805")]["service_id"]
    tr_mie = tr[tr["service_id"].isin(activos_mie)]
    print(f"   Expediciones que circulan un miercoles: {len(tr_mie)}")

    st = stimes[stimes["trip_id"].isin(set(tr_mie["trip_id"]))].copy()
    if "departure_time" in st.columns and len(st):
        # tomamos, por cada trip, su primera hora de paso, para ver el patron horario
        primeras = st.sort_values("stop_sequence").groupby("trip_id")["departure_time"].first()
        horas = sorted(primeras.tolist())
        print(f"   Horas de paso (primera parada de cada expedicion), miercoles: {horas}")
    else:
        print("   No hay horarios que mostrar")

print("\nFIN. Pega esta salida completa.")
