#!/usr/bin/env python3
# =============================================================================
#  diagnostico_nominatim_raw.py
#  Muestra la respuesta CRUDA de Nominatim (sin ningun filtro nuestro) para
#  un puñado de consultas que estan fallando, para saber si el problema es
#  "Nominatim no devuelve nada" o "devuelve algo y lo estamos descartando
#  mal". No escribe nada, solo imprime.
#  USO:  python diagnostico_nominatim_raw.py
# =============================================================================
import json
import time
import urllib.parse
import urllib.request

USER_AGENT = "LLYC-ANEVAL-BALEVAL-mapa-mallorca/diagnostico (contacto: proyecto-baleares@llyc.local)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
BBOX = (2.3058, 39.1248, 3.4754, 39.9617)  # el mismo bbox real que usa el script principal


def query_raw(params, etiqueta):
    qs = urllib.parse.urlencode(params)
    url = f"{NOMINATIM_URL}?{qs}"
    print(f"\n=== {etiqueta} ===")
    print(f"URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ERROR DE RED: {e}")
        return
    print(f"Numero de resultados: {len(data)}")
    for i, d in enumerate(data):
        print(f"  [{i}] class={d.get('class')} type={d.get('type')} "
              f"lat={d.get('lat')} lon={d.get('lon')}")
        print(f"       display_name: {d.get('display_name')}")
    time.sleep(1.1)


minx, miny, maxx, maxy = BBOX
viewbox = f"{minx},{maxy},{maxx},{miny}"

# --- caso 1: estructurado, ciudad grande y conocida que esta fallando ---
query_raw({"city": "Santanyí", "state": "Illes Balears", "country": "Spain",
           "format": "json", "limit": 5, "countrycodes": "es",
           "viewbox": viewbox, "bounded": 1},
          "ESTRUCTURADO city=Santanyí + bounded=1")

query_raw({"city": "Santanyí", "state": "Illes Balears", "country": "Spain",
           "format": "json", "limit": 5, "countrycodes": "es"},
          "ESTRUCTURADO city=Santanyí SIN bounded (para comparar)")

# --- caso 2: texto libre nombre+localidad que esta fallando ---
query_raw({"q": "Es Pujol, Santanyí, Mallorca, Spain", "format": "json",
           "limit": 5, "countrycodes": "es", "viewbox": viewbox, "bounded": 1},
          "LIBRE 'Es Pujol, Santanyí, Mallorca, Spain' + bounded=1")

query_raw({"q": "Es Pujol, Santanyí, Mallorca, Spain", "format": "json",
           "limit": 5, "countrycodes": "es"},
          "LIBRE 'Es Pujol, Santanyí, Mallorca, Spain' SIN bounded (para comparar)")

# --- caso 3: otro pueblo grande que tambien esta fallando (Manacor) ---
query_raw({"city": "Manacor", "state": "Illes Balears", "country": "Spain",
           "format": "json", "limit": 5, "countrycodes": "es",
           "viewbox": viewbox, "bounded": 1},
          "ESTRUCTURADO city=Manacor + bounded=1")

print("\nFIN. Pega esta salida completa.")
