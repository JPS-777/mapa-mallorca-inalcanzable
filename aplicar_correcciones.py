#!/usr/bin/env python3
# =============================================================================
#  aplicar_correcciones.py   ·   v2
#  Proyecto BALEARES (ANEVAL/BALEVAL) - LLYC
#
#  CAMBIO RESPECTO A v1: IDEMPOTENTE.
#  v1 volvia a "aplicar" la correccion aunque ya estuviera aplicada (se veia
#  como "CORREGIDO: Petra -> Petra"), y de paso sobreescribia el campo de
#  auditoria municipio_oficial_original_ign con el valor YA corregido,
#  perdiendo el rastro de cual era el dato original del IGN antes de tocar
#  nada. v2 comprueba si el cambio ya esta aplicado y, si es asi, no hace
#  nada (ademas de no volver a pisar el campo de auditoria si ya existe).
#  Ahora es seguro ejecutar este script tantas veces como haga falta.
#
#  QUE HACE
#  Aplica, ENCIMA del resultado automatico de geocodificar_negocios.py,
#  un pequeno numero de correcciones manuales DOCUMENTADAS Y CON FUENTE,
#  para los casos donde la geometria estricta del IGN entra en conflicto
#  con la direccion postal oficial o con el propio etiquetado de OSM.
#
#  CORRECCIONES APLICADAS (verificadas en esta sesion):
#
#  1) Miquel Oliver: geometria IGN -> Ariany (a 158 m de la frontera).
#     Direccion oficial: "Ctra Petra-Sta Margalida KM 1.8, 07520 Petra".
#     07520 es el codigo postal oficial de PETRA (07529 seria Ariany).
#     -> Se corrige a Petra, se documenta el conflicto.
#
#  2) Son Fogueró: geometria IGN -> Sineu (a 138 m de la frontera).
#     La propia ficha de OpenStreetMap para este negocio incluye el
#     codigo postal 07519, que es el de MARIA DE LA SALUT (Sineu seria
#     07510). Doble coincidencia (etiqueta OSM + codigo postal real)
#     -> Se corrige a Maria de la Salut, se documenta el conflicto.
#
#  3) Finca Serena (Montuïri, con aviso de frontera a 128 m de Algaida):
#     NO se corrige. Se mantiene Montuïri, con la nota conservada.
#
#  4) Es Tomeu (Andratx, asignado por proximidad de costa a 95 m):
#     NO se corrige. Se mantiene Andratx.
#
#  5) Finca Son Cladera: si aparece duplicada, se deja una unica entrada
#     (verificado con 3 fuentes independientes: es un unico establecimiento
#     real en Sa Pobla).
#
#  USO:  python aplicar_correcciones.py
#  (ejecutar DESPUES de geocodificar_negocios.py; es seguro relanzarlo
#  las veces que haga falta, no duplica ni pisa correcciones ya aplicadas)
# =============================================================================

import json
from pathlib import Path

ENTRADA = Path("negocios_geocodificados.json")
SALIDA = Path("negocios_geocodificados.json")  # se sobreescribe, con backup previo
BACKUP = Path("negocios_geocodificados.antes_de_correcciones.json")

CORRECCIONES_MUNICIPIO = {
    "Miquel Oliver": {
        "nuevo_municipio": "Petra",
        "motivo": "Direccion oficial 'Ctra Petra-Sta Margalida KM 1.8, 07520 Petra'. "
                  "07520 es el CP oficial de Petra (07529 seria Ariany). "
                  "La geometria IGN lo situaba en Ariany, a solo 158 m de la frontera.",
    },
    "Son Fogueró": {
        "nuevo_municipio": "Maria de la Salut",
        "motivo": "La propia ficha de OpenStreetMap para este negocio declara CP 07519 "
                  "(Maria de la Salut; Sineu seria 07510), coincidiendo con su etiqueta "
                  "de localidad OSM. La geometria IGN lo situaba en Sineu, a 138 m de la frontera.",
    },
}


def main():
    if not ENTRADA.exists():
        print(f"ERROR: no encuentro {ENTRADA}. Ejecuta antes geocodificar_negocios.py")
        return

    data = json.loads(ENTRADA.read_text(encoding="utf-8"))
    negocios = data["negocios"]

    # backup SOLO si no existe ya uno (para no ir pisando el backup original
    # con versiones ya corregidas en relanzamientos sucesivos)
    if not BACKUP.exists():
        BACKUP.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Backup del fichero original guardado en: {BACKUP}")
    else:
        print(f"(ya existia un backup en {BACKUP}, no se sobreescribe)")

    # --- 1 y 2: correcciones de municipio con fuente documentada ---
    corregidos = 0
    ya_aplicadas = 0
    for neg in negocios:
        c = CORRECCIONES_MUNICIPIO.get(neg["nombre"])
        if not c:
            continue
        if neg["municipio_oficial"] == c["nuevo_municipio"]:
            # ya estaba aplicada en una ejecucion anterior sobre este mismo
            # fichero: no se toca, y sobre todo NO se pisa el rastro de
            # auditoria si ya existe.
            ya_aplicadas += 1
            print(f"YA ESTABA CORREGIDO (sin cambios): {neg['nombre']} -> {neg['municipio_oficial']}")
            continue
        antes = neg["municipio_oficial"]
        if "municipio_oficial_original_ign" not in neg:
            neg["municipio_oficial_original_ign"] = antes
        neg["municipio_oficial"] = c["nuevo_municipio"]
        neg["correccion_manual"] = c["motivo"]
        print(f"CORREGIDO: {neg['nombre']}: {antes} -> {c['nuevo_municipio']}")
        print(f"           motivo: {c['motivo']}")
        corregidos += 1

    # --- 3 y 4: Finca Serena y Es Tomeu se mantienen, solo se confirma ---
    for nombre_confirmar in ("Finca Serena", "Es Tomeu"):
        for neg in negocios:
            if neg["nombre"] == nombre_confirmar:
                print(f"CONFIRMADO SIN CAMBIOS: {neg['nombre']} -> {neg['municipio_oficial']} "
                      f"(nota conservada: {neg.get('nota_geometria')})")

    # --- 5: deduplicar Finca Son Cladera (idempotente: si ya no hay duplicado, no hace nada) ---
    vistos = set()
    unicos = []
    duplicados_eliminados = 0
    for neg in negocios:
        clave = neg["nombre"]
        if clave == "Finca Son Cladera":
            if clave in vistos:
                duplicados_eliminados += 1
                print(f"DUPLICADO ELIMINADO: {neg['nombre']} "
                      f"(verificado como establecimiento unico en {neg['municipio_oficial']})")
                continue
            vistos.add(clave)
        unicos.append(neg)

    data["negocios"] = unicos
    data["meta_correcciones"] = {
        "correcciones_municipio_aplicadas_esta_vez": corregidos,
        "correcciones_ya_estaban_aplicadas": ya_aplicadas,
        "duplicados_eliminados_esta_vez": duplicados_eliminados,
        "detalle": CORRECCIONES_MUNICIPIO,
    }

    SALIDA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n=========== RESUMEN ===========")
    print(f"Negocios antes: {len(negocios)}")
    print(f"Negocios despues (tras deduplicar): {len(unicos)}")
    print(f"Correcciones aplicadas AHORA: {corregidos}")
    print(f"Correcciones que ya estaban de antes: {ya_aplicadas}")
    print(f"Duplicados eliminados: {duplicados_eliminados}")
    print(f"\nEscrito: {SALIDA}")
    print("Ahora ejecuta:  node build_map.js")


if __name__ == "__main__":
    main()
