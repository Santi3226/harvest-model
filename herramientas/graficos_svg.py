"""Graficos SVG estaticos para el informe, solo con la biblioteca estandar.

Los usa analizar_barrido.py (opcion --salida). Paleta: la de referencia de la guia de visualizacion
(base = azul, alternativo = naranja, el par por defecto validado para daltonismo); texto en tinta
neutra, grilla y ejes recesivos, una sola escala por grafico.
"""
import math
import os

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
GRILLA = "#e4e3df"
AZUL = "#2a78d6"       # sistema base (o serie unica)
NARANJA = "#eb6834"    # sistema alternativo
BANDA = "#cde2fb"      # banda del IC (escalon claro del azul)
FUENTE = "font-family:Segoe UI,Helvetica,Arial,sans-serif"


def _esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _num(x, dec=0):
    """Numero en formato argentino: punto de miles, coma decimal."""
    t = f"{x:,.{dec}f}"
    return t.replace(",", "_").replace(".", ",").replace("_", ".")


def _ticks(lo, hi, n=5):
    """Marcas 'redondas' que cubren [lo, hi]."""
    if hi == lo:
        hi = lo + 1
    paso = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(paso))
    for f in (1, 2, 2.5, 5, 10):
        if f * mag >= paso:
            paso = f * mag
            break
    a = math.floor(lo / paso) * paso
    b = math.ceil(hi / paso) * paso
    out, v = [], a
    while v <= b + paso * 1e-9:
        out.append(round(v, 10))
        v += paso
    return out


class Lienzo:
    def __init__(self, ancho, alto, titulo, subtitulo=""):
        self.w, self.h = ancho, alto
        self.partes = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho}" height="{alto}" '
                       f'viewBox="0 0 {ancho} {alto}" role="img" aria-label="{_esc(titulo)}">',
                       f'<rect width="{ancho}" height="{alto}" fill="{SUPERFICIE}"/>',
                       f'<text x="24" y="30" style="{FUENTE};font-size:16px;font-weight:600" fill="{TINTA}">{_esc(titulo)}</text>']
        if subtitulo:
            self.partes.append(f'<text x="24" y="50" style="{FUENTE};font-size:12px" fill="{TINTA_2}">{_esc(subtitulo)}</text>')

    def add(self, s):
        self.partes.append(s)

    def texto(self, x, y, t, tam=11, color=TINTA_2, anchor="start", peso=400):
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" style="{FUENTE};font-size:{tam}px;'
                 f'font-weight:{peso}" fill="{color}">{_esc(t)}</text>')

    def guardar(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(self.partes + ["</svg>"]))
        return ruta


class Ejes:
    """Area de datos con escalas lineales, grilla horizontal y rotulos."""

    def __init__(self, lz, x0, y0, ancho, alto, xr, yr, xt=None, yt=None, xlab="", ylab="", dec_y=0, dec_x=0):
        self.lz, self.x0, self.y0, self.a, self.h = lz, x0, y0, ancho, alto
        self.yt = yt if yt is not None else _ticks(*yr)
        self.xt = xt if xt is not None else _ticks(*xr)
        self.ymin, self.ymax = min(self.yt[0], yr[0]), max(self.yt[-1], yr[1])
        self.xmin, self.xmax = xr
        for v in self.yt:
            y = self.Y(v)
            lz.add(f'<line x1="{x0}" x2="{x0 + ancho}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRILLA}" stroke-width="1"/>')
            lz.texto(x0 - 8, y + 4, _num(v, dec_y), anchor="end")
        for v in self.xt:
            if self.xmin - 1e-9 <= v <= self.xmax + 1e-9:
                lz.texto(self.X(v), y0 + alto + 18, _num(v, dec_x), anchor="middle")
        lz.add(f'<line x1="{x0}" x2="{x0 + ancho}" y1="{y0 + alto}" y2="{y0 + alto}" stroke="{TINTA_2}" stroke-width="1"/>')
        if xlab:
            lz.texto(x0 + ancho / 2, y0 + alto + 38, xlab, anchor="middle")
        if ylab:
            lz.add(f'<text transform="translate({x0 - 52},{y0 + alto / 2}) rotate(-90)" text-anchor="middle" '
                   f'style="{FUENTE};font-size:11px" fill="{TINTA_2}">{_esc(ylab)}</text>')

    def X(self, v):
        return self.x0 + (v - self.xmin) / ((self.xmax - self.xmin) or 1) * self.a

    def Y(self, v):
        return self.y0 + self.h - (v - self.ymin) / ((self.ymax - self.ymin) or 1) * self.h

    def linea(self, xs, ys, color, ancho=2, guiones=None, escalon=False):
        pts = []
        for i, (x, y) in enumerate(zip(xs, ys)):
            if escalon and i:
                pts.append(f"{self.X(x):.1f},{self.Y(ys[i - 1]):.1f}")
            pts.append(f"{self.X(x):.1f},{self.Y(y):.1f}")
        d = f' stroke-dasharray="{guiones}"' if guiones else ""
        self.lz.add(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="{ancho}"'
                    f' stroke-linejoin="round" stroke-linecap="round"{d}/>')

    def hlinea(self, v, color, guiones="4 4", rotulo=None, lado="end"):
        y = self.Y(v)
        self.lz.add(f'<line x1="{self.x0}" x2="{self.x0 + self.a}" y1="{y:.1f}" y2="{y:.1f}" stroke="{color}" '
                    f'stroke-width="1.5" stroke-dasharray="{guiones}"/>')
        if rotulo:
            x = self.x0 + self.a - 4 if lado == "end" else self.x0 + 4
            self.lz.texto(x, y - 5, rotulo, anchor=lado, color=TINTA)

    def banda(self, lo, hi, color=BANDA):
        y1, y2 = self.Y(hi), self.Y(lo)
        self.lz.add(f'<rect x="{self.x0}" y="{y1:.1f}" width="{self.a}" height="{y2 - y1:.1f}" fill="{color}" opacity="0.7"/>')


def leyenda(lz, x, y, items):
    for i, (nombre, color) in enumerate(items):
        xx = x + i * 170
        lz.add(f'<rect x="{xx}" y="{y - 9}" width="12" height="12" rx="2" fill="{color}"/>')
        lz.texto(xx + 18, y + 1, nombre, tam=12, color=TINTA)


# =============================================================================================
def media_acumulada(ruta, acum, lo, hi, media):
    """Media acumulada de la diferencia contra el numero de observaciones (como en el TP 3)."""
    n = len(acum)
    lz = Lienzo(760, 420, "Convergencia de la diferencia de margen (alternativo - base)",
                f"Media acumulada par a par, US$ por campaña. Banda: IC 95% con las {n} observaciones.")
    vals = acum + [lo, hi, 0]
    ej = Ejes(lz, 90, 75, 640, 270, (1, n), (min(vals), max(vals)), xlab="observaciones (pares campaña, réplica)",
              ylab="media acumulada [US$]")
    ej.banda(lo, hi)
    ej.hlinea(0, TINTA_2, rotulo="0", lado="start")
    ej.linea(list(range(1, n + 1)), acum, AZUL)
    ej.hlinea(media, AZUL, guiones="2 3", rotulo=f"media final {_num(media)}")
    return lz.guardar(ruta)


def histograma(ruta, valores, ic_obs, ic_clima, ancho_clase=None):
    """Histograma de las diferencias par a par con la media y los dos IC."""
    lo_v, hi_v = min(valores), max(valores)
    if ancho_clase is None:
        k = max(5, int(math.ceil(1 + math.log2(len(valores)))))   # Sturges
        ancho_clase = _ticks(0, (hi_v - lo_v) / k, 4)[1]
    a = math.floor(lo_v / ancho_clase) * ancho_clase
    bordes = [a]
    while bordes[-1] <= hi_v:
        bordes.append(bordes[-1] + ancho_clase)
    cuentas = [sum(1 for v in valores if bordes[i] <= v < bordes[i + 1]) for i in range(len(bordes) - 1)]
    lz = Lienzo(760, 420, "Distribución de la diferencia de margen (alternativo - base)",
                f"{len(valores)} pares, clases de {_num(ancho_clase)} US$. Líneas: media e IC 95% por clima (el que manda).")
    ej = Ejes(lz, 90, 75, 640, 270, (bordes[0], bordes[-1]), (0, max(cuentas)), xlab="diferencia de margen [US$ por campaña]",
              ylab="frecuencia")
    for i, c in enumerate(cuentas):
        if not c:
            continue
        x1, x2 = ej.X(bordes[i]) + 1, ej.X(bordes[i + 1]) - 1
        y = ej.Y(c)
        lz.add(f'<path d="M{x1:.1f},{ej.Y(0):.1f} V{y + 3:.1f} Q{x1:.1f},{y:.1f} {x1 + 3:.1f},{y:.1f} H{x2 - 3:.1f} '
               f'Q{x2:.1f},{y:.1f} {x2:.1f},{y + 3:.1f} V{ej.Y(0):.1f} Z" fill="{AZUL}"/>')
    m, lo, hi = ic_clima
    for v, g in ((lo, "4 4"), (hi, "4 4"), (m, None)):
        x = ej.X(v)
        dash = f' stroke-dasharray="{g}"' if g else ""
        lz.add(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{ej.y0}" y2="{ej.y0 + ej.h}" stroke="{TINTA}" stroke-width="1.5"{dash}/>')
    # rotulos arriba a la derecha, lejos de las lineas
    xr = ej.x0 + ej.a - 4
    lz.texto(xr, ej.y0 + 12, f"media {_num(m)} US$, IC 95% por clima [{_num(lo)} ; {_num(hi)}]", color=TINTA, anchor="end")
    lz.texto(xr, ej.y0 + 28, f"IC con las observaciones: [{_num(ic_obs[1])} ; {_num(ic_obs[2])}]", anchor="end")
    return lz.guardar(ruta)


def barras_pareadas(ruta, titulo, subtitulo, paneles):
    """Paneles chicos (uno por medida, cada uno con su escala): base y alternativo con su IC 95%.
    paneles = [(nombre, unidad, (m, lo, hi) base, (m, lo, hi) alternativo, decimales)]"""
    np_ = len(paneles)
    ancho_p = 230
    lz = Lienzo(60 + np_ * (ancho_p + 30), 400, titulo, subtitulo)
    leyenda(lz, 24, 76, [("Base: 12 lotes, 1 tren", AZUL), ("Alternativo C: 18 lotes, 2 trenes", NARANJA)])
    for i, (nombre, unidad, b, a, dec) in enumerate(paneles):
        x0 = 70 + i * (ancho_p + 30)
        tope = max(b[2], a[2], b[0], a[0]) * 1.15 or 1
        ej = Ejes(lz, x0, 120, ancho_p - 40, 220, (0, 1), (0, tope), xt=[], dec_y=dec)
        lz.texto(x0 + (ancho_p - 40) / 2, 112, f"{nombre} [{unidad}]", tam=12, color=TINTA, anchor="middle", peso=600)
        for j, (serie, color, rot) in enumerate(((b, AZUL, "base"), (a, NARANJA, "alternativo"))):
            cx = ej.X(0.28 + j * 0.44)
            w = 46
            y = ej.Y(serie[0])
            lz.add(f'<path d="M{cx - w / 2:.1f},{ej.Y(0):.1f} V{y + 4:.1f} Q{cx - w / 2:.1f},{y:.1f} {cx - w / 2 + 4:.1f},{y:.1f} '
                   f'H{cx + w / 2 - 4:.1f} Q{cx + w / 2:.1f},{y:.1f} {cx + w / 2:.1f},{y + 4:.1f} V{ej.Y(0):.1f} Z" fill="{color}"/>')
            ylo, yhi = ej.Y(serie[1]), ej.Y(serie[2])
            lz.add(f'<path d="M{cx:.1f},{ylo:.1f} V{yhi:.1f} M{cx - 7:.1f},{ylo:.1f} H{cx + 7:.1f} M{cx - 7:.1f},{yhi:.1f} '
                   f'H{cx + 7:.1f}" stroke="{TINTA}" stroke-width="1.5" fill="none"/>')
            lz.texto(cx, yhi - 6, _num(serie[0], dec), color=TINTA, anchor="middle")
            lz.texto(cx, ej.Y(0) + 16, rot, anchor="middle")
    return lz.guardar(ruta)


def curvas(ruta, titulo, subtitulo, xs, series, xlab, ylab, marcas=(), dec_y=0, escalon=False):
    """Lineas sobre un eje comun. series = [(nombre, ys, color)]; marcas = [(x, rotulo)] verticales."""
    todas = [v for _, ys, _ in series for v in ys]
    lz = Lienzo(760, 440, titulo, subtitulo)
    leyenda(lz, 24, 76, [(n, c) for n, _, c in series])
    ej = Ejes(lz, 90, 100, 640, 260, (xs[0], xs[-1]), (0, max(todas)), xlab=xlab, ylab=ylab, dec_y=dec_y)
    for x, rot in marcas:
        px = ej.X(x)
        lz.add(f'<line x1="{px:.1f}" x2="{px:.1f}" y1="{ej.y0}" y2="{ej.y0 + ej.h}" stroke="{TINTA_2}" stroke-width="1" stroke-dasharray="4 4"/>')
        lz.texto(px + 5, ej.y0 + 12, rot)
    for nombre, ys, color in series:
        ej.linea(xs, ys, color, escalon=escalon)
    return lz.guardar(ruta)


def asegurar(carpeta):
    os.makedirs(carpeta, exist_ok=True)
    return carpeta
