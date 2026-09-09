#!/usr/bin/env python3
# =============================================================================
#  calcular_tiempos.py   ·   v5
#  Proyecto BALEARES (ANEVAL/BALEVAL) - LLYC
#
#  CAMBIO RESPECTO A v4 (diagnosticado con diagnostico_pla_mallorca.py y
#  diagnostico_frecuencia_3018.py)
#
#  5) VENTANA DE MUESTREO AMPLIADA DE 60 A 120 MINUTOS.
#     Se detecto que Santa Eugenia, Sencelles y Costitx salian por encima de
#     120 min en transporte publico, cuando una prueba con ventana amplia (4h)
#     mostraba un itinerario real de 76-99 min. La causa: la linea 304
#     (Inca-Sencelles-Palma, route_id 3018) tiene huecos reales de hasta
#     90 minutos entre expediciones (verificado leyendo el GTFS: salidas a
#     las 09:25 y luego nada hasta las 10:55 un miercoles cualquiera). Con una
#     ventana de muestreo de solo 60 minutos, una parte relevante de las
#     salidas simuladas caen justo en ese hueco, inflando la MEDIANA muy por
#     encima del itinerario real que obtendria un viajero que coge el bus
#     correcto.
#
#     Esto NO es un problema de estos 3 municipios en particular: es un
#     limite metodologico de la ventana de muestreo frente a lineas de baja
#     frecuencia. Por eso la correccion se aplica de forma UNIFORME a los
#     53 municipios (ampliar la ventana), no solo a los que "salian mal".
#     Los municipios con lineas frecuentes (cada 12-20 min, como los
#     corredores principales) apenas cambiaran: una ventana de 60 min ya
#     capturaba varios ciclos de servicio real. Los municipios con lineas
#     poco frecuentes pasaran a tener una mediana mas estable y representativa.
#
#     Se documenta el cambio explicitamente en el fichero de salida
#     (tiempos_reales.json / meta / ventana_min) para que sea auditable.
#
#  USO:  python calcular_tiempos.py
# =============================================================================

import datetime
import json
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

DATOS = Path("datos")
GTFS_INTERURBANO = DATOS / "tib_gtfs.zip"
GTFS_EMT = DATOS / "emt_palma_gtfs.zip"
OSM = DATOS / "mallorca.osm.pbf"
GEOJSON = DATOS / "mallorca.geojson"
SALIDA = Path("tiempos_reales.json")
AUDITORIA = Path("auditoria_puntos.csv")

# Aeropuerto de Palma - Son Sant Joan, terminal de pasajeros
# Verificado: 39 33'06" N, 2 44'20" E
ORIGEN = (39.551667, 2.738889)

# Miercoles 5 de agosto de 2026, media manana.
# Dentro del calendario del GTFS del TIB (27/03/2026 - 31/10/2026).
FECHA_HORA = pd.Timestamp("2026-08-05 10:00:00")

# v5: ampliada de 60 a 120 min (ver nota arriba). Es un cambio metodologico
# deliberado y documentado, aplicado a los 53 municipios por igual.
VENTANA_MIN = 120
MAX_VIAJE_MIN = 240
MAX_CAMINATA_MIN = 20
VELOCIDAD_ANDANDO = 4.5


def norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    for a in ("sa ", "ses ", "es ", "el ", "la ", "s'", "l'"):
        if s.startswith(a):
            s = s[len(a):]
    return " ".join(s.replace("-", " ").replace(",", " ").split())


def comprobar():
    faltan = [str(p) for p in (GTFS_INTERURBANO, OSM, GEOJSON) if not p.exists()]
    if faltan:
        print("ERROR: faltan ficheros:")
        for f in faltan:
            print("   -", f)
        sys.exit(1)
    if not GTFS_EMT.exists():
        print("=" * 70)
        print("AVISO: no encuentro datos/emt_palma_gtfs.zip")
        print("Sin la red urbana de Palma los tiempos hacia el interior salen inflados.")
        print("=" * 70)
        resp = input("Continuar solo con el interurbano de todas formas? [s/N]: ")
        if resp.strip().lower() != "s":
            sys.exit(1)


def gtfs_feeds():
    feeds = [str(GTFS_INTERURBANO)]
    if GTFS_EMT.exists():
        feeds.append(str(GTFS_EMT))
        print("Usando 2 feeds GTFS: interurbano (TIB) + urbano (EMT Palma)")
    else:
        print("Usando 1 feed GTFS: solo interurbano (TIB) -- INCOMPLETO, ver aviso")
    return feeds


def leer_nucleos(pbf):
    import osmium

    class Places(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.rows = []

        def node(self, n):
            p = n.tags.get("place")
            if p in ("city", "town", "village"):
                nom = n.tags.get("name")
                if not nom:
                    return
                pop = n.tags.get("population")
                try:
                    pop = int(str(pop).replace(".", "").replace(" ", ""))
                except (TypeError, ValueError):
                    pop = 0
                self.rows.append({
                    "osm_name": nom, "place": p, "population": pop,
                    "lon": n.location.lon, "lat": n.location.lat,
                })

    h = Places()
    h.apply_file(str(pbf))
    df = pd.DataFrame(h.rows)
    if df.empty:
        print("ERROR: no encontre nucleos de poblacion en el .pbf")
        sys.exit(1)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    print(f"Nucleos de poblacion encontrados en OSM: {len(gdf)}")
    return gdf


def elegir_destinos(municipios, nucleos):
    dentro = gpd.sjoin(nucleos, municipios[["name", "geometry"]],
                       how="inner", predicate="within")
    filas = []
    for _, mun in municipios.iterrows():
        nom = mun["name"]
        cands = dentro[dentro["name"] == nom]
        metodo, elegido = None, None

        if len(cands):
            nn = norm(nom)
            exact = cands[cands["osm_name"].map(lambda x: norm(x) == nn)]
            if len(exact) == 0:
                exact = cands[cands["osm_name"].map(
                    lambda x: nn in norm(x) or norm(x) in nn)]
            if len(exact):
                elegido = exact.sort_values("population", ascending=False).iloc[0]
                metodo = "nucleo OSM (nombre coincide)"
            else:
                cp = cands.sort_values("population", ascending=False)
                if cp.iloc[0]["population"] > 0:
                    elegido = cp.iloc[0]
                    metodo = "nucleo OSM (mas poblado del municipio)"
                else:
                    orden = {"city": 0, "town": 1, "village": 2}
                    cands = cands.assign(_o=cands["place"].map(orden))
                    elegido = cands.sort_values("_o").iloc[0]
                    metodo = "nucleo OSM (mayor rango)"

        if elegido is None:
            pt = mun.geometry.representative_point()
            filas.append({"id": nom, "name": nom, "lon": pt.x, "lat": pt.y,
                          "metodo": "SIN NUCLEO OSM - centro geometrico",
                          "osm_name": "", "population": 0})
        else:
            filas.append({"id": nom, "name": nom,
                          "lon": elegido.geometry.x, "lat": elegido.geometry.y,
                          "metodo": metodo, "osm_name": elegido["osm_name"],
                          "population": int(elegido["population"])})

    df = pd.DataFrame(filas)
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs="EPSG:4326")
    df.to_csv(AUDITORIA, index=False, encoding="utf-8")
    sin = (df["metodo"].str.startswith("SIN NUCLEO")).sum()
    print(f"Destinos resueltos: {len(df)}  (sin nucleo OSM: {sin})")
    return gdf[["id", "name", "geometry"]]


def matriz(red, origen, destinos, modos, andando):
    from r5py import TravelTimeMatrix
    kw = dict(
        origins=origen, destinations=destinos,
        departure=FECHA_HORA.to_pydatetime(),
        departure_time_window=datetime.timedelta(minutes=VENTANA_MIN),
        max_time=datetime.timedelta(minutes=MAX_VIAJE_MIN),
        transport_modes=modos, percentiles=[50], snap_to_network=True,
    )
    if andando:
        kw["max_time_walking"] = datetime.timedelta(minutes=MAX_CAMINATA_MIN)
        kw["speed_walking"] = VELOCIDAD_ANDANDO
    return TravelTimeMatrix(red, **kw)


def col_t(df):
    for c in ("travel_time", "travel_time_p50"):
        if c in df.columns:
            return c
    raise RuntimeError(f"Columnas inesperadas: {list(df.columns)}")


def main():
    comprobar()
    from r5py import TransportNetwork, TransportMode

    municipios = gpd.read_file(GEOJSON).to_crs("EPSG:4326")
    nucleos = leer_nucleos(OSM)
    destinos = elegir_destinos(municipios, nucleos)

    print("Construyendo la red (GTFS + OSM)...")
    red = TransportNetwork(str(OSM), gtfs_feeds())

    origen = gpd.GeoDataFrame({"id": ["aeropuerto"]},
                              geometry=[Point(ORIGEN[1], ORIGEN[0])],
                              crs="EPSG:4326")

    print(f"Calculando transporte publico (ventana de muestreo: {VENTANA_MIN} min)...")
    tp_df = matriz(red, origen, destinos,
                   [TransportMode.TRANSIT, TransportMode.WALK], True)
    print("Calculando coche...")
    car_df = matriz(red, origen, destinos,
                    [TransportMode.CAR], False)

    tp = tp_df.set_index("to_id")[col_t(tp_df)].to_dict()
    car = car_df.set_index("to_id")[col_t(car_df)].to_dict()

    munis, sin_serv = {}, []
    for nom in destinos["id"]:
        t, c = tp.get(nom), car.get(nom)
        t = 999 if t is None or pd.isna(t) else int(round(float(t)))
        c = 999 if c is None or pd.isna(c) else int(round(float(c)))
        if t == 999:
            sin_serv.append(nom)
        munis[nom] = [t, c]

    salida = {
        "meta": {
            "fuente": "GTFS oficial TIB" + (" + EMT Palma" if GTFS_EMT.exists() else " (SOLO interurbano, incompleto)")
                      + " (CC-BY 4.0) + OpenStreetMap, motor R5 via r5py",
            "origen": "Aeropuerto de Palma (Son Sant Joan), 39.551667 / 2.738889",
            "momento": str(FECHA_HORA) + " (miercoles, temporada alta)",
            "ventana_min": VENTANA_MIN,
            "ventana_min_nota": "Ampliada de 60 a 120 min en v5: una ventana de 60 min resultaba "
                                 "inestable frente a lineas de baja frecuencia con huecos de hasta "
                                 "90 min (ej. linea 304 Inca-Sencelles-Palma). Cambio aplicado por "
                                 "igual a los 53 municipios.",
            "percentil": "mediana (p50) de la ventana de salida",
            "max_caminata_min": MAX_CAMINATA_MIN,
            "velocidad_andando_kmh": VELOCIDAD_ANDANDO,
            "destino_por_municipio": "nucleo urbano real (nodo place de OpenStreetMap); ver auditoria_puntos.csv",
            "nota_999": "999 = no alcanzable dentro de los limites de busqueda",
            "municipios_sin_servicio": sin_serv,
            "red_urbana_palma_incluida": GTFS_EMT.exists(),
        },
        "municipios": munis,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")

    a60 = sum(1 for v in munis.values() if v[0] <= 60)
    a90 = sum(1 for v in munis.values() if v[0] <= 90)
    a120 = sum(1 for v in munis.values() if v[0] <= 120)
    c90 = sum(1 for v in munis.values() if v[1] <= 90)

    print("\n=========== RESULTADO REAL (v5, ventana 120 min) ===========")
    print(f"Red urbana de Palma incluida:     {'SI' if GTFS_EMT.exists() else 'NO -- resultado incompleto'}")
    print(f"Municipios analizados:            {len(munis)}")
    print(f"TP    <= 60 min:                  {a60}")
    print(f"TP    <= 90 min:                  {a90}")
    print(f"TP    <= 120 min:                 {a120}")
    print(f"COCHE <= 90 min:                  {c90}")
    print(f"Sin servicio publico alguno:      {len(sin_serv)}")
    if sin_serv:
        print("   -> " + ", ".join(sin_serv))

    print("\n--- CONTROL DE CORDURA (control historico + los 3 nuevos) ---")
    for x in ("Inca", "Manacor", "Binissalem", "Sóller", "Palma", "Llucmajor",
              "Santa Eugènia", "Sencelles", "Costitx", "Sineu"):
        if x in munis:
            t, c = munis[x]
            print(f"   {x:<16} TP {'sin servicio' if t==999 else str(t)+' min':<14} coche {c} min")

    print(f"\nEscrito: {SALIDA}")
    print(f"Auditoria de puntos: {AUDITORIA}")
    print("Ahora ejecuta:  python aplicar_correcciones.py  (si aun no lo has hecho con este dataset)")
    print("Y despues:      node build_map.js")


if __name__ == "__main__":
    main()
