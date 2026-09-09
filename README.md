# El mapa de la Mallorca inalcanzable — cómo obtener los datos 100% reales

Proyecto BALEARES (ANEVAL/BALEVAL) · LLYC

---

## 1. ¿Qué es GTFS? (en cristiano)

**GTFS = General Transit Feed Specification.** Es el formato estándar mundial con el que
las empresas de transporte público publican sus horarios. Es lo que lee Google Maps cuando
te dice "coge el bus 104 a las 10:15".

Un GTFS es simplemente **un .zip con varios ficheros de texto**:

| Fichero | Qué contiene |
|---|---|
| `stops.txt` | Cada parada, con su latitud y longitud |
| `routes.txt` | Cada línea (bus, tren) |
| `trips.txt` | Cada expedición concreta de cada línea |
| `stop_times.txt` | **El corazón**: a qué hora exacta pasa cada expedición por cada parada |
| `calendar.txt` | Qué días circula cada expedición (laborables, festivos, verano...) |

Es decir: **el GTFS del TIB es la verdad oficial sobre qué transporte público existe en
Mallorca, publicada por el propio Consorcio de Transportes.** Si el mapa dice que a un
pueblo no se llega, no lo decimos nosotros: lo dice la base de datos del Govern.

Por eso esta acción es imbatible. No es opinión, es su propio horario.

**Licencia:** CC-BY 4.0 (uso libre citando la fuente). El feed publicado tiene
**79 líneas y 786 paradas**.

---

## 2. ¿Qué es una isócrona?

Una **isócrona** es "hasta dónde puedes llegar en X minutos desde un punto".
Nosotros calculamos, desde el aeropuerto de Palma:

- ¿A qué municipios llegas en ≤90 min **en transporte público**?
- ¿A cuáles llegas en ≤90 min **en coche**?

La diferencia entre esos dos mapas **es el argumento entero del proyecto**.

Para calcularlo hace falta un **motor de enrutamiento**. Usamos **R5**, desarrollado por
Conveyal y usado en investigación académica de accesibilidad. Es importante que sea un
motor estándar y citable: si usáramos uno casero, nos lo discutirían.

---

## 3. Qué necesitas instalar (una vez)

```bash
# 1. Java 21 o superior  (R5 está escrito en Java)
java -version      # debe decir 21 o más

# 2. Librerías de Python
pip install r5py geopandas shapely pandas
```

---

## 4. Los tres ficheros que hay que descargar

Colócalos dentro de la carpeta `datos/`.

### a) GTFS del TIB → `datos/tib_gtfs.zip`
Portal de transparencia del Consorcio de Transportes de Mallorca:
**https://www.tib.org/es/sobre-ctm/portal-de-transparencia/datos-abiertos**
→ sección "Datos abiertos" → descargar la **base de datos de oferta (GTFS)**.

Alternativa oficial (Ministerio de Transportes, NAP):
**https://nap.transportes.gob.es/Files/Detail/1071** (requiere registro gratuito).

> Comprueba las fechas de `calendar.txt`: la fecha que uses en el script
> (`FECHA_HORA`) tiene que caer dentro del calendario del feed.

### b) Red viaria de OpenStreetMap → `datos/mallorca.osm.pbf`
De Geofabrik (descargas gratuitas de OSM):
**https://download.geofabrik.de/europe/spain.html**
Descarga Baleares/España y recorta a Mallorca, o busca directamente un extracto de Baleares.

Sirve para dos cosas: calcular los tiempos **en coche** y los tramos **a pie**
(del portal a la parada, y de la parada al destino).

### c) Límites municipales → `datos/mallorca.geojson`
**Ya lo tienes en este paquete.** Son los 53 municipios de Mallorca, geometría oficial del
Instituto Geográfico Nacional (IGN). No hay que tocar nada.

---

## 5. Ejecutar

```bash
python calcular_tiempos.py
```

Tarda unos minutos la primera vez (construye la red). Al terminar imprime algo así:

```
=========== RESULTADO REAL ===========
Municipios analizados:            53
Alcanzables en TP <= 90 min:      ??
NO alcanzables en TP <= 90 min:   ??
Sin servicio alguno:              ??
```

**Esas son las cifras reales.** Son las que se pueden publicar.

Y genera `tiempos_reales.json`.

Después:

```bash
node build_map.js
```

El mapa se regenera **solo**, usando los datos reales, y **la marca de agua
"DATOS SIMULADOS" desaparece automáticamente**. Está programado así a propósito: el mapa
solo pierde el aviso cuando los datos son de verdad.

---

## 6. Decisiones metodológicas (defiéndelas así si preguntan)

Están todas en la cabecera del script, y son deliberadamente **conservadoras**:

| Decisión | Valor | Por qué |
|---|---|---|
| Día | Laborable de temporada alta | Ni el mejor ni el peor día |
| Hora | Media mañana | Franja realista de llegada de vuelos |
| Ventana | 60 min, se toma la **mediana** | Evita el cherry-picking de "el peor bus del día" |
| Caminata máx. | 20 min | Acceso a pie razonable |
| Velocidad a pie | 4,5 km/h | Estándar en la literatura |
| Destino | Punto representativo del polígono del IGN | No lo elegimos nosotros a ojo |
| No alcanzable | 999 | Explícito, no se disimula |

**Todo esto se publica junto al mapa.** Si alguien quiere replicarlo, que lo replique:
ese es justamente el punto. Es lo contrario de los estudios de carga que criticamos.

---

## 7. Lo que aún falta para la versión pública

- [ ] **Capa de negocios real**: registro del C.R. D.O. Binissalem, D.O. Pla i Llevant,
      Asoc. Balear de Agroturismo, AFEDECO/PIMECO. (Pedirla es, en sí, acción de alianza.)
- [ ] **Ibiza, Menorca y Formentera**: tienen consorcios distintos → hay que localizar
      sus feeds GTFS.
- [ ] **Validación técnica externa** (Camins Balears) antes de publicar.
- [ ] **Go / no-go**: si los números no sostienen el relato, no se publica la cara A.
      Se pivota a la cara B (turística) y no se pierde la inversión.

---

## 8. Regla de oro

> Primero calculamos. Después decidimos el titular.
> Nunca al revés.

La fuerza de este mapa es ser aritmética honesta frente a percepciones.
Si lo forzamos, nos convertimos en aquello que criticamos.
