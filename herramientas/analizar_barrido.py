"""Analiza el barrido de ParametersVariation: sistema base contra sistema alternativo C.

Uso (desde la raiz del repo):
    python herramientas/analizar_barrido.py                       # lee resultados.csv
    python herramientas/analizar_barrido.py otro.csv --salida salida/
    python herramientas/analizar_barrido.py --param perdida_kg_ha_dia=36   # sensibilidad
    python herramientas/analizar_barrido.py --demo                # prueba con datos SINTETICOS

Que hace (parte 4.5 de docs/PLAN.md):
1. Controla el CSV: columnas, cantidad de filas, pares (campaña, replica) completos, semillas
   comunes entre los dos sistemas y las causas de parada (suman lo detenido, 'otra' = 0).
2. Arma los dos sistemas. Base: 12 lotes, un tren (tren = 1). Alternativo: 18 lotes, dos trenes de
   9 lotes (tren = 1 y tren = 2), uniendo las dos corridas de la misma (campaña, replica).
3. Calcula ingreso, costos y margen por campaña en US$ con los parametros de PARAMETROS.
   Casi todos son SUPUESTOS sin fuente: se declaran en el informe y se barren en la sensibilidad.
4. Compara por pares: diferencia de margen con IC del 95% de dos maneras (con las observaciones,
   como en el TP 3, y por campaña, que es la conservadora), proporcion de siembras a tiempo
   (test de McNemar) y media acumulada de la diferencia (convergencia, como en el TP 3).
5. Valida el modelo sin teoria cerrada, al estilo del TP 2.2: la meta de madurez contra la media
   y el desvio de la triangular, y las fallas contra horas trabajadas / MTBF.
6. Medidas de desempeño de Law y Kelton, adaptadas (servidor = tren, clientes = lotes que llegan
   todos al abrir la labor): b(n) de la maquina, del carro y del camion, q(n) y d(n), con IC.
7. Horizonte de la simulacion: muestra que es una simulacion con fin natural (terminante) y que
   la cola de lotes se vacia en todas las replicas, asi que no hay estado estable que estimar.
Con --salida escribe ademas los graficos SVG del informe (herramientas/graficos_svg.py).

Solo usa la biblioteca estandar.
"""
import argparse
import csv
import math
import os
import random
import sys
import tempfile
from collections import defaultdict
from statistics import NormalDist, mean, stdev

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_POR_DEFECTO = os.path.join(RAIZ, "resultados.csv")

# ---------------------------------------------------------------------------------------------
# Parametros economicos y del diseño. Cada uno dice de donde sale. Los marcados SUPUESTO no
# tienen fuente (ver docs/PLAN.md, parte 4.3): se eligen para que el margen del base sea positivo.
# ---------------------------------------------------------------------------------------------
PARAMETROS = {
    # --- diseño del barrido ---
    "dia_limite_siembra": 45,       # 15/11, el dia 0 es el 1/10
    "ha_por_lote": 104.4,           # 145 hileras de 9 m por 800 m (Main.auditarSemilla)
    "lotes_base": 12,
    "lotes_alt_por_tren": 9,
    "lotes_propios": 12,            # del alternativo, los demas son arrendados
    "mtbf_horas": 100.0,            # SUPUESTO (Main.mtbfHoras)
    "gdd_min": 1700.0,              # SUPUESTO, triangular de la meta de madurez
    "gdd_moda": 1900.0,
    "gdd_max": 2100.0,
    "alfa": 0.05,
    "p_min_a_tiempo": 0.90,         # probabilidad minima de terminar la siembra a tiempo
    # --- ingreso ---
    "rinde_potencial_kg_ha": 4100.0,  # BCR GEA 2025/26, soja de primera, zona nucleo: 41 qq/ha
    "rinde_sin_cosechar": 0.80,       # SUPUESTO: fraccion del rinde que conserva un lote sembrado cuya cosecha no cierra antes del
                                      # 30/9 (la cosecha sigue en octubre: perdida por demora, desgrane y tiempo en el campo). Sensibilidad: 0 a 1
    "perdida_kg_ha_dia": 25.0,        # por dia de siembra despues del 15/11 (Rossi, zona nucleo; sin fuente INTA). Sensibilidad: 15 y 36
    "precio_usd_t": 331.0,            # AgBi, soja campaña 2026/27
    "flete_pct": 0.10,                # SUPUESTO, flete y comercializacion sobre el ingreso
    # --- costos ---
    "insumos_usd_ha": 350.0,          # SUPUESTO: de los ~700 US$/ha de implantar soja (BCR), sin labores ni cosecha propias
    "arriendo_qq_ha": 15.0,           # Infocampo / BCR: ~15 qq/ha en el sudeste de Cordoba
    "fijo_tren_usd": 120000.0,        # SUPUESTO: poseer un tren (maquina, carro y camion): amortizacion, interes y seguro por campaña.
                                      # Referencia: un contratista cobra ~165 a 190 US$/ha (FACMA 2026/27), ~205.000 a 240.000 US$ por 1.253 ha
    "salario_mes_usd": 1200.0,        # SUPUESTO: CCT UATRE (ARS 1.892.406,17/mes en oct 2026) a ~1.575 ARS/US$ (bruto, sin cargas)
    "costo_hora_usd": 40.0,           # SUPUESTO: combustible (~25 l/h) y mantenimiento por hora trabajada
    "costo_falla_usd": 300.0,         # SUPUESTO: reparacion por falla
}

ENCABEZADO = (["lotes", "turnos", "campaña", "replica", "tren", "semillaFallas", "semillaMadurez", "gddMeta",
               "diaFinSiembra", "diaMadurez", "diaFinCosecha"])
POR_PASADA = ["trabajando", "detenida", "viajes", "diasSinPiso", "fallas", "horasReparando",
              "falla", "sinSemilla", "jornada", "sinPiso", "esperaCarro", "traslado", "otra",
              "carroOcioso", "carroViajando", "carroConLaMaquina", "carroEsperaCamion", "carroDescargando",
              "carroCargaSemilla", "camionEsperaCarro", "camionCargando", "camionViajando", "camionDescargando"]
CAUSAS = ["falla", "sinSemilla", "jornada", "sinPiso", "esperaCarro", "traslado", "otra"]
COLUMNAS = (ENCABEZADO + ["s_" + c for c in POR_PASADA] + ["c_" + c for c in POR_PASADA]
            + ["diasSiembraLote", "diasCosechaLote"])


# =============================================================================================
# Estadistica basica (sin scipy)
# =============================================================================================
def _betacf(a, b, x):
    """Fraccion continua de la beta incompleta (Numerical Recipes, betacf)."""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def _beta_incompleta(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    frente = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return frente * _betacf(a, b, x) / a
    return 1.0 - frente * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, gl):
    x = gl / (gl + t * t)
    cola = 0.5 * _beta_incompleta(gl / 2.0, 0.5, x)
    return 1.0 - cola if t > 0 else cola


def t_critico(gl, alfa=0.05):
    """Cuantil 1 - alfa/2 de la t de Student, por biseccion sobre la CDF."""
    objetivo = 1.0 - alfa / 2.0
    lo, hi = 0.0, 100.0
    for _ in range(200):
        medio = (lo + hi) / 2.0
        if t_cdf(medio, gl) < objetivo:
            lo = medio
        else:
            hi = medio
    return (lo + hi) / 2.0


def ic_media(valores, alfa=0.05):
    """(media, desvio, n, inferior, superior) con t de Student."""
    n = len(valores)
    m = mean(valores)
    if n < 2:
        return m, float("nan"), n, float("nan"), float("nan")
    s = stdev(valores)
    medio = t_critico(n - 1, alfa) * s / math.sqrt(n)
    return m, s, n, m - medio, m + medio


def mcnemar_exacto(b, c):
    """p-valor bilateral exacto del test de McNemar (binomial con p = 0,5 sobre los discordantes)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cola = sum(math.comb(n, i) for i in range(k + 1)) / 2.0 ** n
    return min(1.0, 2.0 * cola)


# =============================================================================================
# Lectura y control del CSV
# =============================================================================================
def _num(txt):
    txt = txt.strip()
    return None if txt in ("", "NA") else float(txt)


def _dias(txt):
    return [_num(x) for x in txt.split("|")] if txt.strip() else []


def leer_csv(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        lector = csv.reader(f, delimiter=";")
        cabecera = next(lector)
        if cabecera != COLUMNAS:
            faltan = [c for c in COLUMNAS if c not in cabecera]
            sys.exit(f"ERROR: el encabezado de {ruta} no es el del barrido nuevo ({len(cabecera)} columnas, se "
                     f"esperaban {len(COLUMNAS)}). Faltan: {faltan[:6]}. Si es el resultados.csv viejo, hay que "
                     f"rehacerlo corriendo ParametersVariation (docs/PLAN.md, paso 7).")
        filas = []
        for n, r in enumerate(lector, start=2):
            if len(r) != len(COLUMNAS):
                sys.exit(f"ERROR: la fila {n} tiene {len(r)} campos y se esperaban {len(COLUMNAS)}")
            d = {}
            for nombre, v in zip(COLUMNAS, r):
                if nombre in ("diasSiembraLote", "diasCosechaLote"):
                    d[nombre] = _dias(v)
                else:
                    d[nombre] = _num(v)
            filas.append(d)
    return filas


def controlar(filas, esperadas, P):
    """Devuelve (indice, avisos). indice[(campaña, replica, tren, lotes)] = fila."""
    avisos = []
    indice = {}
    for f in filas:
        clave = (int(f["campaña"]), int(f["replica"]), int(f["tren"]), int(f["lotes"]))
        if clave in indice:
            avisos.append(f"fila repetida para campaña/replica/tren/lotes = {clave}")
        indice[clave] = f
    if len(filas) != esperadas:
        avisos.append(f"hay {len(filas)} filas y se esperaban {esperadas}")
    # causas de parada: suman lo detenido y 'otra' da 0 (paso 4)
    mal = 0
    for f in filas:
        for p in ("s_", "c_"):
            suma = sum(f[p + c] or 0.0 for c in CAUSAS)
            if abs(suma - (f[p + "detenida"] or 0.0)) > 1e-6 or (f[p + "otra"] or 0.0) != 0.0:
                mal += 1
    if mal:
        avisos.append(f"{mal} pasadas con causas de parada que no suman lo detenido o con 'otra' distinta de 0")
    return indice, avisos


def armar_pares(indice, P):
    """Pares completos (campaña, replica): una corrida del base y dos del alternativo."""
    claves = sorted({(c, r) for (c, r, _, _) in indice})
    pares, incompletos = [], []
    for c, r in claves:
        base = indice.get((c, r, 1, P["lotes_base"]))
        a1 = indice.get((c, r, 1, P["lotes_alt_por_tren"]))
        a2 = indice.get((c, r, 2, P["lotes_alt_por_tren"]))
        if base and a1 and a2:
            pares.append({"campaña": c, "replica": r, "base": base, "alt": [a1, a2]})
        else:
            incompletos.append((c, r))
    return pares, incompletos


def controlar_semillas(pares):
    """El tren 1 del alternativo tiene que compartir semillas con el base; la madurez es la misma en los tres."""
    mal = 0
    for p in pares:
        b, a1, a2 = p["base"], p["alt"][0], p["alt"][1]
        if b["semillaFallas"] != a1["semillaFallas"]:
            mal += 1
        if not (b["semillaMadurez"] == a1["semillaMadurez"] == a2["semillaMadurez"]):
            mal += 1
        if a1["semillaFallas"] == a2["semillaFallas"]:
            mal += 1
    return mal


# =============================================================================================
# Modelo economico
# =============================================================================================
def evaluar(trenes, lotes_arrendados, P):
    """Ingreso, costos y margen de un sistema formado por una o mas corridas (trenes)."""
    siembra = [d for t in trenes for d in t["diasSiembraLote"]]
    cosecha = [d for t in trenes for d in t["diasCosechaLote"]]
    ha = P["ha_por_lote"]
    kg = 0.0
    sembrados = 0
    for ds, dc in zip(siembra, cosecha):
        if ds is None:
            continue
        sembrados += 1
        atraso = max(0.0, ds - P["dia_limite_siembra"])
        rinde = max(0.0, P["rinde_potencial_kg_ha"] - P["perdida_kg_ha_dia"] * atraso)
        if dc is None:
            # la cosecha no cierra dentro del año del barrido: sigue en octubre, no se pierde todo el lote
            rinde *= P["rinde_sin_cosechar"]
        kg += rinde * ha
    ingreso = kg / 1000.0 * P["precio_usd_t"]
    superficie = len(siembra) * ha

    operarios = 0.0
    for t in trenes:
        ds = [d for d in t["diasSiembraLote"] if d is not None]
        dc = [d for d in t["diasCosechaLote"] if d is not None]
        meses = (max(ds) if ds else 0.0) / 30.0
        meses += (max(0.0, max(dc) - t["diaMadurez"]) if dc and t["diaMadurez"] is not None else 0.0) / 30.0
        operarios += P["salario_mes_usd"] * meses

    horas = sum((t["s_trabajando"] or 0.0) + (t["c_trabajando"] or 0.0) for t in trenes)
    fallas = sum((t["s_fallas"] or 0.0) + (t["c_fallas"] or 0.0) for t in trenes)
    costos = {
        "flete": P["flete_pct"] * ingreso,
        "insumos": P["insumos_usd_ha"] * sembrados * ha,
        "arriendo": lotes_arrendados * ha * P["arriendo_qq_ha"] * 0.1 * P["precio_usd_t"],
        "fijo_trenes": P["fijo_tren_usd"] * len(trenes),
        "operarios": operarios,
        "combustible_mant": P["costo_hora_usd"] * horas,
        "reparaciones": P["costo_falla_usd"] * fallas,
    }
    fin_siembra = [t["diaFinSiembra"] for t in trenes]
    a_tiempo = all(d is not None and d != -1 and d <= P["dia_limite_siembra"] for d in fin_siembra)
    total = sum(costos.values())
    return {"ingreso": ingreso, "costos": costos, "costo_total": total, "margen": ingreso - total,
            "superficie": superficie, "margen_ha": (ingreso - total) / superficie if superficie else float("nan"),
            "a_tiempo": a_tiempo, "fin_siembra": max((d for d in fin_siembra if d is not None), default=-1),
            "sembrados": sembrados, "cosechados": sum(1 for ds, dc in zip(siembra, cosecha) if ds is not None and dc is not None),
            "lotes": len(siembra), "horas": horas, "fallas": fallas}


def evaluar_pares(pares, P):
    for p in pares:
        p["res_base"] = evaluar([p["base"]], 0, P)
        p["res_alt"] = evaluar(p["alt"], max(0, 2 * P["lotes_alt_por_tren"] - P["lotes_propios"]), P)
        for pasada in ("s", "c"):
            p["lk_base_" + pasada] = lk_sistema([p["base"]], pasada)
            p["lk_alt_" + pasada] = lk_sistema(p["alt"], pasada)
    return pares


# =============================================================================================
# Medidas de desempeño de Law y Kelton, adaptadas
# =============================================================================================
# Law y Kelton definen, para una cola con un servidor: d(n) = demora media en cola de los n clientes,
# q(n) = numero medio en cola en el tiempo (area bajo Q(t) / T(n)) y b(n) o u(n) = fraccion del tiempo
# en que el servidor esta ocupado (area bajo B(t) / T(n)). Adaptacion (la misma que el panel de Main):
#  - servidor: el tren de maquinas (maquina, carro y camion); clientes: los lotes.
#  - llegadas: todos los lotes llegan juntos al abrir la labor (siembra: dia 0 = 1/10; cosecha: dia de madurez).
#  - un lote entra en servicio cuando termina el anterior; el primero no espera. Traslados y paradas
#    (lluvia, jornada, fallas) son tiempo de servicio del lote en curso, no de cola.
#  - b(n) de la maquina = horas trabajando / horas de la labor; del carro y del camion = 1 - fraccion ociosa.
# Al cerrar la labor vale la ley de Little: q(n) * T(n) = n * d(n).
CARRO = ["carroOcioso", "carroViajando", "carroConLaMaquina", "carroEsperaCamion", "carroDescargando", "carroCargaSemilla"]
CAMION = ["camionEsperaCarro", "camionCargando", "camionViajando", "camionDescargando"]


def lk_tren(f, pasada):
    """Medidas de una corrida (un tren) en la siembra ('s') o la cosecha ('c'). None si la labor no cerro."""
    fin = f["diasSiembraLote"] if pasada == "s" else f["diasCosechaLote"]
    llegada = 0.0 if pasada == "s" else f["diaMadurez"]
    if not fin or llegada is None or any(x is None for x in fin) or f[pasada + "_trabajando"] is None:
        return None
    inicios = [llegada] + fin[:-1]
    T = fin[-1] - llegada
    demoras = [i - llegada for i in inicios]
    carro = [f[pasada + "_" + c] or 0.0 for c in CARRO]
    camion = [f[pasada + "_" + c] or 0.0 for c in CAMION]
    return {"n": len(fin), "T": T, "llegada": llegada, "inicios": inicios, "demoras": demoras,
            "d": mean(demoras), "q": sum(demoras) / T,
            "b_maquina": f[pasada + "_trabajando"] / (24.0 * T),
            "b_carro": 1.0 - carro[0] / sum(carro) if sum(carro) > 0 else 0.0,
            "b_camion": 1.0 - camion[0] / sum(camion) if sum(camion) > 0 else 0.0}


def lk_sistema(trenes, pasada):
    """Un sistema de uno o mas trenes en paralelo: d sobre todos los lotes, q = suma de las colas de los trenes
    (cada una promediada en su propia labor), b = promedio por servidor, T = la labor del tren mas lento."""
    ts = [lk_tren(t, pasada) for t in trenes]
    if any(t is None for t in ts):
        return None
    dem = [x for t in ts for x in t["demoras"]]
    return {"trenes": ts, "n": len(dem), "T": max(t["T"] for t in ts), "d": mean(dem), "q": sum(t["q"] for t in ts),
            "b_maquina": mean(t["b_maquina"] for t in ts), "b_carro": mean(t["b_carro"] for t in ts),
            "b_camion": mean(t["b_camion"] for t in ts)}


def cola_promedio(sistemas, paso=0.5):
    """Q(t) promedio de las replicas, con t en dias desde la apertura de la labor de cada tren.
    Q(t) = lotes que todavia no entraron en servicio (los trenes de un sistema se suman)."""
    tmax = max(t["T"] for s in sistemas for t in s["trenes"])
    xs = [i * paso for i in range(int(tmax / paso) + 2)]
    ys = []
    for x in xs:
        tot = 0
        for s in sistemas:
            for t in s["trenes"]:
                tot += sum(1 for i in t["inicios"] if i - t["llegada"] > x)
        ys.append(tot / len(sistemas))
    return xs, ys


# =============================================================================================
# Informe
# =============================================================================================
def pts(x, dec=0):
    """Numero con punto de miles (1.234.567), como se escribe en los docs."""
    return f"{x:,.{dec}f}".replace(",", ".") if dec == 0 else f"{x:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_usd(x):
    return f"{pts(x):>12}"


def seccion(titulo):
    print("\n" + titulo)
    print("-" * len(titulo))


def informe(pares, incompletos, avisos, P, esperadas, salida=None, sintetico=False):
    if sintetico:
        print("*" * 78)
        print("*  DATOS SINTETICOS: solo prueban el script. No son resultados del modelo.  *")
        print("*" * 78)
    seccion("1. Control del CSV")
    print(f"pares (campaña, replica) completos: {len(pares)}   incompletos: {len(incompletos)}")
    mal_sem = controlar_semillas(pares)
    print(f"semillas comunes (base = tren 1 del alternativo, misma madurez, fallas distintas entre trenes): "
          f"{'OK' if mal_sem == 0 else f'{mal_sem} incumplimientos'}")
    for a in avisos:
        print("AVISO:", a)
    if not pares:
        sys.exit("No hay pares completos: no se puede comparar.")

    seccion("2. Resultado economico por sistema (promedio de los pares, US$ por campaña)")
    rb = [p["res_base"] for p in pares]
    ra = [p["res_alt"] for p in pares]
    rubros = ["ingreso"] + list(rb[0]["costos"].keys())
    print(f"{'':<22}{'base':>14}{'alternativo':>14}")
    print(f"{'ingreso':<22}{_fmt_usd(mean(r['ingreso'] for r in rb))}{_fmt_usd(mean(r['ingreso'] for r in ra))}")
    for k in rb[0]["costos"]:
        print(f"{'- ' + k:<22}{_fmt_usd(mean(r['costos'][k] for r in rb))}{_fmt_usd(mean(r['costos'][k] for r in ra))}")
    print(f"{'= margen':<22}{_fmt_usd(mean(r['margen'] for r in rb))}{_fmt_usd(mean(r['margen'] for r in ra))}")
    print(f"{'superficie [ha]':<22}{pts(mean(r['superficie'] for r in rb)):>14}{pts(mean(r['superficie'] for r in ra)):>14}")
    print(f"{'margen por ha':<22}{pts(mean(r['margen_ha'] for r in rb)):>14}{pts(mean(r['margen_ha'] for r in ra)):>14}")
    print(f"{'fin de siembra [dia]':<22}{mean(r['fin_siembra'] for r in rb):>14.1f}{mean(r['fin_siembra'] for r in ra):>14.1f}")
    print(f"{'horas trabajadas':<22}{mean(r['horas'] for r in rb):>14.0f}{mean(r['horas'] for r in ra):>14.0f}")
    print(f"{'fallas':<22}{mean(r['fallas'] for r in rb):>14.1f}{mean(r['fallas'] for r in ra):>14.1f}")
    sin_cosechar = sum(r["lotes"] - r["cosechados"] for r in rb + ra)
    if sin_cosechar:
        print(f"AVISO: {sin_cosechar} lotes (sumando los dos sistemas) quedaron sin cosechar en el año y conservan el {P['rinde_sin_cosechar']:.0%} del rinde (rinde_sin_cosechar)")
    if mean(r["margen"] for r in rb) <= 0:
        print("AVISO: el margen del base es <= 0; los costos supuestos no estan calibrados (PLAN.md, paso 5)")

    seccion("3. Diferencia de margen (alternativo - base), par a par")
    alfa = P["alfa"]
    d = [p["res_alt"]["margen"] - p["res_base"]["margen"] for p in pares]
    dha = [p["res_alt"]["margen_ha"] - p["res_base"]["margen_ha"] for p in pares]
    por_campaña = defaultdict(list)
    for p, x in zip(pares, d):
        por_campaña[p["campaña"]].append(x)
    d_clima = [mean(v) for _, v in sorted(por_campaña.items())]
    nivel = int(round((1 - alfa) * 100))
    filas_ic = [("margen total, con las observaciones", d), ("margen total, POR CLIMA (conservador)", d_clima),
                ("margen por ha, con las observaciones", dha)]
    print(f"{'':<40}{'n':>5}{'media':>13}{'desvio':>12}   IC {nivel}%")
    for nombre, v in filas_ic:
        m, s, n, lo, hi = ic_media(v, alfa)
        print(f"{nombre:<40}{n:>5}{pts(m):>13}{pts(s):>12}   [{pts(lo)} ; {pts(hi)}]")
    m_c, _, n_c, lo_c, hi_c = ic_media(d_clima, alfa)
    m_o, _, _, lo_o, hi_o = ic_media(d, alfa)
    print("Las observaciones de un mismo clima no son independientes: manda el IC por clima (docs/PLAN.md, 4.5).")

    seccion("4. Siembra terminada antes del 15/11 (por pares)")
    ab = [p["res_base"]["a_tiempo"] for p in pares]
    aa = [p["res_alt"]["a_tiempo"] for p in pares]
    n = len(pares)
    b = sum(1 for x, y in zip(ab, aa) if y and not x)   # alternativo si, base no
    c = sum(1 for x, y in zip(ab, aa) if x and not y)   # base si, alternativo no
    pb, pa = sum(ab) / n, sum(aa) / n
    dif = (b - c) / n
    se = math.sqrt(max(0.0, b + c - (b - c) ** 2 / n)) / n
    z = NormalDist().inv_cdf(1 - alfa / 2)
    print(f"base: {pb:.1%}   alternativo: {pa:.1%}   diferencia: {dif:+.1%}  IC {nivel}% [{dif - z * se:+.1%} ; {dif + z * se:+.1%}]")
    print(f"discordantes: solo el alternativo a tiempo = {b}, solo el base a tiempo = {c}   McNemar exacto p = {mcnemar_exacto(b, c):.3f}")
    print(f"fracasos (base / alternativo): {n - sum(ab)} / {n - sum(aa)}   "
          f"{'la aproximacion normal vale' if min(n - sum(ab), sum(ab), n - sum(aa), sum(aa)) >= 5 else 'POCOS casos: leer solo el test exacto'}")

    seccion("5. Convergencia de la media de la diferencia (como el TP 3)")
    acum, corriente = [], 0.0
    for i, x in enumerate(d, start=1):
        corriente += x
        acum.append(corriente / i)
    puntos = sorted({k for k in (10, 20, 30, 50, 75, n) if k <= n})
    print("n observaciones:   " + "".join(f"{k:>12}" for k in puntos))
    print("media acumulada:   " + "".join(f"{pts(acum[k - 1]):>12}" for k in puntos))
    if len(puntos) > 1:
        ant = puntos[-2]
        print(f"variacion de la media entre n = {ant} y n = {n}: {abs(acum[-1] - acum[ant - 1]) / (abs(acum[-1]) or 1):.1%}")

    seccion("6. Decision")
    if lo_c > 0:
        ganador = "el sistema ALTERNATIVO (arrendar mas campo y sumar una maquina)"
    elif hi_c < 0:
        ganador = "el sistema BASE"
    else:
        ganador = None
    if ganador:
        print(f"Con el IC por clima, el IC de la diferencia no incluye el 0: conviene {ganador}.")
    else:
        print("Con el IC por clima, el IC de la diferencia incluye el 0: NO hay diferencia significativa de margen.")
    mha, _, _, lo_h, hi_h = ic_media(dha, alfa)
    if (lo_h > 0) != (lo_c > 0) or (hi_h < 0) != (hi_c < 0):
        print(f"OJO: por hectarea el resultado es distinto (diferencia media {pts(mha)} US$/ha, IC [{pts(lo_h)} ; {pts(hi_h)}]): "
              "el sistema con mas campo gana en margen total pero no necesariamente por ha. La decision usa el margen total.")
    if (lo_o > 0) != (lo_c > 0) or (hi_o < 0) != (hi_c < 0):
        print("AVISO: el IC con las observaciones y el IC por clima no coinciden; manda el IC por clima.")
    for nombre, p in (("base", pb), ("alternativo", pa)):
        print(f"probabilidad de siembra a tiempo del {nombre}: {p:.1%}  "
              f"({'cumple' if p >= P['p_min_a_tiempo'] else 'NO cumple'} el minimo de {P['p_min_a_tiempo']:.0%})")

    seccion("7. Validacion del modelo (al estilo del TP 2.2)")
    metas = {}
    for p in pares:
        metas[(p["campaña"], p["replica"])] = (p["base"]["semillaMadurez"], p["base"]["gddMeta"])
    valores = [g for _, g in metas.values()]
    semillas = {s for s, _ in metas.values()}
    a, mo, bb = P["gdd_min"], P["gdd_moda"], P["gdd_max"]
    media_t = (a + mo + bb) / 3.0
    sd_t = math.sqrt((a * a + bb * bb + mo * mo - a * bb - a * mo - bb * mo) / 18.0)
    mm = mean(valores)
    zm = (mm - media_t) / (sd_t / math.sqrt(len(valores)))
    print(f"meta de madurez: {len(valores)} metas con {len(semillas)} semillas distintas; media {mm:.1f} "
          f"(teorica {media_t:.1f}), desvio {stdev(valores):.1f} (teorico {sd_t:.1f}), z = {zm:+.2f}  "
          f"{'OK' if abs(zm) < 1.96 else 'REVISAR'}")
    if len(semillas) < len(valores):
        print("AVISO: hay metas repetidas; las semillas de madurez no son todas distintas")
    # las pasadas sin terminar (cosecha que no cierra en el año) traen NA en sus contadores: cuentan como 0
    horas = sum((f["s_trabajando"] or 0.0) + (f["c_trabajando"] or 0.0) for p in pares for f in [p["base"]] + p["alt"])
    fallas = sum((f["s_fallas"] or 0.0) + (f["c_fallas"] or 0.0) for p in pares for f in [p["base"]] + p["alt"])
    esperadas_f = horas / P["mtbf_horas"]
    zf = (fallas - esperadas_f) / math.sqrt(esperadas_f) if esperadas_f > 0 else float("nan")
    print(f"fallas: {fallas:.0f} observadas contra {esperadas_f:.1f} esperadas (horas trabajadas / MTBF = "
          f"{pts(horas)} h / {P['mtbf_horas']:.0f} h), z = {zf:+.2f}  {'OK' if abs(zf) < 1.96 else 'REVISAR'}")

    seccion("8. Medidas de desempeño de Law y Kelton (adaptadas: servidor = tren, clientes = lotes)")
    print("b(n): fraccion de la labor en que el recurso esta ocupado. q(n): lotes en cola, promedio en el tiempo.")
    print("d(n): demora media de un lote en la cola [dias]. T(n): duracion de la labor [dias]. IC 95% con t de Student.")
    medidas = [("b_maquina", "b(n) maquina", 1), ("b_carro", "b(n) carro", 1), ("b_camion", "b(n) camion", 1),
               ("q", "q(n) [lotes]", 0), ("d", "d(n) [dias]", 0), ("T", "T(n) [dias]", 0)]
    lk = {}
    for pasada, nombre_p in (("s", "SIEMBRA"), ("c", "COSECHA")):
        validos = [p for p in pares if p["lk_base_" + pasada] and p["lk_alt_" + pasada]]
        print(f"\n{nombre_p}: {len(validos)} pares con la labor cerrada en los dos sistemas"
              + (f" ({len(pares) - len(validos)} excluidos: la labor no cerro antes del 30/9)" if len(validos) < len(pares) else ""))
        print(f"{'':<16}{'base':>24}{'alternativo':>26}{'diferencia (alt - base)':>34}")
        for clave, nombre, es_pct in medidas:
            b = [p["lk_base_" + pasada][clave] for p in validos]
            a = [p["lk_alt_" + pasada][clave] for p in validos]
            dif = [y - x for x, y in zip(b, a)]
            rb, ra, rd = ic_media(b, alfa), ic_media(a, alfa), ic_media(dif, alfa)
            lk[(pasada, clave)] = (rb, ra)
            f = (lambda v: f"{100 * v:5.1f}%") if es_pct else (lambda v: f"{v:6.2f}")
            print(f"{nombre:<16}{f(rb[0]):>9} [{f(rb[3])};{f(rb[4])}]{f(ra[0]):>10} [{f(ra[3])};{f(ra[4])}]"
                  f"{f(rd[0]):>13} [{f(rd[3])};{f(rd[4])}]")
        # ley de Little por tren: q * T = n * d al cerrar la labor (control de la adaptacion)
        err = max(abs(t["q"] * t["T"] - t["n"] * t["d"]) for p in validos
                  for s in (p["lk_base_" + pasada], p["lk_alt_" + pasada]) for t in s["trenes"])
        print(f"ley de Little por tren, max |q*T - n*d| = {err:.2e} lotes-dia")
        lk[pasada] = validos

    seccion("9. Horizonte de la simulacion: terminante, sin estado estable")
    for pasada, nombre_p in (("s", "siembra"), ("c", "cosecha")):
        for sis in ("base", "alt"):
            todos = [p["lk_" + sis + "_" + pasada] for p in pares]
            ok = [s for s in todos if s]
            if not ok:
                continue
            Ts = [s["T"] for s in ok]
            print(f"{nombre_p:<8} {sis:<5}: la labor cierra en {len(ok)} de {len(todos)} replicas; "
                  f"T(n) entre {min(Ts):.1f} y {max(Ts):.1f} dias (media {mean(Ts):.1f}); al cerrar Q(t) = 0")
    print("Cada corrida es una campaña con un evento de fin natural (cosecha cerrada, o el 30/9 si no cierra) y\n"
          "condiciones iniciales fijas (1/10, campo sin sembrar). Q(t) arranca en n - 1 y baja a 0 en cada labor: el\n"
          "sistema no tiene un regimen estacionario, asi que no se descarta un periodo de calentamiento y se usan\n"
          "replicas independientes (docs/CAMBIOS-2026-10.md, seccion 19).")

    if salida:
        os.makedirs(salida, exist_ok=True)
        with open(os.path.join(salida, "diferencias_por_par.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["campaña", "replica", "margen_base", "margen_alt", "diferencia", "media_acumulada",
                        "a_tiempo_base", "a_tiempo_alt"])
            for i, p in enumerate(pares):
                w.writerow([p["campaña"], p["replica"], round(p["res_base"]["margen"], 2),
                            round(p["res_alt"]["margen"], 2), round(d[i], 2), round(acum[i], 2),
                            int(p["res_base"]["a_tiempo"]), int(p["res_alt"]["a_tiempo"])])
        print(f"\nescrito: {os.path.join(salida, 'diferencias_por_par.csv')}")
        graficos(salida, d, acum, ic_media(d, alfa), ic_media(d_clima, alfa), lk, pares, sintetico)


def graficos(salida, d, acum, ic_obs, ic_clima, lk, pares, sintetico):
    """Graficos SVG del informe (herramientas/graficos_svg.py)."""
    import graficos_svg as g
    carpeta = g.asegurar(os.path.join(salida, "graficos"))
    marca = " [DATOS SINTETICOS]" if sintetico else ""
    hechos = [
        g.media_acumulada(os.path.join(carpeta, "1_media_acumulada.svg"), acum, ic_obs[3], ic_obs[4], ic_obs[0]),
        g.histograma(os.path.join(carpeta, "2_histograma_diferencias.svg"), d,
                     (ic_obs[0], ic_obs[3], ic_obs[4]), (ic_clima[0], ic_clima[3], ic_clima[4])),
    ]
    for i, (pasada, nombre) in enumerate((("s", "siembra"), ("c", "cosecha"))):
        panel = []
        for clave, titulo, unidad, factor, dec in (("b_maquina", "b(n) máquina", "%", 100, 1),
                                                   ("b_carro", "b(n) carro", "%", 100, 1),
                                                   ("q", "q(n)", "lotes", 1, 1), ("d", "d(n)", "días", 1, 1)):
            rb, ra = lk[(pasada, clave)]
            panel.append((titulo, unidad, tuple(factor * rb[k] for k in (0, 3, 4)),
                          tuple(factor * ra[k] for k in (0, 3, 4)), dec))
        hechos.append(g.barras_pareadas(
            os.path.join(carpeta, f"{3 + i}_law_kelton_{nombre}.svg"),
            f"Medidas de Law y Kelton en la {nombre}{marca}",
            f"Media de {len(lk[pasada])} réplicas con IC 95%. Servidor = tren de máquinas, clientes = lotes.", panel))
    for i, (pasada, nombre) in enumerate((("s", "siembra"), ("c", "cosecha"))):
        validos = lk[pasada]
        xb, yb = cola_promedio([p["lk_base_" + pasada] for p in validos])
        xa, ya = cola_promedio([p["lk_alt_" + pasada] for p in validos])
        n = max(len(xb), len(xa))
        xs = [k * 0.5 for k in range(n)]
        yb += [0.0] * (n - len(yb))
        ya += [0.0] * (n - len(ya))
        marcas = [(45, "15/11")] if pasada == "s" else []
        hechos.append(g.curvas(
            os.path.join(carpeta, f"{5 + i}_cola_{nombre}.svg"),
            f"Q(t) promedio en la {nombre}: la cola se vacía, no hay estado estable{marca}",
            f"Lotes que todavía no entraron en servicio, promedio de {len(validos)} réplicas. "
            f"t = días desde la apertura de la labor" + (" (1/10)." if pasada == "s" else " (madurez)."),
            xs, [("Base: 12 lotes, 1 tren", yb, g.AZUL), ("Alternativo C: 18 lotes, 2 trenes", ya, g.NARANJA)],
            "días desde la apertura de la labor", "lotes en cola", marcas=marcas, dec_y=0))
    for h in hechos:
        print("escrito:", h)


# =============================================================================================
# Datos sinteticos para probar el script
# =============================================================================================
def generar_demo(ruta, semilla=1):
    """Escribe un CSV con la estructura del barrido y numeros inventados (plausibles, no del modelo)."""
    rng = random.Random(semilla)
    P = PARAMETROS
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(COLUMNAS)
        for camp in range(20):
            atraso_clima = rng.uniform(0, 14)       # el clima del año atrasa la siembra
            for rep in range(1, 6):
                meta = rng.triangular(P["gdd_min"], P["gdd_max"], P["gdd_moda"])
                for tren in (1, 2):
                    for lotes in (9, 12):
                        dias_lote = 3.4 + rng.uniform(-0.3, 0.3)
                        ds, t = [], 2.0 + atraso_clima * 0.3
                        for _ in range(lotes):
                            t += dias_lote + rng.expovariate(1 / 0.6)
                            ds.append(t)
                        fin_s = int(ds[-1])
                        madurez = fin_s + rng.uniform(125, 150)
                        dc, t = [], madurez + 2
                        for _ in range(lotes):
                            t += 5.2 + rng.expovariate(1 / 0.8)
                            dc.append(t)
                        fin_c = int(dc[-1]) if dc[-1] < 364 else -1
                        fila = [lotes, 1, camp, rep, tren, rep + 5 * camp + 100 * (tren - 1), rep + 5 * camp,
                                round(meta, 3), fin_s, int(madurez), fin_c]
                        for pasada, n in (("s", lotes), ("c", lotes)):
                            trab = n * 16.6
                            fall = sum(1 for _ in range(int(trab * 10)) if rng.random() < 0.001)
                            rep_h = fall * rng.uniform(2, 5)
                            sin_piso = rng.choice([0, 31, 62])
                            esp = 0.0 if pasada == "s" else rng.uniform(15, 35)
                            tras = 0.6
                            det = trab * 4.0
                            jorn = det - rep_h - sin_piso - esp - tras
                            valores = [trab, det, 0 if pasada == "s" else n * 6, 5, fall, rep_h, rep_h, 0.0, jorn,
                                       sin_piso, esp, tras, 0.0] + [rng.uniform(0, 500) for _ in range(6)] + \
                                      [rng.uniform(0, 500) for _ in range(4)]
                            fila += [repr(float(x)) for x in valores]
                        fila.append("|".join(f"{x:.2f}" for x in ds))
                        fila.append("|".join(f"{x:.2f}" for x in dc) if fin_c != -1 else "|".join(["NA"] * lotes))
                        w.writerow(fila)


# =============================================================================================
def main():
    ap = argparse.ArgumentParser(description="Analiza el barrido de ParametersVariation (base contra alternativo C).")
    ap.add_argument("csv", nargs="?", default=CSV_POR_DEFECTO)
    ap.add_argument("--salida", help="carpeta donde escribir diferencias_por_par.csv")
    ap.add_argument("--param", action="append", default=[], metavar="NOMBRE=VALOR",
                    help="cambia un parametro de PARAMETROS (sensibilidad)")
    ap.add_argument("--filas", type=int, default=400, help="filas esperadas en el CSV (por defecto 400)")
    ap.add_argument("--demo", action="store_true", help="prueba el script con datos SINTETICOS")
    a = ap.parse_args()

    P = dict(PARAMETROS)
    for kv in a.param:
        k, _, v = kv.partition("=")
        if k not in P:
            sys.exit(f"parametro desconocido: {k}. Los validos: {', '.join(P)}")
        P[k] = float(v)
    ruta = a.csv
    if a.demo:
        ruta = os.path.join(tempfile.gettempdir(), "barrido_sintetico.csv")
        generar_demo(ruta)
    filas = leer_csv(ruta)
    indice, avisos = controlar(filas, a.filas, P)
    pares, incompletos = armar_pares(indice, P)
    evaluar_pares(pares, P)
    informe(pares, incompletos, avisos, P, a.filas, a.salida, sintetico=a.demo)


if __name__ == "__main__":
    main()
