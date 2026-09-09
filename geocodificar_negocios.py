#!/usr/bin/env python3
# =============================================================================
#  geocodificar_negocios.py   ·   v4
#  Proyecto BALEARES (ANEVAL/BALEVAL) - LLYC
#
#  CAMBIO RESPECTO A v3 (diagnosticado con diagnostico_nominatim_raw.py)
#
#  4) LA BUSQUEDA ESTRUCTURADA (city=) NO DEBE RECHAZAR class=boundary.
#     Comprobado con la respuesta CRUDA de Nominatim: al pedir city=Santanyí
#     o city=Manacor, Nominatim devuelve correctamente el municipio, pero
#     clasificado como class=boundary/type=administrative (es como
#     representa un poligono de poblacion). v3 rechazaba "boundary" tambien
#     en este metodo por precaucion, lo cual descartaba la respuesta BUENA
#     y mandaba a "sin geocodificar" pueblos tan conocidos como Santanyí o
#     Manacor. Ahora el metodo estructurado solo rechaza calle/torrente/via
#     (highway/waterway/railway), nunca boundary/administrative.
#
#  CAMBIOS DE v3 (los tres fallos que aparecieron al probarlo)
#
#  1) VIEWBOX REAL DE MALLORCA + bounded=1.
#     "Sa Carrotja" y "Restaurant Alma" geocodificaron en MENORCA (a mas de
#     100 km). Se calcula el bounding box REAL a partir del propio
#     mallorca.geojson (no de memoria) y se lo pasamos a Nominatim con
#     bounded=1, que EXCLUYE por completo resultados fuera de esa caja.
#
#  2) EL FILTRO DE CLASE SOLO SE APLICA A LOS METODOS "DE RESPALDO".
#     v2 rechazaba cualquier resultado de clase "highway" (calle/camino),
#     lo cual esta bien para evitar el bug de "Carrer de Selva en Palma",
#     pero MAL para las fincas rurales cuya direccion oficial ES un camino
#     ("Camada Real s/n", "Cami de Son Reixach"...). Ahi que Nominatim
#     devuelva class=highway es CORRECTO, no un fallo. v3 solo aplica el
#     filtro estricto a los metodos 2 y 3 (busqueda por nombre+localidad o
#     por localidad sola), nunca al metodo 1 (direccion exacta de la
#     fuente oficial).
#
#  3) TOLERANCIA DE COSTA.
#     "Es Tomeu" geocodifico a solo 95 m de Andratx pero fuera del
#     poligono estricto (las lineas de costa de OSM y del IGN no
#     coinciden al metro). Si un punto no cae dentro de NINGUN poligono
#     pero esta a menos de ~350 m del mas cercano, se asigna a ese
#     municipio con una nota explicita "asignado por proximidad de
#     costa", en vez de descartarlo.
#
#  Sigue sin inventar nada: lo que de verdad no se puede resolver con
#  confianza (ni por contencion estricta ni por proximidad de costa) va a
#  negocios_sin_geocodificar.json.
#
#  USO:  python geocodificar_negocios.py
# =============================================================================

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

FUENTE = Path("negocios_fuente.json")
GEOJSON = Path("datos/mallorca.geojson")
CACHE = Path("geocode_cache_v4.json")
SALIDA = Path("negocios_geocodificados.json")
SIN_GEOCODIFICAR = Path("negocios_sin_geocodificar.json")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LLYC-ANEVAL-BALEVAL-mapa-mallorca/3.0 (uso interno, contacto: proyecto-baleares@llyc.local)"
PAUSA_SEG = 1.1

CLASES_RECHAZADAS_RESPALDO = {"highway", "waterway", "railway", "boundary"}
CLASES_RECHAZADAS_DIRECCION = {"boundary"}  # a una direccion exacta solo le rechazamos esto
# La busqueda ESTRUCTURADA (city=) devuelve casi siempre class=boundary,
# type=administrative para una poblacion real -- eso es la respuesta
# CORRECTA a "dame este pueblo", no hay que rechazarla. Solo rechazamos
# calle/torrente/via, que ahi si serian una respuesta equivocada.
CLASES_RECHAZADAS_ESTRUCTURADO = {"highway", "waterway", "railway"}
DIST_FRONTERA_AVISO = 0.0018       # ~150-200 m: aviso de "cerca de otro municipio"
DIST_COSTA_TOLERANCIA = 0.0032     # ~350 m: margen por desajuste de linea de costa


def cargar_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def guardar_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def nominatim_get(params, cache_key, cache, clases_rechazadas):
    if cache_key in cache:
        return cache[cache_key]
    qs = urllib.parse.urlencode(params)
    url = f"{NOMINATIM_URL}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"    ! error de red (no se guarda en cache, se puede reintentar): {e}")
        time.sleep(PAUSA_SEG)
        return None  # OJO: no cacheamos un fallo de RED como si fuera "no existe"
    time.sleep(PAUSA_SEG)

    resultado = None
    for d in data:
        if d.get("class") in clases_rechazadas:
            continue
        resultado = {
            "lat": float(d["lat"]), "lon": float(d["lon"]),
            "display_name": d.get("display_name", ""),
            "osm_class": d.get("class"), "osm_type": d.get("type"),
        }
        break
    # aqui SI cacheamos, tanto si hay resultado como si Nominatim respondio
    # correctamente pero sin ningun match valido (eso es un "None" real)
    cache[cache_key] = resultado
    guardar_cache(cache)
    return resultado


def viewbox_param(bbox):
    minx, miny, maxx, maxy = bbox
    # Nominatim: viewbox=<left>,<top>,<right>,<bottom> = lon_min,lat_max,lon_max,lat_min
    return f"{minx},{maxy},{maxx},{miny}"


def geocodificar_direccion(texto, bbox):
    return {"q": texto, "format": "json", "limit": 3, "countrycodes": "es",
            "viewbox": viewbox_param(bbox), "bounded": 1}


def geocodificar_libre(texto, bbox):
    return {"q": texto, "format": "json", "limit": 3, "countrycodes": "es",
            "viewbox": viewbox_param(bbox), "bounded": 1}


def geocodificar_estructurado(nombre_lugar, bbox):
    return {"city": nombre_lugar, "state": "Illes Balears", "country": "Spain",
            "format": "json", "limit": 3, "countrycodes": "es",
            "viewbox": viewbox_param(bbox), "bounded": 1}


# --------------------------------------------------------------- geometria
def cargar_municipios():
    import geopandas as gpd
    gdf = gpd.read_file(GEOJSON).to_crs("EPSG:4326")
    invalidos = (~gdf.geometry.is_valid).sum()
    if invalidos:
        print(f"Reparando {invalidos} poligono(s) con geometria invalida (buffer 0)...")
        gdf["geometry"] = gdf.geometry.buffer(0)
    assert gdf.geometry.is_valid.all(), "Sigue habiendo poligonos invalidos tras la reparacion"
    return gdf


def resolver_municipio(lat, lon, municipios_gdf):
    """Devuelve (municipio, nota). nota indica si hubo aviso de frontera o
    si se asigno por proximidad de costa (nunca se inventa a mas distancia
    que DIST_COSTA_TOLERANCIA)."""
    from shapely.geometry import Point
    p = Point(lon, lat)

    contenedor = None
    for _, row in municipios_gdf.iterrows():
        if row.geometry.contains(p):
            contenedor = row["name"]
            break

    if contenedor is not None:
        distancias = []
        for _, row in municipios_gdf.iterrows():
            if row["name"] == contenedor:
                continue
            distancias.append((row.geometry.distance(p), row["name"]))
        distancias.sort()
        if distancias and distancias[0][0] < DIST_FRONTERA_AVISO:
            nota = f"cerca de la frontera con {distancias[0][1]} (a {distancias[0][0]*111000:.0f} m)"
            return contenedor, nota
        return contenedor, None

    # no esta ESTRICTAMENTE dentro de ningun poligono: probamos tolerancia
    # de costa (desajuste de linea de costa entre OSM y el IGN)
    distancias = sorted(((row.geometry.distance(p), row["name"]) for _, row in municipios_gdf.iterrows()))
    if distancias and distancias[0][0] < DIST_COSTA_TOLERANCIA:
        d_m = distancias[0][0] * 111000
        nota = f"asignado por proximidad de costa (fuera del poligono estricto por {d_m:.0f} m)"
        return distancias[0][1], nota

    return None, None


def main():
    fuente = json.loads(FUENTE.read_text(encoding="utf-8"))
    cache = cargar_cache()
    municipios = cargar_municipios()
    bbox = tuple(municipios.total_bounds)  # (minx, miny, maxx, maxy) real, del propio IGN
    print(f"Municipios cargados: {len(municipios)}")
    print(f"Viewbox real de Mallorca (bounded=1): lon {bbox[0]:.4f} a {bbox[2]:.4f} · lat {bbox[1]:.4f} a {bbox[3]:.4f}\n")

    todos = []
    for categoria in ("bodegas", "agroturismos", "gastronomia"):
        todos.extend(fuente[categoria])
    print(f"Negocios a geocodificar: {len(todos)}\n")

    resultados, fallidos = [], []
    for i, item in enumerate(todos, 1):
        nombre = item["nombre"]
        print(f"[{i}/{len(todos)}] {nombre} ({item['localidad_pedania']}) ...", end=" ")

        r, metodo = None, None

        if item.get("direccion_exacta"):
            q = f"{item['direccion_exacta']}, Illes Balears, Spain"
            r = nominatim_get(geocodificar_direccion(q, bbox), f"dir::{q}", cache,
                               CLASES_RECHAZADAS_DIRECCION)
            metodo = "direccion exacta"

        if r is None:
            q = f"{nombre}, {item['localidad_pedania']}, Mallorca, Spain"
            r = nominatim_get(geocodificar_libre(q, bbox), f"libre::{q}", cache,
                               CLASES_RECHAZADAS_RESPALDO)
            metodo = "nombre+localidad (texto libre)"

        if r is None:
            r = nominatim_get(geocodificar_estructurado(item["localidad_pedania"], bbox),
                               f"struct::{item['localidad_pedania']}", cache,
                               CLASES_RECHAZADAS_ESTRUCTURADO)
            metodo = "localidad (busqueda estructurada 'city=')"

        if r is None:
            print("SIN GEOCODIFICAR")
            fallidos.append({**item, "motivo": "ningun metodo dio un resultado valido dentro de Mallorca"})
            continue

        municipio_oficial, nota = resolver_municipio(r["lat"], r["lon"], municipios)
        if municipio_oficial is None:
            print(f"geocodificado (lat={r['lat']}, lon={r['lon']}) pero demasiado lejos de cualquier municipio -- revisar")
            fallidos.append({**item, "lat": r["lat"], "lon": r["lon"],
                              "motivo": "geocodificado pero sin municipio IGN cercano"})
            continue

        etiqueta = municipio_oficial + (f"  [{nota}]" if nota else "")
        print(f"OK -> {etiqueta}  ({metodo})")

        resultados.append({
            **item,
            "lat": r["lat"], "lon": r["lon"],
            "municipio_oficial": municipio_oficial,
            "nota_geometria": nota,
            "metodo_geocodificacion": metodo,
            "osm_class": r.get("osm_class"), "osm_type": r.get("osm_type"),
            "nominatim_display_name": r["display_name"],
        })

    SALIDA.write_text(json.dumps({"negocios": resultados}, ensure_ascii=False, indent=1), encoding="utf-8")
    SIN_GEOCODIFICAR.write_text(json.dumps({"pendientes": fallidos}, ensure_ascii=False, indent=1), encoding="utf-8")

    con_nota = [r for r in resultados if r["nota_geometria"]]
    print("\n=========== RESUMEN ===========")
    print(f"Geocodificados y asignados a municipio real: {len(resultados)}")
    print(f"  ...de los cuales con nota (revisar igual):  {len(con_nota)}")
    print(f"Sin geocodificar / a revisar a mano:          {len(fallidos)}")
    if fallidos:
        print("   -> " + ", ".join(f['nombre'] for f in fallidos))
    if con_nota:
        print("\n   Con nota:")
        for r in con_nota:
            print(f"   - {r['nombre']}: {r['municipio_oficial']}  ({r['nota_geometria']})")
    print(f"\nEscrito: {SALIDA}")
    print(f"Pendientes de revisar: {SIN_GEOCODIFICAR}")

    print("\n--- Verificacion casos ya conocidos ---")
    for r in resultados:
        if r["nombre"] in ("Petit Caimari", "Son Fogueró", "Es Tomeu", "Sa Carrotja",
                            "Restaurant Alma - Cas Patró", "Casal Santa Eulàlia", "Predi Son Serra"):
            print(f"   {r['nombre']:<28} -> {r['municipio_oficial']}  {r['nota_geometria'] or ''}")


if __name__ == "__main__":
    main()
