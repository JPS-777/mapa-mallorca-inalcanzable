#!/usr/bin/env python3
# =============================================================================
#  auditar_anomalias_tiempo.py
#  Revisa los 53 municipios A LA VEZ (no uno por uno cuando alguien pregunta).
#  Para cada uno, calcula la distancia real en linea recta desde el
#  aeropuerto y la compara con el tiempo en transporte publico y en coche.
#  Marca como SOSPECHOSO cualquier municipio donde el TP tarde muchisimo
#  mas de lo que la distancia y el tiempo en coche sugieren que deberia
#  tardar -- exactamente el patron que delato lo de Sencelles/Costitx y
#  ahora Calvia/Puigpunyent.
#  No corrige nada solo. Solo señala donde mirar con diagnostico detallado.
#  USO:  python auditar_anomalias_tiempo.py
# =============================================================================
import json
import math
from pathlib import Path

import pandas as pd

TIEMPOS = Path("tiempos_reales.json")
AUDIT = Path("auditoria_puntos.csv")
ORIGEN = (39.551667, 2.738889)  # lat, lon aeropuerto


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    if not TIEMPOS.exists() or not AUDIT.exists():
        print("Faltan tiempos_reales.json o auditoria_puntos.csv. Ejecuta antes calcular_tiempos.py")
        return

    data = json.loads(TIEMPOS.read_text(encoding="utf-8"))
    munis = data["municipios"]
    puntos = pd.read_csv(AUDIT).set_index("name")

    filas = []
    for nombre, (tp, car) in munis.items():
        if nombre not in puntos.index:
            continue
        lat, lon = puntos.loc[nombre, "lat"], puntos.loc[nombre, "lon"]
        dist = haversine_km(ORIGEN[0], ORIGEN[1], lat, lon)
        # velocidad media implicita del transporte publico (linea recta / tiempo)
        vel_tp = (dist / (tp / 60)) if tp and tp < 999 else 0
        # ratio TP vs coche: cuanto mas lento es el TP respecto al coche
        ratio = (tp / car) if car else None
        filas.append({
            "municipio": nombre, "dist_km": round(dist, 1),
            "tp_min": tp, "car_min": car,
            "ratio_tp_car": round(ratio, 2) if ratio else None,
            "vel_tp_kmh": round(vel_tp, 1),
        })

    df = pd.DataFrame(filas).sort_values("dist_km")

    print("=========== TODOS LOS MUNICIPIOS, ORDENADOS POR DISTANCIA AL AEROPUERTO ===========")
    print(df.to_string(index=False))

    # --- deteccion de sospechosos ---
    # Un municipio es sospechoso si esta CERCA (menos de 20 km en linea recta,
    # similar a Calvia/Puigpunyent/Sencelles) pero el TP tarda desproporcionado
    # (ratio TP/coche muy alto, o velocidad implicita del TP muy baja).
    cercanos = df[df["dist_km"] <= 20]
    sospechosos = cercanos[(cercanos["ratio_tp_car"] >= 2.2) | (cercanos["vel_tp_kmh"] <= 12)]

    print("\n=========== SOSPECHOSOS (a <20 km del aeropuerto, TP desproporcionado) ===========")
    if sospechosos.empty:
        print("Ninguno. Todos los municipios cercanos tienen un TP razonable respecto al coche.")
    else:
        print(sospechosos.to_string(index=False))
        print("\nEstos son candidatos a revisar con un diagnostico detallado (itinerario paso a")
        print("paso + frecuencia real de la linea), como se hizo con Sencelles/Costitx y ahora")
        print("con Calvia/Puigpunyent. No asumas que el numero esta mal: puede ser una linea de")
        print("baja frecuencia real. Pero hay que MIRARLO, no darlo por bueno ni por malo a ciegas.")

    print(f"\nTotal municipios analizados: {len(df)}")
    print(f"Total sospechosos encontrados: {len(sospechosos)}")


if __name__ == "__main__":
    main()
