#!/usr/bin/env python3
"""Analiza el Excel "Comentarios CX red ACA.xlsx" (base de comentarios Y-CX de YPF)
para las estaciones de la región definidas en references/estaciones.json.

Uso:
  python3 analizar_cx.py <Comentarios CX red ACA.xlsx> <carpeta_salida> [--historial datos/cx_historial.csv]

Genera en <carpeta_salida>:
  resumen.json            métricas de la red ACA, de la región y de cada estación
  negativos_region.csv    comentarios negativos de la región (todo el año), con días de antigüedad
  Informe CX Region <dd-mm>.xlsx   informe para el usuario (ranking, tópicos, canales, negativos)
y, si se pasa --historial, agrega una fila por estación al CSV histórico (evolución semanal).

Y-CX = % positivos - % negativos sobre todos los comentarios (cuadra con el PDF de YPF).
"Y-CX 30 días" = comentarios con Fecha > (última fecha del archivo - 30 días).
"""
import json, sys, os, re
from pathlib import Path
import pandas as pd

AQUI = Path(__file__).resolve().parent
CFG = json.load(open(AQUI.parent / "references" / "estaciones.json", encoding="utf-8"))
EST = {int(k): v for k, v in CFG["estaciones"].items()}
OBJ = CFG.get("objetivo_ycx", 80)
CANALES = ["GOOGLE", "APP", "NPS", "QR"]


def limpiar_topico(t):
    return re.sub(r"^[^\wÁÉÍÓÚÑáéíóúñ]+", "", str(t)).strip()


def ycx(s):
    n = len(s)
    if n == 0:
        return None
    return round(((s == "positivo").sum() - (s == "negativo").sum()) / n * 100, 2)


def faltan_positivos(s, obj=OBJ):
    """Comentarios positivos adicionales (sin nuevos negativos) para llegar al objetivo."""
    T = len(s); P = (s == "positivo").sum(); N = (s == "negativo").sum()
    if T == 0:
        return None
    x = (obj / 100 * T - P + N) / (1 - obj / 100)
    return max(0, int(-(-x // 1)))


def metricas(d, fin, nombre=None):
    s = d.Sentimiento
    w30 = d[d.Fecha > fin - pd.Timedelta(days=30)]
    w60 = d[(d.Fecha > fin - pd.Timedelta(days=60)) & (d.Fecha <= fin - pd.Timedelta(days=30))]
    m = {
        "nombre": nombre,
        "comentarios": int(len(d)),
        "negativos": int((s == "negativo").sum()),
        "ycx_acum": ycx(s),
        "comentarios_30d": int(len(w30)),
        "negativos_30d": int((w30.Sentimiento == "negativo").sum()),
        "ycx_30d": ycx(w30.Sentimiento),
        "ycx_30d_anterior": ycx(w60.Sentimiento),
        "faltan_positivos_80": faltan_positivos(s),
        "canales": {},
        "topicos_neg_acum": {},
        "topicos_neg_30d": {},
        "topicos_ycx_acum": {},
    }
    for c in CANALES:
        dc = d[d.Canal == c]
        m["canales"][c] = {"comentarios": int(len(dc)), "ycx": ycx(dc.Sentimiento),
                           "comentarios_30d": int((dc.Fecha > fin - pd.Timedelta(days=30)).sum())}
    neg = d[s == "negativo"]
    m["topicos_neg_acum"] = neg.Top.value_counts().to_dict()
    m["topicos_neg_30d"] = w30[w30.Sentimiento == "negativo"].Top.value_counts().to_dict()
    for t, g in d.groupby("Top"):
        m["topicos_ycx_acum"][t] = {"comentarios": int(len(g)), "ycx": ycx(g.Sentimiento)}
    return m


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    xlsx, out = sys.argv[1], Path(sys.argv[2])
    hist = None
    if "--historial" in sys.argv:
        hist = Path(sys.argv[sys.argv.index("--historial") + 1])
    out.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(xlsx, sheet_name="DatosCX")
    df["Fecha"] = pd.to_datetime(df.Fecha)
    df["Sentimiento"] = df.Sentimiento.str.lower().str.strip()
    df["Top"] = df.Topico.map(limpiar_topico)
    fin = df.Fecha.max()

    faltan = sorted(set(EST) - set(df.Apies.unique()))
    reg = df[df.Apies.isin(EST)].copy()
    reg["Estacion"] = reg.Apies.map(EST)

    res = {
        "fecha_datos": fin.strftime("%Y-%m-%d"),
        "objetivo": OBJ,
        "estaciones_sin_datos": [EST[a] for a in faltan],
        "red": metricas(df, fin, "Red ACA"),
        "region": metricas(reg, fin, CFG.get("region", "Región")),
        "estaciones": {},
    }
    for a, nom in EST.items():
        d = reg[reg.Apies == a]
        m = metricas(d, fin, nom)
        # comentarios negativos recientes (60 días) para los mails
        n = d[(d.Sentimiento == "negativo") & (d.Fecha > fin - pd.Timedelta(days=60))].sort_values("Fecha", ascending=False)
        m["neg_recientes"] = [
            {"id": str(r.ID), "fecha": r.Fecha.strftime("%d/%m"), "canal": r.Canal, "topico": r.Top, "texto": str(r.Comentario)[:400]}
            for r in n.itertuples()]
        p = d[(d.Sentimiento == "positivo") & (d.Fecha > fin - pd.Timedelta(days=30))]
        p = p[p.Comentario.astype(str).str.len().between(40, 300)].sort_values("Fecha", ascending=False)
        m["pos_recientes"] = [{"fecha": r.Fecha.strftime("%d/%m"), "canal": r.Canal, "texto": str(r.Comentario)} for r in p.head(3).itertuples()]
        res["estaciones"][str(a)] = m

    # ranking
    orden = sorted(res["estaciones"].items(), key=lambda kv: (kv[1]["ycx_acum"] is None, -(kv[1]["ycx_acum"] or 0)))
    for i, (a, m) in enumerate(orden, 1):
        m["puesto"] = i
    json.dump(res, open(out / "resumen.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=int)

    negs = reg[reg.Sentimiento == "negativo"].copy()
    negs["dias"] = (fin - negs.Fecha).dt.days
    negs[["ID", "Apies", "Estacion", "Fecha", "Canal", "Top", "Comentario", "Contacto", "dias"]].sort_values(
        "Fecha", ascending=False).to_csv(out / "negativos_region.csv", index=False)

    escribir_excel(res, reg, fin, out)

    if hist is not None:
        hist.parent.mkdir(parents=True, exist_ok=True)
        filas = []
        for a, m in list(res["estaciones"].items()) + [("REGION", res["region"]), ("RED", res["red"])]:
            filas.append({"fecha_datos": res["fecha_datos"], "apies": a, "estacion": m["nombre"],
                          "ycx_acum": m["ycx_acum"], "ycx_30d": m["ycx_30d"], "comentarios": m["comentarios"],
                          "negativos": m["negativos"], "comentarios_30d": m["comentarios_30d"],
                          "negativos_30d": m["negativos_30d"],
                          **{f"ycx_{c.lower()}": m["canales"][c]["ycx"] for c in CANALES}})
        nuevo = pd.DataFrame(filas)
        if hist.exists():
            viejo = pd.read_csv(hist, dtype={"apies": str})
            viejo = viejo[viejo.fecha_datos != res["fecha_datos"]]
            nuevo = pd.concat([viejo, nuevo], ignore_index=True)
        nuevo.to_csv(hist, index=False)

    print(f"Datos al {fin:%d/%m/%Y}. Red ACA Y-CX {res['red']['ycx_acum']}% | Región {res['region']['ycx_acum']}% "
          f"(30d {res['region']['ycx_30d']}%). Estaciones sin datos: {res['estaciones_sin_datos'] or 'ninguna'}")


def escribir_excel(res, reg, fin, out):
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter
    path = out / f"Informe CX Region {fin:%d-%m}.xlsx"
    rk = []
    for a, m in sorted(res["estaciones"].items(), key=lambda kv: kv[1]["puesto"]):
        top = max(m["topicos_neg_acum"].items(), key=lambda kv: kv[1])[0] if m["topicos_neg_acum"] else "-"
        rk.append({"Puesto": m["puesto"], "APIES": int(a), "Estación": m["nombre"],
                   "Y-CX acumulado %": m["ycx_acum"], "Y-CX 30 días %": m["ycx_30d"],
                   "Y-CX 30 días anteriores %": m["ycx_30d_anterior"],
                   "Comentarios año": m["comentarios"], "Negativos año": m["negativos"],
                   "Comentarios 30d": m["comentarios_30d"], "Negativos 30d": m["negativos_30d"],
                   **{f"{c} Y-CX %": m["canales"][c]["ycx"] for c in CANALES},
                   **{f"{c} coment.": m["canales"][c]["comentarios"] for c in CANALES},
                   "Positivos que faltan p/80%": m["faltan_positivos_80"],
                   "Tópico con más negativos": top})
    rk = pd.DataFrame(rk)
    tops = sorted({t for m in res["estaciones"].values() for t in m["topicos_neg_acum"]})
    tp = []
    for a, m in sorted(res["estaciones"].items(), key=lambda kv: kv[1]["puesto"]):
        fila = {"Estación": m["nombre"]}
        for t in tops:
            fila[f"{t} (año)"] = m["topicos_neg_acum"].get(t, 0)
        for t in tops:
            fila[f"{t} (30d)"] = m["topicos_neg_30d"].get(t, 0)
        tp.append(fila)
    tp = pd.DataFrame(tp)
    negs = reg[reg.Sentimiento == "negativo"].sort_values(["Fecha"], ascending=False)
    negs = negs[["Estacion", "Apies", "Fecha", "Canal", "Top", "Comentario", "Contacto", "ID"]].rename(
        columns={"Estacion": "Estación", "Top": "Tópico"})
    negs["Fecha"] = negs.Fecha.dt.date
    kpi = []
    for nombre, m in [("Región", res["region"]), ("Red ACA", res["red"])]:
        kpi.append({"Ámbito": nombre, "Y-CX acumulado %": m["ycx_acum"], "Y-CX 30 días %": m["ycx_30d"],
                    "Y-CX 30 días anteriores %": m["ycx_30d_anterior"], "Comentarios año": m["comentarios"],
                    "Negativos año": m["negativos"], "Comentarios 30d": m["comentarios_30d"],
                    "Negativos 30d": m["negativos_30d"],
                    **{f"{c} Y-CX %": m["canales"][c]["ycx"] for c in CANALES},
                    "Positivos que faltan p/80%": m["faltan_positivos_80"]})
    kpi = pd.DataFrame(kpi)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        kpi.to_excel(xw, sheet_name="Resumen", index=False, startrow=2)
        rk.to_excel(xw, sheet_name="Ranking estaciones", index=False)
        tp.to_excel(xw, sheet_name="Negativos por tópico", index=False)
        negs.to_excel(xw, sheet_name="Comentarios negativos", index=False)
        ws = xw.sheets["Resumen"]
        ws["A1"] = f"Experiencia del Cliente (Y-CX) – datos al {fin:%d/%m/%Y} – objetivo {OBJ}%"
        ws["A1"].font = Font(bold=True, size=13)
        hdr = PatternFill("solid", fgColor="7FCBCF")
        for name in xw.sheets:
            sh = xw.sheets[name]
            r0 = 3 if name == "Resumen" else 1
            for cell in sh[r0]:
                cell.font = Font(bold=True); cell.fill = hdr
                cell.alignment = Alignment(wrap_text=True, vertical="center")
            sh.freeze_panes = sh.cell(row=r0 + 1, column=1)
            for i, col in enumerate(sh.iter_cols(min_row=r0, max_row=min(sh.max_row, 200)), 1):
                w = max(len(str(c.value or "")) for c in col)
                sh.column_dimensions[get_column_letter(i)].width = min(max(10, w + 2), 60 if name != "Comentarios negativos" else 90)
        rojo, verde = PatternFill("solid", fgColor="F8CBAD"), PatternFill("solid", fgColor="C6EFCE")
        sh = xw.sheets["Ranking estaciones"]
        for row in sh.iter_rows(min_row=2):
            for cell in row:
                h = sh.cell(1, cell.column).value or ""
                if "Y-CX" in h and isinstance(cell.value, (int, float)):
                    cell.fill = verde if cell.value >= OBJ else rojo
    return path


if __name__ == "__main__":
    main()
