#!/usr/bin/env python3
# =============================================================================
#  diagnostico.py
#  Mira QUE contiene realmente el GTFS antes de fiarnos de ningun numero.
#  No calcula rutas: solo lee el fichero. Tarda segundos.
#  USO:  python diagnostico.py
# =============================================================================

import math
import zipfile
from pathlib import Path

import pandas as pd

GTFS = Path("datos/tib_gtfs.zip")
AEROPUERTO = (39.551667, 2.738889)


def leer(z, nombre):
    try:
        with z.open(nombre) as f:
            return pd.read_csv(f, dtype=str, low_memory=False)
    except KeyError:
        return None


def dist_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


z = zipfile.ZipFile(GTFS)
print("FICHEROS EN EL GTFS:")
for n in sorted(z.namelist()):
    print("   ", n)

# ---------------------------------------------------------------- 1. agencias
print("\n=========== 1. OPERADORES INCLUIDOS ===========")
ag = leer(z, "agency.txt")
if ag is None:
    print("   (no hay agency.txt)")
else:
    cols = [c for c in ("agency_id", "agency_name", "agency_url") if c in ag.columns]
    print(ag[cols].to_string(index=False))
    print(f"\n   Total operadores: {len(ag)}")
    nombres = " ".join(ag.get("agency_name", pd.Series([], dtype=str)).astype(str)).upper()
    print("   Menciona EMT (bus urbano de Palma)? ->",
          "SI" if "EMT" in nombres else "NO  <-- OJO")
    print("   Menciona SFM / tren?                ->",
          "SI" if ("SFM" in nombres or "FERROCARRIL" in nombres or "TREN" in nombres) else "NO  <-- OJO")

# ---------------------------------------------------------------- 2. rutas
print("\n=========== 2. RUTAS ===========")
rt = leer(z, "routes.txt")
if rt is not None:
    print(f"   Total rutas: {len(rt)}")
    if "route_type" in rt.columns:
        tipos = {"0": "tranvia", "1": "metro", "2": "TREN", "3": "AUTOBUS",
                 "4": "ferry", "5": "cable", "6": "telecabina", "7": "funicular"}
        vc = rt["route_type"].value_counts()
        for k, v in vc.items():
            print(f"      tipo {k} ({tipos.get(str(k),'?')}): {v} rutas")
    if "agency_id" in rt.columns and ag is not None and "agency_id" in ag.columns:
        m = rt.merge(ag[["agency_id", "agency_name"]], on="agency_id", how="left")
        print("\n   Rutas por operador:")
        print(m["agency_name"].value_counts().to_string())

# ---------------------------------------------------------------- 3. paradas
print("\n=========== 3. PARADAS CERCA DEL AEROPUERTO ===========")
st = leer(z, "stops.txt")
st["stop_lat"] = st["stop_lat"].astype(float)
st["stop_lon"] = st["stop_lon"].astype(float)
st["km"] = st.apply(
    lambda r: dist_km(AEROPUERTO[0], AEROPUERTO[1], r["stop_lat"], r["stop_lon"]), axis=1
)
cerca = st.nsmallest(8, "km")[["stop_id", "stop_name", "km"]]
cerca["km"] = cerca["km"].round(3)
print(cerca.to_string(index=False))
mas_cerca = cerca.iloc[0]["km"]
print(f"\n   Parada mas cercana: {mas_cerca} km",
      "-> OK, se llega andando" if mas_cerca < 1.0 else "-> LEJOS, sospechoso")

# ------------------------------------------------- 4. que sale del aeropuerto
print("\n=========== 4. QUE LINEAS PARAN EN EL AEROPUERTO ===========")
ids = set(st[st["km"] < 1.0]["stop_id"])
if not ids:
    print("   NINGUNA parada a menos de 1 km. Esto explicaria todo.")
else:
    stimes = leer(z, "stop_times.txt")
    trips = leer(z, "trips.txt")
    sel = stimes[stimes["stop_id"].isin(ids)]
    tr = trips[trips["trip_id"].isin(set(sel["trip_id"]))]
    if rt is not None:
        rr = rt[rt["route_id"].isin(set(tr["route_id"]))]
        cols = [c for c in ("route_id", "route_short_name", "route_long_name") if c in rr.columns]
        print(f"   Lineas que paran junto al aeropuerto: {len(rr)}")
        print(rr[cols].head(25).to_string(index=False))
        print(f"\n   Expediciones totales que pasan: {len(tr)}")

# ---------------------------------------------------------------- 5. calendario
print("\n=========== 5. SERVICIO EL 5 AGOSTO 2026 (miercoles) ===========")
cal = leer(z, "calendar.txt")
if cal is not None:
    activos = cal[(cal["wednesday"] == "1")
                  & (cal["start_date"] <= "20260805")
                  & (cal["end_date"] >= "20260805")]
    print(f"   Servicios activos ese miercoles: {len(activos)} de {len(cal)}")
cd = leer(z, "calendar_dates.txt")
if cd is not None:
    ex = cd[cd["date"] == "20260805"]
    print(f"   Excepciones para esa fecha en calendar_dates: {len(ex)}")
    if len(ex):
        print(ex["exception_type"].value_counts().to_string())
        print("   (2 = servicio SUPRIMIDO ese dia)")
else:
    print("   (no hay calendar_dates.txt)")

print("\nFIN. Pega esta salida completa.")
