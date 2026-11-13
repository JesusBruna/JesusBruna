#!/usr/bin/env python3
"""Genera un mail (texto plano) por estación con su situación de Experiencia del Cliente (Y-CX).

Uso:
  python3 mails_cx.py <resumen.json> <carpeta_salida> [--reclasif propuestas.json] [--xlsx Comentarios.xlsx]

--reclasif y --xlsx (juntos) agregan la línea "pedimos a YPF reclasificar N comentarios" en las
estaciones que tienen propuestas.
Sale un .txt por estación (primera línea = "Asunto: ...") y TODOS.txt.
"""
import json, sys
from pathlib import Path


def f(x, d=1):
    return "s/d" if x is None else f"{x:.{d}f}".replace(".", ",")


CONSEJO = {
    "Tiempo de espera": "reforzar personal en horas pico, habilitar todos los surtidores y cajas disponibles y agilizar el cobro (App YPF / QR)",
    "Atención al cliente": "saludo y trato cordial en cada atención, ofrecer los servicios (aire, agua, parabrisas) y repasar con el equipo los casos puntuales",
    "Sanitarios": "cumplir la planilla de limpieza, reponer papel y jabón y mantener los baños abiertos y señalizados",
    "Imagen e instalaciones": "limpieza de playa y tienda, iluminación y reparar lo que esté roto",
    "Stock de productos": "revisar los faltantes que se repiten (combustibles y productos de tienda) y anticipar pedidos",
    "Calidad de productos": "controlar la calidad de café y comidas y la temperatura de lo que se sirve",
    "Problemáticas críticas": "tratar uno por uno los casos sensibles (cobros, maltrato, seguridad) y darles respuesta",
}


def mail(a, m, res, n_reclasif=0, excluir=()):
    obj = res["objetivo"]
    fecha = "/".join(res["fecha_datos"].split("-")[::-1][:2])
    nom = m["nombre"]
    tot = len(res["estaciones"])
    L = [f"Asunto: Experiencia del Cliente (Y-CX) – {nom} – datos al {fecha}", "",
         f"Hola equipo de {nom},", "",
         "Les comparto cómo viene la estación en Experiencia del Cliente (Y-CX), el indicador con el que YPF "
         "mide los comentarios de los clientes en Google, App YPF, encuestas NPS y QR. "
         f"El objetivo es {obj}%.", "",
         f"CÓMO VIENEN (datos al {fecha})"]
    est = "arriba" if (m["ycx_acum"] or 0) >= obj else "debajo"
    L.append(f"• Y-CX acumulado del año: {f(m['ycx_acum'])}% ({est} del objetivo de {obj}%). Puesto {m['puesto']} de {tot} en la región "
             f"(región {f(res['region']['ycx_acum'])}%, red ACA {f(res['red']['ycx_acum'])}%).")
    t30, ant = m["ycx_30d"], m["ycx_30d_anterior"]
    if t30 is not None:
        tend = ""
        if ant is not None:
            dif = t30 - ant
            tend = " — mejorando" if dif >= 3 else (" — bajando" if dif <= -3 else " — estable")
            tend = f" (los 30 días anteriores: {f(ant)}%{tend})"
        L.append(f"• Últimos 30 días: {f(t30)}%{tend}.")
    L.append(f"• Comentarios en el año: {m['comentarios']} ({m['negativos']} negativos). "
             f"Últimos 30 días: {m['comentarios_30d']} comentarios, {m['negativos_30d']} negativo{'' if m['negativos_30d']==1 else 's'}.")
    if m["comentarios_30d"] < 15:
        L.append("• Ojo: entran pocos comentarios por mes, así que cada comentario negativo pesa mucho en el resultado.")
    L += ["", "POR CANAL (acumulado del año)"]
    nombres = {"GOOGLE": "Google", "APP": "App YPF", "NPS": "Encuesta NPS", "QR": "QR en la estación"}
    flojos = []
    for c in ["GOOGLE", "APP", "NPS", "QR"]:
        cm = m["canales"][c]
        if cm["comentarios"] == 0:
            L.append(f"• {nombres[c]}: sin comentarios.")
            continue
        L.append(f"• {nombres[c]}: {f(cm['ycx'])}% ({cm['comentarios']} comentario{'' if cm['comentarios']==1 else 's'})")
        if cm["comentarios"] >= 10 and cm["ycx"] < obj:
            flojos.append(nombres[c])
    if flojos:
        L.append(f"  → Debajo del {obj}%: {', '.join(flojos)}.")

    L += ["", "DÓNDE PONER FOCO"]
    tops = sorted(m["topicos_neg_acum"].items(), key=lambda kv: -kv[1])[:3]
    if not tops:
        L.append("• No tienen comentarios negativos en el año. ¡Excelente!")
    for t, n in tops:
        n30 = m["topicos_neg_30d"].get(t, 0)
        extra = f", {n30} en los últimos 30 días" if n30 else ""
        L.append(f"• {t}: {n} comentarios negativos en el año{extra}. Sugerencia: {CONSEJO.get(t, 'revisar los casos con el equipo')}.")
    negs = [c for c in m.get("neg_recientes", []) if c.get("id") not in excluir][:3]
    if negs:
        L += ["", "Algunos comentarios negativos recientes:"]
        for c in negs:
            txt = " ".join(c["texto"].split())
            if len(txt) > 220:
                txt = txt[:217].rsplit(" ", 1)[0] + "…"
            L.append(f"  - {c['fecha']} ({c['canal']}, {c['topico']}): \"{txt}\"")

    L += ["", "PRÓXIMOS PASOS"]
    falt = m["faltan_positivos_80"]
    if falt and falt > 0:
        if falt <= 150:
            L.append(f"• Para llegar al {obj}% necesitan sumar unos {falt} comentarios positivos sin nuevos negativos.")
        else:
            L.append(f"• La brecha al {obj}% es grande (harían falta unos {falt} comentarios positivos sin nuevos negativos): "
                     "lo más efectivo es cortar las causas de los negativos y, a la vez, sumar comentarios de clientes conformes.")
    elif t30 is not None and t30 < obj and m["comentarios_30d"] >= 15:
        L.append(f"• Están arriba del {obj}%, pero los últimos 30 días bajaron al {f(t30)}%: hay que cortar los negativos "
                 "que están entrando antes de que afecten el acumulado.")
    elif (m["ycx_acum"] or 0) < obj + 2:
        L.append(f"• Están apenas arriba del {obj}%: un par de comentarios negativos los deja debajo. Hay que sostenerlo "
                 "y sumar comentarios de clientes conformes.")
    else:
        L.append(f"• Están arriba del {obj}%: el desafío es sostenerlo, sin descuidar los comentarios negativos que entren.")
    L.append("• Pedir a los clientes conformes que califiquen la carga en la App YPF y que dejen su reseña en Google (QR visible en playa y tienda).")
    L.append("• Responder las reseñas de Google, sobre todo las negativas, con un mensaje cordial y una solución.")
    if n_reclasif:
        L.append(f"• Detectamos {n_reclasif} comentario{'s' if n_reclasif > 1 else ''} de la estación mal clasificado{'s' if n_reclasif > 1 else ''} "
                 "y estamos pidiendo a YPF su revisión.")
    pos = m.get("pos_recientes", [])[:2]
    if pos:
        L += ["", "LO QUE DESTACAN LOS CLIENTES"]
        for c in pos:
            L.append(f"  - {c['fecha']} ({c['canal']}): \"{' '.join(c['texto'].split())}\"")
    L += ["", "Cualquier duda me consultan.", "", "Saludos,", "Jesús Bruna"]
    return "\n".join(L)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    res = json.load(open(sys.argv[1], encoding="utf-8"))
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    rec = {}
    prop = {}
    if "--reclasif" in sys.argv and "--xlsx" in sys.argv:
        import pandas as pd
        prop = json.load(open(sys.argv[sys.argv.index("--reclasif") + 1], encoding="utf-8"))
        df = pd.read_excel(sys.argv[sys.argv.index("--xlsx") + 1], sheet_name="DatosCX", dtype={"ID": str},
                           usecols=["ID", "Apies"])
        df = df[df.ID.astype(str).isin(prop)].drop_duplicates("ID")
        rec = df.Apies.astype(int).astype(str).value_counts().to_dict()
    todos = []
    for a, m in sorted(res["estaciones"].items(), key=lambda kv: kv[1]["puesto"]):
        txt = mail(a, m, res, rec.get(a, 0), set(prop))
        nombre = m["nombre"].replace("ACA ", "").replace(" ", "_").replace("(", "").replace(")", "").replace(".", "")
        (out / f"{a}_{nombre}.txt").write_text(txt, encoding="utf-8")
        todos.append(txt)
    (out / "TODOS.txt").write_text(("\n\n" + "=" * 70 + "\n\n").join(todos), encoding="utf-8")
    print(f"{len(todos)} mails en {out}")


if __name__ == "__main__":
    main()
