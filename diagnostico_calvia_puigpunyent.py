#!/usr/bin/env python3
# =============================================================================
#  diagnostico_calvia_puigpunyent.py
#  Por que Calvia y Puigpunyent, pegados a Palma, salen a mas de 120 min en
#  transporte publico? Mismo procedimiento que resolvio lo de Sencelles:
#  ventana amplia (4h) para ver el itinerario real y la frecuencia real.
#  Incluye Esporles como referencia (pueblo cercano, tambien en la sierra).
#  USO:  python diagnostico_calvia_puigpunyent.py
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
AUDIT = Path("auditoria_puntos.csv")

OBJETIVOS = ["Calvià", "Puigpunyent", "Esporles"]  # Esporles = referencia cercana


def main():
    from r5py import TransportNetwork, TransportMode, DetailedItineraries

    a = pd.read_csv(AUDIT)
    objetivo = a[a["name"].isin(OBJETIVOS)]
    if objetivo.empty:
        print("No encuentro esos nombres en auditoria_puntos.csv. Nombres disponibles:")
        print(a["name"].tolist())
        return
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

    print("Calculando itinerarios detallados (ventana de 4 horas)...")
    it = DetailedItineraries(
        red,
        origins=origen,
        destinations=destinos,
        departure=FECHA_HORA.to_pydatetime(),
        departure_time_window=datetime.timedelta(minutes=240),
        max_time=datetime.timedelta(minutes=240),
        max_time_walking=datetime.timedelta(minutes=20),
        speed_walking=4.5,
        transport_modes=[TransportMode.TRANSIT, TransportMode.WALK],
    )

    df = pd.DataFrame(it)
    if df.empty:
        print("\nNO SE ENCUENTRA NINGUN ITINERARIO en 4 horas para NINGUNO de estos destinos.")
        print("Eso ya es informacion real: no hay ningun autobus/tren que conecte el aeropuerto")
        print("con estos pueblos dentro de una ventana de 4 horas.")
        return

    for destino in OBJETIVOS:
        sub = df[df["to_id"] == destino]
        if sub.empty:
            print(f"\n=== {destino}: SIN ITINERARIO en 4 horas ===")
            continue
        totales = sub.groupby("option").apply(
            lambda g: g["travel_time"].sum() + g["wait_time"].sum()
        ).sort_values()
        mejor_opcion = totales.index[0]
        opt = sub[sub["option"] == mejor_opcion].sort_values("segment")
        total = totales.iloc[0]
        print(f"\n=== AEROPUERTO -> {destino} (mejor de {len(totales)} opciones en 4h) ===")
        print(f"    Tiempo total (viaje+espera): {total}")
        cols = ["segment", "transport_mode", "route_id", "agency_id",
                "start_stop_id", "end_stop_id", "travel_time", "wait_time"]
        cols = [c for c in cols if c in opt.columns]
        print(opt[cols].to_string(index=False))

    print("\nFIN. Pega esta salida completa.")


if __name__ == "__main__":
    main()
