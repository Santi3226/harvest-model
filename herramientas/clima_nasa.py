"""Genera las series de clima del modelo a partir de NASA POWER y las inyecta en el .alp.

Uso (desde la raiz del repo):
    python3 herramientas/clima_nasa.py            # baja los datos si falta el CSV e inyecta
    python3 herramientas/clima_nasa.py --verificar # solo compara contra lo que tiene el .alp

Que hace:
1. Baja de NASA POWER (reanalisis MERRA-2, punto -33,0 / -61,0, zona Rosario) la lluvia
   diaria corregida y las temperaturas maxima y minima, del 1/10/2005 al 30/9/2025.
   El CSV crudo queda en datos/ para que cualquiera pueda auditar el origen.
2. Arma 20 campanias. La campania c va del 1/10/(2005+c) al 30/9/(2006+c): 365 dias,
   o 366 si incluye un 29 de febrero. El dia 0 del modelo es siempre el 1 de octubre.
3. Calcula tres series por campania:
   - lluvia [mm/dia], redondeada a 1 decimal.
   - temperatura media [C] = (Tmax + Tmin) / 2, redondeada a 1 decimal.
   - ET0 [mm/dia] por Hargreaves (FAO-56, ec. 52), redondeada a 2 decimales.
4. Reemplaza el valor inicial de las variables String climaLluvia, climaTmedia y climaEt0
   de Main. Formato: dias separados por "," y campanias separadas por ";".
   Main.cargarClima() las parsea al arrancar.

Por que String y no un arreglo: AnyLogic mete la inicializacion de todas las variables de
un agente en un solo metodo Java, y un metodo no puede pasar de 64 KB de bytecode.
Un String es una sola constante (limite propio: 65.535 bytes; la mayor serie mide ~36 KB).
"""
import datetime as dt
import math
import os
import re
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALP = os.path.join(RAIZ, "Optimización de la Ventana de Siembra.alp")
CSV = os.path.join(RAIZ, "datos", "nasa_power_rosario_2005-2025.csv")
URL = ("https://power.larc.nasa.gov/api/temporal/daily/point"
       "?parameters=PRECTOTCORR,T2M_MAX,T2M_MIN&community=ag"
       "&longitude=-61.0&latitude=-33.0&start=20051001&end=20250930&format=CSV")
LATITUD = math.radians(-33.0)
CAMPANIAS = 20


def bajar():
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    with urllib.request.urlopen(URL, timeout=300) as r:
        open(CSV, "wb").write(r.read())


def leer():
    datos = {}
    for linea in open(CSV):
        if not linea[:2] == "20":          # salta el encabezado de NASA
            continue
        anio, doy, lluvia, tmax, tmin = linea.strip().split(",")[:5]
        fecha = dt.date(int(anio), 1, 1) + dt.timedelta(int(doy) - 1)
        valores = (float(lluvia), float(tmax), float(tmin))
        if -999 in valores:
            sys.exit(f"dato faltante en {fecha}")
        datos[fecha] = valores
    return datos


def radiacion_extraterrestre(fecha):
    """Ra [MJ/m2/dia], FAO-56 ecuaciones 21 a 25."""
    j = fecha.timetuple().tm_yday
    dr = 1 + 0.033 * math.cos(2 * math.pi * j / 365)
    decl = 0.409 * math.sin(2 * math.pi * j / 365 - 1.39)
    ws = math.acos(-math.tan(LATITUD) * math.tan(decl))
    return 24 * 60 / math.pi * 0.0820 * dr * (
        ws * math.sin(LATITUD) * math.sin(decl)
        + math.cos(LATITUD) * math.cos(decl) * math.sin(ws))


def et0_hargreaves(fecha, tmax, tmin):
    """ET0 [mm/dia] = 0,0023 (Tmedia + 17,8) raiz(Tmax - Tmin) Ra, con Ra pasada a mm (x 0,408)."""
    tmedia = (tmax + tmin) / 2
    return 0.0023 * (tmedia + 17.8) * math.sqrt(max(0, tmax - tmin)) * radiacion_extraterrestre(fecha) * 0.408


def texto(x, decimales):
    s = f"{round(x, decimales):.{decimales}f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def series(datos):
    lluvias, tmedias, et0s = [], [], []
    for c in range(CAMPANIAS):
        inicio, fin = dt.date(2005 + c, 10, 1), dt.date(2006 + c, 9, 30)
        ll, tm, et = [], [], []
        for i in range((fin - inicio).days + 1):
            fecha = inicio + dt.timedelta(i)
            lluvia, tmax, tmin = datos[fecha]
            ll.append(texto(lluvia, 1))
            tm.append(texto((tmax + tmin) / 2, 1))
            et.append(texto(et0_hargreaves(fecha, tmax, tmin), 2))
        lluvias.append(",".join(ll))
        tmedias.append(",".join(tm))
        et0s.append(",".join(et))
    return {"climaLluvia": ";".join(lluvias), "climaTmedia": ";".join(tmedias), "climaEt0": ";".join(et0s)}


def patron(nombre):
    # el valor inicial de la variable String <nombre> dentro de Main
    return re.compile(r"(<Name><!\[CDATA\[" + nombre + r"\]\]></Name>.*?<Code><!\[CDATA\[\")([^\"]*)(\"\]\]></Code>)", re.S)


def main():
    if not os.path.exists(CSV):
        print("bajando", URL)
        bajar()
    nuevas = series(leer())
    alp = open(ALP, encoding="utf-8").read()
    for nombre, valor in nuevas.items():
        coincidencias = patron(nombre).findall(alp)
        if len(coincidencias) != 1:
            sys.exit(f"{nombre}: se esperaba 1 coincidencia y hay {len(coincidencias)}")
        actual = coincidencias[0][1]
        dias = [len(f.split(",")) for f in valor.split(";")]
        print(f"{nombre}: {len(valor.encode())} bytes, {len(dias)} campanias, {min(dias)}-{max(dias)} dias"
              + ("  (sin cambios)" if actual == valor else ""))
        if len(valor.encode()) > 65535:
            sys.exit(f"{nombre} supera el limite de 65.535 bytes de una constante String")
        if "--verificar" not in sys.argv:
            alp = patron(nombre).sub(lambda m: m.group(1) + valor + m.group(3), alp, count=1)
    if "--verificar" not in sys.argv:
        open(ALP, "w", encoding="utf-8").write(alp)
        print("inyectado en", os.path.basename(ALP))


if __name__ == "__main__":
    main()
