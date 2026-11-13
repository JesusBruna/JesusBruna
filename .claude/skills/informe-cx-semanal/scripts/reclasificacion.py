#!/usr/bin/env python3
"""Arma la planilla de reclasificación para mandar a YPF y estima el impacto en el Y-CX.

Uso:
  python3 reclasificacion.py <Comentarios CX red ACA.xlsx> <propuestas.json> <salida.xlsx>

propuestas.json: {"<ID>": ["<Nuevo sentimiento>", "<Nuevo tópico>", "<Motivo>"], ...}
Valores válidos (hoja "Hoja1" del Excel de YPF):
  sentimiento: Positivo | Negativo | Inválido
  tópico: Atención al cliente | Imagen e instalaciones | Tiempo de espera | Sanitarios |
          Calidad de productos | Stock de productos | Problemáticas críticas | Digital | Precios
"Digital" y "Precios" no cuentan en el Y-CX de la estación (el PDF dice "Sin Digital ni variables eco y Bancos").

La salida conserva las columnas del archivo de YPF y trae solo las filas propuestas, con las
tres últimas columnas completas. Imprime el impacto estimado por estación.
"""
import json, sys
from pathlib import Path
import pandas as pd

AQUI = Path(__file__).resolve().parent
EST = {int(k): v for k, v in json.load(open(AQUI.parent / "references" / "estaciones.json", encoding="utf-8"))["estaciones"].items()}
SENT = {"Positivo", "Negativo", "Inválido"}
TOP = {"Atención al cliente", "Imagen e instalaciones", "Tiempo de espera", "Sanitarios", "Calidad de productos",
       "Stock de productos", "Problemáticas críticas", "Digital", "Precios"}
FUERA = {"Digital", "Precios"}


def ycx(s):
    return ((s == "positivo").sum() - (s == "negativo").sum()) / len(s) * 100 if len(s) else float("nan")


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    xlsx, prop, salida = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8")), sys.argv[3]
    for i, (s, t, _m) in prop.items():
        assert s in SENT, f"{i}: sentimiento inválido {s}"
        assert t in TOP, f"{i}: tópico inválido {t}"
    df = pd.read_excel(xlsx, sheet_name="DatosCX", dtype={"ID": str})
    hoja1 = pd.read_excel(xlsx, sheet_name="Hoja1", header=None)
    df["ID"] = df.ID.astype(str).str.strip()
    faltan = [i for i in prop if i not in set(df.ID)]
    if faltan:
        print("ATENCION: IDs no encontrados:", faltan)
    sel = df[df.ID.isin(prop)].drop_duplicates("ID").copy()
    cols = list(df.columns)
    sel[cols[-3]] = sel.ID.map(lambda i: prop[i][0])
    sel[cols[-2]] = sel.ID.map(lambda i: prop[i][1])
    sel[cols[-1]] = sel.ID.map(lambda i: prop[i][2])
    with pd.ExcelWriter(salida, engine="openpyxl") as xw:
        sel[cols].to_excel(xw, sheet_name="DatosCX", index=False)
        hoja1.to_excel(xw, sheet_name="Hoja1", index=False, header=False)
        ws = xw.sheets["DatosCX"]
        for c, w in zip("ABCDEFGHIJK", [16, 8, 12, 9, 11, 22, 70, 18, 16, 22, 70]):
            ws.column_dimensions[c].width = w

    # impacto estimado
    df["s"] = df.Sentimiento.str.lower()
    nuevo = df.copy()
    for i, (s, t, _m) in prop.items():
        m = nuevo.ID == i
        if s == "Inválido" or t in FUERA:
            nuevo.loc[m, "s"] = "_fuera"
        else:
            nuevo.loc[m, "s"] = s.lower()
    nuevo = nuevo[nuevo.s != "_fuera"]
    print(f"{len(sel)} comentarios propuestos -> {salida}")
    for a in sorted(set(sel.Apies)):
        antes, desp = ycx(df[df.Apies == a].s), ycx(nuevo[nuevo.Apies == a].s)
        print(f"  {EST.get(int(a), a):<28} {antes:6.2f}% -> {desp:6.2f}%  ({desp - antes:+.2f} pp)")
    reg = list(EST)
    antes, desp = ycx(df[df.Apies.isin(reg)].s), ycx(nuevo[nuevo.Apies.isin(reg)].s)
    print(f"  {'REGION':<28} {antes:6.2f}% -> {desp:6.2f}%  ({desp - antes:+.2f} pp)")


if __name__ == "__main__":
    main()
