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
    if x is None:
        return "s/d"
    if abs(x - round(x)) < 0.05:
        return str(int(round(x)))
    return f"{x:.{d}f}".replace(".", ",")


CONSEJO = {
    "Tiempo de espera": "que en los horarios pico haya más gente en la playa y estén habilitados todos los surtidores y cajas",
    "Atención al cliente": "repasar con los chicos el saludo, el trato y ofrecer siempre los servicios (aire, agua, parabrisas)",
    "Sanitarios": "que se cumpla la planilla de limpieza, que no falte papel ni jabón y que los baños estén abiertos",
    "Imagen e instalaciones": "mantener limpia la playa y la tienda y arreglar lo que esté roto",
    "Stock de productos": "revisar los faltantes que se repiten y anticipar los pedidos",
    "Calidad de productos": "controlar la calidad del café y las comidas",
    "Problemáticas críticas": "ver uno por uno los casos de cobros, maltrato o seguridad y darles respuesta",
}

TEMA = {
    "Tiempo de espera": "la demora", "Atención al cliente": "la atención", "Sanitarios": "los baños",
    "Imagen e instalaciones": "la imagen y las instalaciones", "Stock de productos": "los faltantes de productos",
    "Calidad de productos": "la calidad de los productos", "Problemáticas críticas": "casos puntuales graves",
}
NOMBRE_CANAL = {"GOOGLE": "Google", "APP": "la App YPF", "NPS": "la encuesta NPS", "QR": "el QR"}


def lista(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]


def mail(a, m, res, n_reclasif=0, excluir=()):
    obj = res["objetivo"]
    fecha = "/".join(res["fecha_datos"].split("-")[::-1][:2])
    nom = m["nombre"]
    tot = len(res["estaciones"])
    acum, t30, ant = m["ycx_acum"] or 0, m["ycx_30d"], m["ycx_30d_anterior"]
    arriba = acum >= obj
    L = [f"Asunto: CX – {nom} – cómo vienen al {fecha}", "", "Hola, ¿cómo están?", ""]

    # párrafo 1: situación
    p = f"Les paso cómo viene la estación en Experiencia del Cliente (Y-CX) con los datos al {fecha}. "
    if arriba:
        p += f"En el acumulado del año están en {f(acum)}%, arriba del {obj}% que pide YPF, y quedan en el puesto {m['puesto']} de las {tot} estaciones de la región."
    else:
        p += f"En el acumulado del año están en {f(acum)}%, todavía debajo del {obj}% que pide YPF, y quedan en el puesto {m['puesto']} de las {tot} estaciones de la región."
    L += [p, ""]

    # párrafo 2: último mes
    if t30 is not None:
        neg30 = m["negativos_30d"]
        cn = f"{m['comentarios_30d']} comentarios y {neg30} negativo{'' if neg30 == 1 else 's'}"
        if ant is not None and t30 - ant >= 3:
            p = f"Lo bueno es que el último mes vienen mejor: {f(t30)}% contra {f(ant)}% del mes anterior ({cn})."
            p += " Hay que sostener esto." if not arriba else " ¡Muy bien!"
        elif ant is not None and t30 - ant <= -3:
            p = f"Ojo con el último mes, que bajó a {f(t30)}% (el mes anterior estaban en {f(ant)}%), con {cn}."
        else:
            p = (f"En el último mes siguen en {f(t30)}% ({cn})." if ant is not None and abs(t30 - ant) < 0.5 else f"En el último mes están en {f(t30)}%, parecido al mes anterior ({cn}).")
        if m["comentarios_30d"] < 15:
            p += " Como entran pocos comentarios, cada negativo pesa mucho."
        L += [p, ""]

    # párrafo 3: canales
    flojos = [NOMBRE_CANAL[c] + f" ({f(m['canales'][c]['ycx'], 0)}%)" for c in ["GOOGLE", "APP", "NPS"]
              if m["canales"][c]["comentarios"] >= 10 and (m["canales"][c]["ycx"] or 0) < obj]
    if flojos:
        L += [f"Donde más nos cuesta es en {lista(flojos)}.", ""]

    # párrafo 4: temas
    tops = sorted(m["topicos_neg_acum"].items(), key=lambda kv: -kv[1])[:2]
    if tops:
        t1 = tops[0][0]
        p = (f"Lo poco negativo que entra tiene que ver con {TEMA.get(t1, t1.lower())} ({tops[0][1]} en el año)" if m["negativos"] <= 20 and arriba else f"Lo que más se repite en los comentarios negativos tiene que ver con {TEMA.get(t1, t1.lower())} ({tops[0][1]} en el año)")
        if len(tops) > 1:
            p += f" y {TEMA.get(tops[1][0], tops[1][0].lower())} ({tops[1][1]})"
        p += (". Igual no hay que descuidarlo: " if m["negativos"] <= 20 and arriba else ". Les pido que le pongamos foco: ") + CONSEJO.get(t1, "revisar los casos con el equipo")
        if len(tops) > 1:
            p += f", y {CONSEJO.get(tops[1][0], '')}"
        L += [p + ".", ""]

    negs = [c for c in m.get("neg_recientes", []) if c.get("id") not in excluir][:2]
    if negs:
        L.append("Algunos de los últimos comentarios, para que los vean con el equipo:")
        for c in negs:
            txt = " ".join(c["texto"].split())
            if len(txt) > 200:
                txt = txt[:197].rsplit(" ", 1)[0] + "…"
            L.append(f"- \"{txt}\" ({ {'GOOGLE': 'Google', 'APP': 'App', 'NPS': 'NPS', 'QR': 'QR'}.get(c['canal'], c['canal']) }, {c['fecha']})")
        L.append("")

    # párrafo 5: objetivo y pedido
    falt = m["faltan_positivos_80"]
    if falt and falt > 0:
        if falt <= 40:
            p = f"Están muy cerca: con unos {falt} comentarios positivos más, sin nuevos negativos, llegan al {obj}%."
        elif falt <= 150:
            p = f"Para llegar al {obj}% harían falta unos {falt} comentarios positivos más, sin nuevos negativos."
        else:
            p = f"Llegar al {obj}% va a llevar tiempo (harían falta unos {falt} comentarios positivos), así que lo primero es cortar los negativos."
    elif t30 is not None and t30 < obj and m["comentarios_30d"] >= 15:
        p = "Están arriba del objetivo, pero si siguen entrando negativos como este último mes lo vamos a perder."
    elif acum < obj + 2:
        p = f"Están arriba del {obj}% pero muy justos: con un par de negativos quedan abajo."
    else:
        p = "La idea es mantenerlo."
    p += " Es clave pedirles a los clientes que quedan conformes que califiquen la carga en la App YPF y que dejen su reseña en Google, y responder las reseñas de Google, sobre todo las negativas."
    L += [p, ""]

    if n_reclasif:
        L += [f"Además, encontramos {n_reclasif} comentario{'s' if n_reclasif > 1 else ''} que YPF clasificó mal y ya le estamos pidiendo que {'los corrija' if n_reclasif > 1 else 'lo corrija'}.", ""]

    pos = m.get("pos_recientes", [])[:1]
    if pos:
        L += [f"Y para cerrar con algo lindo, un cliente escribió hace poco: \"{' '.join(pos[0]['texto'].split())}\". ¡Felicitaciones al equipo!", ""]

    L += ["Cualquier cosa me avisan.", "", "Saludos,", "Jesús"]
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
