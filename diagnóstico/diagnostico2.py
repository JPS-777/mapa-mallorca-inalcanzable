#!/usr/bin/env python3
# =============================================================================
#  diagnostico2.py
#  Dos preguntas muy concretas:
#   1) Existe la linea A1 (Aeroport - Placa d'Espanya) en el feed, y donde para?
#   2) El punto que usamos como "Palma" (auditoria_puntos.csv), esta cerca de
#      la estacion intermodal / Placa d'Espanya, o lejos?
#  Si (2) esta lejos, ESE es el motivo de que todo salga inflado: no es un
#  problema del transporte publico real, es que medimos mal el punto de Palma.
#  USO:  python diagnostico2.py
# =============================================================================

import math
import zipfile
from pathlib import Path

import pandas as pd

GTFS = Path("datos/tib_gtfs.zip")
AUDIT = Path("auditoria_puntos.csv")

# Estacio Intermodal / Placa d'Espanya (referencia real, verificable en Google Maps)
INTERMODAL = (39.5751, 2.6503)


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
routes = leer(z, "routes.txt")
trips = leer(z, "trips.txt")
stimes = leer(z, "stop_times.txt")
stops = leer(z, "stops.txt")
stops["stop_lat"] = stops["stop_lat"].astype(float)
stops["stop_lon"] = stops["stop_lon"].astype(float)

print("=========== 1. BUSCANDO LA LINEA A1 / PLACA D'ESPANYA ===========")
cols = [c for c in ("route_id", "route_short_name", "route_long_name") if c in routes.columns]
mask = pd.Series(False, index=routes.index)
for c in ("route_short_name", "route_long_name"):
    if c in routes.columns:
        mask |= routes[c].astype(str).str.contains("A1", case=False, na=False, regex=False)
        mask |= routes[c].astype(str).str.contains("Espanya", case=False, na=False)
        mask |= routes[c].astype(str).str.contains("Espa\u00f1a", case=False, na=False)
cand = routes[mask]
if len(cand):
    print(cand[cols].to_string(index=False))
else:
    print("   NO aparece ninguna ruta 'A1' ni 'Espanya' en routes.txt")
    print("   -> el bus urbano directo aeropuerto-centro puede no estar en este feed,")
    print("      o estar integrado dentro de una linea EMT con otro nombre.")

print("\nBuscando 'Espanya' / 'Intermodal' en los nombres de PARADAS:")
m2 = stops["stop_name"].astype(str).str.contains("Espanya", case=False, na=False) | \
     stops["stop_name"].astype(str).str.contains("Espa\u00f1a", case=False, na=False) | \
     stops["stop_name"].astype(str).str.contains("Intermodal", case=False, na=False)
cerca_hub = stops[m2][["stop_id", "stop_name", "stop_lat", "stop_lon"]]
print(cerca_hub.to_string(index=False) if len(cerca_hub) else "   (ninguna)")

print("\n=========== 2. DONDE HEMOS PUESTO EL PUNTO 'PALMA'? ===========")
if AUDIT.exists():
    a = pd.read_csv(AUDIT)
    fila = a[a["name"] == "Palma"]
    if len(fila):
        f = fila.iloc[0]
        print(f"   Punto elegido: {f['osm_name']}  (metodo: {f['metodo']})")
        print(f"   Coordenadas:   {f['lat']}, {f['lon']}")
        d = dist_km(f["lat"], f["lon"], INTERMODAL[0], INTERMODAL[1])
        print(f"   Distancia a la Estacio Intermodal / Placa d'Espanya: {d:.2f} km")
        if d > 1.5:
            print("   -> LEJOS. Es muy probable que ESTE sea el problema:")
            print("      medimos el tiempo hasta un punto de Palma alejado del")
            print("      nodo de transporte real, no un problema del transporte publico.")
        else:
            print("   -> Cerca, esto no explicaria el problema por si solo.")
    else:
        print("   No encuentro la fila 'Palma' en auditoria_puntos.csv")
else:
    print("   No existe auditoria_puntos.csv todavia (ejecuta antes calcular_tiempos.py)")

print("\n=========== 3. FRECUENCIA REAL AEROPUERTO -> PRIMERA PARADA UTIL ===========")
ids_ap = set(stops[stops["stop_name"].str.contains("Aeroport", case=False, na=False)]["stop_id"])
sel = stimes[stimes["stop_id"].isin(ids_ap)].copy()
if len(sel):
    sel["dep"] = sel["departure_time"]
    print(f"   Expediciones que salen del aeropuerto (todo el dia, todas lineas): {len(sel)}")
    print("   Primeras salidas registradas:", sorted(sel['dep'].dropna().unique())[:10])
else:
    print("   No hay stop_times para paradas 'Aeroport'")

print("\nFIN. Pega esta salida completa.")
