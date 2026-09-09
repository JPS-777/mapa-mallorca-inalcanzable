#!/usr/bin/env python3
# =============================================================================
#  diagnostico_itinerario.py
#  No nos fiamos del numero final: pedimos el itinerario PASO A PASO que ha
#  escogido el motor para el aeropuerto -> Binissalem e Inca, para ver si usa
#  el tren real o se lia con una ruta rara. Esto es lo que explica por que
#  Binissalem (mas cerca en la misma linea) sale mas lento que Inca.
#  USO:  python diagnostico_itinerario.py
# =============================================================================

import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

DATOS = Path("datos")
GTFS_INTERURBANO = DATOS / "tib_gtfs.zip"
GTFS_EMT = DATOS / "emt_palma_gtfs.zip"
OSM = DATOS / "mallorca.osm.pbf"

ORIGEN = (39.551667, 2.738889)
FECHA_HORA = pd.Timestamp("2026-08-05 10:00:00")

# los mismos puntos de destino que uso calcular_tiempos.py, leidos de la
# auditoria para no reinventar nada
AUDIT = Path("auditoria_puntos.csv")


def main():
    from r5py import TransportNetwork, TransportMode, DetailedItineraries

    a = pd.read_csv(AUDIT)
    objetivo = a[a["name"].isin(["Inca", "Binissalem", "Manacor", "Palma"])]
    print("Puntos usados (de auditoria_puntos.csv):")
    print(objetivo[["name", "osm_name", "lat", "lon"]].to_string(index=False))

    destinos = gpd.GeoDataFrame(
        {"id": objetivo["name"]},
        geometry=gpd.points_from_xy(objetivo["lon"], objetivo["lat"]),
        crs="EPSG:4326",
    )
    origen = gpd.GeoDataFrame(
        {"id": ["aeropuerto"]},
        geometry=[Point(ORIGEN[1], ORIGEN[0])],
        crs="EPSG:4326",
    )

    print("\nConstruyendo la red...")
    feeds = [str(GTFS_INTERURBANO)]
    if GTFS_EMT.exists():
        feeds.append(str(GTFS_EMT))
    red = TransportNetwork(str(OSM), feeds)

    print("Calculando itinerarios detallados (puede tardar un poco mas)...")
    it = DetailedItineraries(
        red,
        origins=origen,
        destinations=destinos,
        departure=FECHA_HORA.to_pydatetime(),
        departure_time_window=datetime.timedelta(minutes=60),
        max_time=datetime.timedelta(minutes=240),
        max_time_walking=datetime.timedelta(minutes=20),
        speed_walking=4.5,
        transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
    )

    df = pd.DataFrame(it)
    if df.empty:
        print("No se ha encontrado ningun itinerario (raro). Revisar.")
        return

    for destino in objetivo["name"]:
        sub = df[df["to_id"] == destino]
        if sub.empty:
            print(f"\n=== {destino}: sin itinerario encontrado ===")
            continue
        # IMPORTANTE: el indice de 'option' NO indica cual es la mas rapida.
        # Elegimos la opcion cuyo tiempo TOTAL (suma de tramos) sea menor,
        # que es el criterio correcto (y descarta el "ir andando todo el
        # camino" que a veces aparece como opcion de reserva).
        totales = sub.groupby("option")["travel_time"].sum().sort_values()
        mejor_opcion = totales.index[0]
        opt = sub[sub["option"] == mejor_opcion].sort_values("segment")
        total_viaje = opt["travel_time"].sum()
        total_espera = opt["wait_time"].sum() if "wait_time" in opt.columns else "?"
        print(f"\n=== AEROPUERTO -> {destino} ===")
        print(f"    Opciones encontradas: {sorted(totales.index.tolist())}  (tiempos totales: {[str(t) for t in totales.values]})")
        print(f"    Opcion elegida: {mejor_opcion}  |  viaje total {total_viaje}  |  espera total {total_espera}")
        cols = ["segment", "transport_mode", "route_id", "agency_id",
                "start_stop_id", "end_stop_id", "travel_time", "wait_time"]
        cols = [c for c in cols if c in opt.columns]
        print(opt[cols].to_string(index=False))

    print("\nFIN. Pega esta salida completa (o al menos Inca y Binissalem).")


if __name__ == "__main__":
    main()
