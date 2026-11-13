#!/usr/bin/env python3
"""Genera el informe visual (HTML autocontenido) de Experiencia del Cliente de la región.

Uso:
  python3 informe_html.py <resumen.json> <salida.html> [--red-pdf datos/cx_red_pdf.csv]
        [--reclasif datos/reclasif_X.json --xlsx Comentarios.xlsx] [--historial datos/cx_historial.csv]

Para PDF: node html_a_pdf.js <salida.html>  (Playwright/Chromium)
"""
import json, sys, csv, html
from pathlib import Path

A = sys.argv
res = json.load(open(A[1], encoding="utf-8"))
OUT = Path(A[2])
OBJ = res["objetivo"]


def opt(flag):
    return A[A.index(flag) + 1] if flag in A else None


def f(x, d=1):
    return "–" if x is None else f"{x:.{d}f}".replace(".", ",")


def e(s):
    return html.escape(str(s))


fecha = "/".join(res["fecha_datos"].split("-")[::-1])
R, RED = res["region"], res["red"]
est = sorted(res["estaciones"].items(), key=lambda kv: kv[1]["puesto"])
arriba = sum(1 for _, m in est if (m["ycx_acum"] or 0) >= OBJ)

# ---------- reclasificación ----------
rec_por_est, rec_impacto = {}, None
if opt("--reclasif") and opt("--xlsx"):
    import pandas as pd
    prop = json.load(open(opt("--reclasif"), encoding="utf-8"))
    df = pd.read_excel(opt("--xlsx"), sheet_name="DatosCX", dtype={"ID": str}, usecols=["ID", "Apies", "Sentimiento"])
    df["ID"] = df.ID.astype(str)
    df["s"] = df.Sentimiento.str.lower()
    sel = df[df.ID.isin(prop)].drop_duplicates("ID")
    rec_por_est = sel.Apies.astype(int).astype(str).value_counts().to_dict()
    nuevo = df.copy()
    for i, (s, t, _m) in prop.items():
        m = nuevo.ID == i
        nuevo.loc[m, "s"] = "_x" if (s == "Inválido" or t in ("Digital", "Precios")) else s.lower()
    nuevo = nuevo[nuevo.s != "_x"]
    yc = lambda s: ((s == "positivo").sum() - (s == "negativo").sum()) / len(s) * 100
    rec_impacto = {}
    for a in res["estaciones"]:
        d0, d1 = df[df.Apies == int(a)].s, nuevo[nuevo.Apies == int(a)].s
        rec_impacto[a] = (yc(d0), yc(d1))
    reg = [int(a) for a in res["estaciones"]]
    rec_impacto["REG"] = (yc(df[df.Apies.isin(reg)].s), yc(nuevo[nuevo.Apies.isin(reg)].s))
    tipos = {"Positivo": 0, "Inválido": 0, "Digital": 0, "Tópico": 0}
    for s, t, _m in prop.values():
        if s == "Positivo": tipos["Positivo"] += 1
        elif s == "Inválido": tipos["Inválido"] += 1
        elif t == "Digital": tipos["Digital"] += 1
        else: tipos["Tópico"] += 1

red_pdf = []
if opt("--red-pdf") and Path(opt("--red-pdf")).exists():
    red_pdf = list(csv.DictReader(open(opt("--red-pdf"), encoding="utf-8")))

# ---------- SVG: ranking ----------
def svg_ranking():
    W, rowh, left, right = 760, 24, 170, 70
    H = rowh * len(est) + 40
    x0, x1 = left, W - right
    lo, hi = 40, 100
    X = lambda v: x0 + (max(lo, min(hi, v)) - lo) / (hi - lo) * (x1 - x0)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Ranking Y-CX acumulado por estación">']
    for t in range(40, 101, 10):
        g.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="18" y2="{H-14}" class="grid"/>'
                 f'<text x="{X(t):.1f}" y="12" class="ax" text-anchor="middle">{t}%</text>')
    for i, (a, m) in enumerate(est):
        y = 22 + i * rowh
        v, v30 = m["ycx_acum"] or 0, m["ycx_30d"]
        bajo = v < OBJ
        g.append(f'<g class="row"><title>{e(m["nombre"])} — acumulado {f(v)}% · 30 días {f(v30)}% · '
                 f'{m["comentarios"]} comentarios ({m["negativos"]} negativos)</title>'
                 f'<rect x="0" y="{y-2}" width="{W}" height="{rowh}" class="hit"/>'
                 f'<text x="{left-8}" y="{y+13}" class="lbl" text-anchor="end">{m["puesto"]}. {e(m["nombre"].replace("ACA ", ""))}</text>'
                 f'<rect x="{x0}" y="{y+3}" width="{max(2, X(v)-x0):.1f}" height="14" rx="3" class="bar{" low" if bajo else ""}"/>'
                 f'<text x="{W-6}" y="{y+14}" class="val" text-anchor="end">{f(v)}%</text>')
        if v30 is not None:
            g.append(f'<circle cx="{X(v30):.1f}" cy="{y+10}" r="4.5" class="dot"/>')
        g.append("</g>")
    g.append(f'<line x1="{X(OBJ):.1f}" x2="{X(OBJ):.1f}" y1="16" y2="{H-10}" class="obj"/>'
             f'<text x="{X(OBJ)+4:.1f}" y="{H-2}" class="ax objt">objetivo {OBJ}%</text>')
    g.append("</svg>")
    return "".join(g)


# ---------- SVG: barras agrupadas canales ----------
def svg_canales():
    ch = [("GOOGLE", "Google"), ("APP", "App YPF"), ("NPS", "NPS"), ("QR", "QR")]
    W, H, l, b, t = 520, 230, 40, 30, 16
    lo, hi = 0, 100
    Y = lambda v: t + (hi - max(lo, min(hi, v))) / (hi - lo) * (H - t - b)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Y-CX por canal, región contra red">']
    for v in range(0, 101, 20):
        g.append(f'<line x1="{l}" x2="{W-8}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                 f'<text x="{l-6}" y="{Y(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
    g.append(f'<line x1="{l}" x2="{W-8}" y1="{Y(OBJ):.1f}" y2="{Y(OBJ):.1f}" class="obj"/>')
    gw = (W - l - 8) / 4
    for i, (k, n) in enumerate(ch):
        cx = l + gw * i + gw / 2
        for j, (src, cls) in enumerate([(R, "s1"), (RED, "s2")]):
            v = src["canales"][k]["ycx"] or 0
            x = cx - 30 + j * 32
            yv = Y(max(v, 0))
            g.append(f'<g><title>{n} — {"Región" if j == 0 else "Red ACA"}: {f(v)}% ({src["canales"][k]["comentarios"]} comentarios)</title>'
                     f'<rect x="{x:.1f}" y="{yv:.1f}" width="28" height="{max(1, Y(0)-yv):.1f}" rx="3" class="{cls}"/>'
                     f'<text x="{x+14:.1f}" y="{yv-4:.1f}" class="val" text-anchor="middle">{f(v,0)}</text></g>')
        g.append(f'<text x="{cx:.1f}" y="{H-10}" class="lbl" text-anchor="middle">{n}</text>')
    g.append("</svg>")
    return "".join(g)


# ---------- SVG: tópicos negativos ----------
def svg_topicos():
    tops = sorted(R["topicos_neg_acum"].items(), key=lambda kv: -kv[1])
    W, rowh, left = 520, 30, 170
    H = rowh * len(tops) + 10
    mx = max(v for _, v in tops)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Comentarios negativos por tópico en la región">']
    for i, (t, v) in enumerate(tops):
        y = 6 + i * rowh
        w = v / mx * (W - left - 130)
        v30 = R["topicos_neg_30d"].get(t, 0)
        g.append(f'<g><title>{e(t)}: {v} negativos en el año, {v30} en los últimos 30 días</title>'
                 f'<text x="{left-8}" y="{y+15}" class="lbl" text-anchor="end">{e(t)}</text>'
                 f'<rect x="{left}" y="{y+3}" width="{max(2,w):.1f}" height="16" rx="3" class="s1"/>'
                 f'<text x="{left+w+6:.1f}" y="{y+16}" class="val">{v} <tspan class="muted">({v30} en 30 d)</tspan></text></g>')
    g.append("</svg>")
    return "".join(g)


# ---------- SVG: evolución red ----------
def svg_evol():
    if len(red_pdf) < 2:
        return ""
    W, H, l, b, t = 520, 200, 40, 34, 16
    vals = [float(r[k]) for r in red_pdf for k in ("ycx_acum", "ycx_30d")]
    lo, hi = min(vals + [OBJ]) - 1, max(vals + [OBJ]) + 1
    n = len(red_pdf)
    X = lambda i: l + 20 + i * (W - l - 50) / (n - 1)
    Y = lambda v: t + (hi - v) / (hi - lo) * (H - t - b)
    g = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Evolución semanal del Y-CX de la red ACA">']
    for v in range(int(lo) + 1, int(hi) + 1):
        g.append(f'<line x1="{l}" x2="{W-8}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                 f'<text x="{l-6}" y="{Y(v)+4:.1f}" class="ax" text-anchor="end">{v}</text>')
    g.append(f'<line x1="{l}" x2="{W-8}" y1="{Y(OBJ):.1f}" y2="{Y(OBJ):.1f}" class="obj"/>'
             f'<text x="{W-10}" y="{Y(OBJ)-4:.1f}" class="ax objt" text-anchor="end">objetivo {OBJ}%</text>')
    for k, cls in (("ycx_acum", "l1"), ("ycx_30d", "l2")):
        pts = " ".join(f"{X(i):.1f},{Y(float(r[k])):.1f}" for i, r in enumerate(red_pdf))
        g.append(f'<polyline points="{pts}" class="{cls}" fill="none"/>')
        for i, r in enumerate(red_pdf):
            g.append(f'<circle cx="{X(i):.1f}" cy="{Y(float(r[k])):.1f}" r="4" class="{cls}p"><title>'
                     f'{"Acumulado" if k=="ycx_acum" else "30 días"} al {"/".join(r["fecha_reporte"].split("-")[::-1][:2])}: {f(float(r[k]),2)}%</title></circle>')
    for i, r in enumerate(red_pdf):
        g.append(f'<text x="{X(i):.1f}" y="{H-12}" class="ax" text-anchor="middle">{"/".join(r["fecha_reporte"].split("-")[::-1][:2])}</text>')
    last = red_pdf[-1]
    g.append(f'<text x="{X(n-1)+6:.1f}" y="{Y(float(last["ycx_acum"]))+14:.1f}" class="val">{f(float(last["ycx_acum"]))}</text>')
    g.append(f'<text x="{X(n-1)+6:.1f}" y="{Y(float(last["ycx_30d"]))-6:.1f}" class="val">{f(float(last["ycx_30d"]))}</text>')
    g.append("</svg>")
    return "".join(g)


# ---------- tabla estaciones ----------
def celda(v, n=None):
    if v is None or n == 0:
        return '<td class="num muted">–</td>'
    cls = "ok" if v >= OBJ else "bad"
    ico = "" if v >= OBJ else '<span class="ico" aria-label="debajo del objetivo">▼</span>'
    tip = f' title="{n} comentarios"' if n is not None else ""
    return f'<td class="num {cls}"{tip}>{ico}{f(v)}</td>'


filas = []
for a, m in est:
    top = max(m["topicos_neg_acum"].items(), key=lambda kv: kv[1])[0] if m["topicos_neg_acum"] else "–"
    dif = None if m["ycx_30d"] is None or m["ycx_30d_anterior"] is None else m["ycx_30d"] - m["ycx_30d_anterior"]
    tend = "–" if dif is None else ("▲" if dif >= 3 else ("▼" if dif <= -3 else "="))
    tcls = "" if dif is None else ("up" if dif >= 3 else ("down" if dif <= -3 else "muted"))
    c = m["canales"]
    imp = ""
    if rec_impacto and rec_por_est.get(a):
        d0, d1 = rec_impacto[a]
        imp = f'{rec_por_est[a]} <span class="muted">(+{f(d1-d0)} pp)</span>'
    filas.append(
        f'<tr><td class="num muted">{m["puesto"]}</td><td>{e(m["nombre"].replace("ACA ", ""))} <span class="muted">{a}</span></td>'
        f'{celda(m["ycx_acum"])}{celda(m["ycx_30d"])}<td class="num {tcls}" title="30 días anteriores: {f(m["ycx_30d_anterior"])}%">{tend}</td>'
        f'{celda(c["GOOGLE"]["ycx"], c["GOOGLE"]["comentarios"])}{celda(c["APP"]["ycx"], c["APP"]["comentarios"])}'
        f'{celda(c["NPS"]["ycx"], c["NPS"]["comentarios"])}{celda(c["QR"]["ycx"], c["QR"]["comentarios"])}'
        f'<td class="num">{m["comentarios"]}</td><td class="num">{m["negativos_30d"]}</td>'
        f'<td class="num">{m["faltan_positivos_80"] or "–"}</td><td class="wrap">{e(top)}</td><td class="num">{imp or "–"}</td></tr>')

# ---------- alertas ----------
cerca = [m for _, m in est if (m["ycx_acum"] or 0) < OBJ and (m["faltan_positivos_80"] or 999) <= 40]
bajando = [m for _, m in est if m["ycx_30d"] is not None and m["ycx_30d_anterior"] is not None
           and m["ycx_30d"] - m["ycx_30d_anterior"] <= -8 and m["comentarios_30d"] >= 10]
lejos = [m for _, m in est if (m["faltan_positivos_80"] or 0) > 150]
mejor30 = [m for _, m in est if m["ycx_30d"] is not None and m["ycx_30d_anterior"] is not None
           and m["ycx_30d"] - m["ycx_30d_anterior"] >= 15 and (m["ycx_acum"] or 0) < OBJ]
nm = lambda L: ", ".join(e(m["nombre"].replace("ACA ", "")) for m in L) or "ninguna"
alertas = [
    ("warn", "A un paso del 80%", ", ".join(f'{e(m["nombre"].replace("ACA ", ""))} (faltan ~{m["faltan_positivos_80"]} positivos)' for m in cerca) or "ninguna"),
    ("crit", "Bajando fuerte en el último mes", ", ".join(f'{e(m["nombre"].replace("ACA ", ""))} ({f(m["ycx_30d_anterior"],0)}% → {f(m["ycx_30d"],0)}%)' for m in bajando) or "ninguna"),
    ("good", "Debajo del 80% pero mejorando", ", ".join(f'{e(m["nombre"].replace("ACA ", ""))} ({f(m["ycx_30d_anterior"],0)}% → {f(m["ycx_30d"],0)}% en 30 d)' for m in mejor30) or "ninguna"),
    ("crit", "Brecha grande (más de 150 positivos para llegar)", nm(lejos)),
]
ICON = {"warn": "!", "crit": "▼", "good": "▲"}

dif_red = R["ycx_acum"] - RED["ycx_acum"]
t30 = R["ycx_30d"] - (R["ycx_30d_anterior"] or R["ycx_30d"])
rec_html = ""
if rec_impacto:
    d0, d1 = rec_impacto["REG"]
    rec_html = (f'<section><h2>Pedido de reclasificación a YPF</h2><p class="lead">Encontramos <b>{sum(rec_por_est.values())} comentarios</b> mal clasificados: '
                f'{tipos["Positivo"]} elogios marcados como negativos, {tipos["Inválido"]} que no son sobre la estación, '
                f'{tipos["Digital"]} quejas de la App (tópico Digital) y {tipos["Tópico"]} con el tópico equivocado. '
                f'Si YPF los acepta, la región pasaría de <b>{f(d0,2)}%</b> a <b>{f(d1,2)}%</b>.</p><div class="chips">'
                + "".join(f'<span class="chip">{e(res["estaciones"][a]["nombre"].replace("ACA ", ""))}: {f(rec_impacto[a][0])}% → <b>{f(rec_impacto[a][1])}%</b></span>'
                          for a in sorted(rec_por_est, key=lambda a: -(rec_impacto[a][1]-rec_impacto[a][0])) if rec_impacto[a][1]-rec_impacto[a][0] >= 0.3)
                + "</div></section>")

evol = svg_evol()
evol_html = ""
if evol:
    p, u = red_pdf[0], red_pdf[-1]
    evol_html = (f'<div class="card"><h3>Red ACA, semana a semana</h3><p class="muted small">Del PDF de YPF de cada semana. '
                 f'Acumulado: {f(float(p["ycx_acum"]),2)}% → {f(float(u["ycx_acum"]),2)}% · 30 días: {f(float(p["ycx_30d"]),2)}% → {f(float(u["ycx_30d"]),2)}%</p>'
                 f'<div class="legend"><span><i class="k l1k"></i>Acumulado</span><span><i class="k l2k"></i>30 días</span></div>{evol}</div>')

HTML = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Informe CX Región</title>
<style>
:root{{color-scheme:light;--bg:#f6f6f4;--surface:#fcfcfb;--line:#e4e3df;--grid:#ecebe7;--t1:#0b0b0b;--t2:#52514e;--t3:#7a7975;
--s1:#2a78d6;--s2:#eb6834;--good:#0ca30c;--goodtxt:#006300;--goodbg:#e7f5e7;--crit:#d03b3b;--crittxt:#b02a2a;--critbg:#fbeaea;--warn:#fab219;--warnbg:#fff4dc;--accent:#7fcbcf}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--line:#2e2e2b;--grid:#262624;--t1:#f0efec;--t2:#c3c2b7;--t3:#93928b;
--s1:#3987e5;--s2:#d95926;--goodtxt:#5fcf5f;--goodbg:#15301a;--crittxt:#f08a8a;--critbg:#3a1a1a;--warnbg:#3a2e10}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#121211;--surface:#1a1a19;--line:#2e2e2b;--grid:#262624;--t1:#f0efec;--t2:#c3c2b7;--t3:#93928b;
--s1:#3987e5;--s2:#d95926;--goodtxt:#5fcf5f;--goodbg:#15301a;--crittxt:#f08a8a;--critbg:#3a1a1a;--warnbg:#3a2e10}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--t1);font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}}
.wrap{{max-width:1080px;margin:0 auto;padding:24px 16px 48px}}
header{{border-left:6px solid var(--accent);padding:4px 0 4px 14px;margin-bottom:20px}}
h1{{font-size:24px;margin:0}}h2{{font-size:18px;margin:28px 0 10px}}h3{{font-size:15px;margin:0 0 4px}}
.muted{{color:var(--t3)}}.small{{font-size:12px}}.lead{{color:var(--t2);max-width:820px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}
.kpi{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px}}
.kpi .n{{font-size:30px;font-weight:700;line-height:1.1;margin-top:4px}}.kpi .l{{color:var(--t2);font-size:12px;text-transform:uppercase;letter-spacing:.03em}}
.kpi .d{{font-size:12px;color:var(--t2);margin-top:4px}}
.grid2{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,480px),1fr));gap:14px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px;overflow:hidden}}
svg{{width:100%;height:auto;display:block}}
svg .grid{{stroke:var(--grid);stroke-width:1}}svg .ax{{fill:var(--t3);font-size:11px}}svg .lbl{{fill:var(--t2);font-size:12px}}
svg .val{{fill:var(--t1);font-size:11.5px;font-weight:600}}svg .muted{{fill:var(--t3);font-weight:400}}
svg .bar,svg .s1{{fill:var(--s1)}}svg .bar.low{{fill:var(--s1);opacity:.45}}svg .s2{{fill:var(--s2)}}
svg .dot{{fill:var(--s2);stroke:var(--surface);stroke-width:2}}svg .obj{{stroke:var(--t1);stroke-width:1.5;stroke-dasharray:4 3}}svg .objt{{fill:var(--t2)}}
svg .hit{{fill:transparent}}svg .row:hover .hit{{fill:var(--grid)}}
svg .l1{{stroke:var(--s1);stroke-width:2}}svg .l2{{stroke:var(--s2);stroke-width:2}}svg .l1p{{fill:var(--s1);stroke:var(--surface);stroke-width:2}}svg .l2p{{fill:var(--s2);stroke:var(--surface);stroke-width:2}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--t2);margin:6px 0 8px}}.legend span{{display:inline-flex;align-items:center;gap:6px}}
.k{{display:inline-block;width:14px;height:10px;border-radius:2px}}.k.bk{{background:var(--s1)}}.k.bl{{background:var(--s1);opacity:.45}}.k.dk{{width:10px;height:10px;border-radius:50%;background:var(--s2)}}
.k.l1k{{background:var(--s1);height:3px}}.k.l2k{{background:var(--s2);height:3px}}.k.ok{{border:1px dashed var(--t1);background:none;width:0;height:12px}}
.alerts{{display:grid;gap:10px}}.alert{{display:flex;gap:10px;align-items:flex-start;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 14px}}
.badge{{flex:none;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700;color:#fff}}
.badge.warn{{background:var(--warn);color:#3a2a00}}.badge.crit{{background:var(--crit)}}.badge.good{{background:var(--good)}}
.tbl{{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}}th,td{{padding:6px 7px;border-bottom:1px solid var(--line);text-align:left;white-space:nowrap}}
th{{position:sticky;top:0;background:var(--surface);color:var(--t2);font-weight:600;font-size:11.5px}}
td.wrap{{white-space:normal;min-width:110px}}td.num,th.num{{text-align:right;font-variant-numeric:tabular-nums}}
td.ok{{color:var(--goodtxt)}}td.bad{{color:var(--crittxt);background:var(--critbg)}}.ico{{font-size:9px;margin-right:4px}}
td.up{{color:var(--goodtxt)}}td.down{{color:var(--crittxt)}}
.chips{{display:flex;flex-wrap:wrap;gap:8px}}.chip{{background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:12.5px}}
footer{{margin-top:32px;color:var(--t3);font-size:11.5px}}
@media print{{.grid2{{grid-template-columns:1fr 1fr 1fr}}.rank svg{{max-width:600px;margin:0 auto}}.kpi .n{{font-size:24px}}h2{{margin:14px 0 8px}}.pb{{break-before:page}}table{{font-size:11px}}th,td{{padding:3px 5px}}body{{background:#fff}}.wrap{{padding:0}}.card,.kpi,.alert,.tbl{{break-inside:avoid}}section{{break-inside:auto}}th{{position:static}}}}
</style></head><body><div class="wrap">
<header><h1>Experiencia del Cliente (Y-CX) — Región Jesús Bruna</h1>
<div class="muted">25 estaciones ACA · datos al {fecha} · fuente: base de comentarios CX de YPF · objetivo {OBJ}%</div></header>

<section class="kpis">
<div class="kpi"><div class="l">Y-CX región (año)</div><div class="n">{f(R["ycx_acum"])}%</div><div class="d">{"▲" if dif_red>=0 else "▼"} {f(abs(dif_red))} pp sobre la red ACA ({f(RED["ycx_acum"])}%)</div></div>
<div class="kpi"><div class="l">Últimos 30 días</div><div class="n">{f(R["ycx_30d"])}%</div><div class="d">{"▲" if t30>=0 else "▼"} {f(abs(t30))} pp contra los 30 días anteriores</div></div>
<div class="kpi"><div class="l">Estaciones en objetivo</div><div class="n">{arriba} <span class="muted" style="font-size:18px">de {len(est)}</span></div><div class="d">{len(est)-arriba} debajo del {OBJ}%</div></div>
<div class="kpi"><div class="l">Comentarios en el año</div><div class="n">{R["comentarios"]:,}</div><div class="d">{R["negativos"]} negativos · {R["negativos_30d"]} en los últimos 30 días</div></div>
</section>

<h2>Ranking de estaciones</h2>
<div class="card rank"><div class="legend"><span><i class="k bk"></i>Y-CX acumulado (en objetivo)</span><span><i class="k bl"></i>Debajo del {OBJ}%</span><span><i class="k dk"></i>Últimos 30 días</span><span><i class="k ok"></i>Objetivo {OBJ}%</span></div>
{svg_ranking()}<p class="muted small">Pasá el mouse por cada fila para ver el detalle. El eje empieza en 40% para que se distingan las diferencias.</p></div>

<h2 class="pb">Alertas</h2>
<div class="alerts">{"".join(f'<div class="alert"><span class="badge {k}" aria-hidden="true">{ICON[k]}</span><div><b>{t}</b><br><span class="lead">{v}</span></div></div>' for k,t,v in alertas)}</div>

<h2>Dónde se pierden puntos</h2>
<div class="grid2">
<div class="card"><h3>Y-CX por canal</h3><p class="muted small">La línea punteada marca el objetivo de {OBJ}%.</p><div class="legend"><span><i class="k" style="background:var(--s1)"></i>Región</span><span><i class="k" style="background:var(--s2)"></i>Red ACA</span></div>{svg_canales()}</div>
<div class="card"><h3>Comentarios negativos por tópico (región, año)</h3><p class="muted small">Entre paréntesis, los de los últimos 30 días.</p>{svg_topicos()}</div>
{evol_html}
</div>

<h2 class="pb">Detalle por estación</h2>
<div class="tbl"><table><thead><tr><th class="num">#</th><th>Estación</th><th class="num">Acum.</th><th class="num">30 d</th><th class="num">Tend.</th>
<th class="num">Google</th><th class="num">App</th><th class="num">NPS</th><th class="num">QR</th><th class="num">Coment.</th><th class="num">Neg. 30 d</th>
<th class="num">Faltan p/{OBJ}%</th><th>Tópico con más negativos</th><th class="num">Reclasif. (impacto)</th></tr></thead><tbody>{"".join(filas)}</tbody></table></div>
<p class="muted small">▼ en rojo = debajo del {OBJ}%. "Tend." compara los últimos 30 días contra los 30 anteriores (▲/▼ = 3 pp o más). "Faltan" = comentarios positivos que harían falta, sin nuevos negativos, para llegar al {OBJ}% acumulado.</p>

{rec_html}

<footer>Y-CX = % positivos − % negativos sobre el total de comentarios (Google, App YPF, NPS y QR); el cálculo coincide con el PDF de YPF para la red ACA ({f(RED["ycx_acum"],2)}%). Documento con información YPF-Privado: uso interno.</footer>
</div></body></html>"""
OUT.write_text(HTML, encoding="utf-8")
print(f"OK -> {OUT}")
