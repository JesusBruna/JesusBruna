---
name: informe-cx-semanal
description: Analiza el informe semanal de Experiencia del Cliente (Y-CX) de YPF para la región de Jesús Bruna (25 estaciones ACA del Litoral/NEA). Lee el mail "GGO - Informe semanal | Reporte CX y entrenamiento de la red ACA" (carpeta FERNANDO CANCELMO de Outlook) y el Excel "Comentarios CX red ACA.xlsx". Arma el ranking regional, la evolución, los tópicos y canales flojos, la planilla de reclasificación para YPF y un borrador de mail por estación. Usar siempre que el usuario mencione el informe CX semanal, el Y-CX, los comentarios CX, el "Comentarios CX red ACA.xlsx", reclasificar comentarios, o pida "cómo viene la región en CX", aunque no nombre la skill.
---

# Informe CX semanal (región Jesús Bruna)

El usuario es Jesús Bruna, gestor ACA de 25 estaciones (14 propias y 11 del NEA que figuran a nombre de Christian Cortés en el listado de gestores). No es programador. Entregale siempre cosas que pueda abrir o mandar: borradores de Outlook, un Excel o texto para copiar. Nunca le pases un `.py`, un `.json` o una ruta como entregable. Escribile en español rioplatense.

Las estaciones y sus APIES están en `references/estaciones.json`. Si el usuario suma o saca una estación, editá ese archivo. El listado de gestores sale del mail "gestores calidad ACA" de Guillermina Bosch (12/11/2026).

## De dónde salen los datos

- **Mail semanal:** lo manda Fernando Cancelmo y se guarda en la carpeta Outlook `FERNANDO CANCELMO`. El asunto es `GGO - Informe semanal | Reporte CX y entrenamiento de la red ACA`, a veces con `RV:` y sin "GGO". Es un reenvío del informe que YPF (Tomás Layún / Santiago Gordillo) le manda a Fernando. Trae 4 adjuntos:
  - `Informe CX ACA.pdf`: totales de la **red ACA**, con Y-CX acumulado, 30 días, canales y tópicos. Se lee bien con `read_resource`.
  - `Informe aprendizaje ACA.pdf`: cursada +YPF por rol y por trimestre. Se lee bien.
  - `Comentarios CX red ACA.xlsx`: unos 57.000 comentarios de toda la red. **El conector de Outlook lo corta en 200.000 caracteres** (unas 1.250 filas), así que no sirve para analizar. **Pedile al usuario que suba el Excel a la conversación.**
  - `Entrenamiento de la red ACA.xlsx`: también se corta. Usá solo el PDF de aprendizaje, salvo que el usuario suba este Excel.
- **Fórmula (verificada contra el PDF):** `Y-CX = (positivos − negativos) / total de comentarios`. "30 días" toma los comentarios con fecha posterior a (última fecha del Excel − 30 días).
- **Valores válidos para reclasificar** (hoja `Hoja1`): sentimiento `Positivo | Negativo | Inválido`; tópicos `Atención al cliente, Imagen e instalaciones, Tiempo de espera, Sanitarios, Calidad de productos, Stock de productos, Problemáticas críticas, Digital, Precios`. Digital y Precios **no cuentan** en el Y-CX de la estación.

## Pasos

```bash
SK=.claude/skills/informe-cx-semanal/scripts
X="<ruta del Excel subido>"
F=<AAAA-MM-DD de la última fecha del Excel>
python3 $SK/analizar_cx.py "$X" datos/cx_$F --historial datos/cx_historial.csv
mkdir -p informes/cx_$F && mv datos/cx_$F/Informe*.xlsx informes/cx_$F/
```

`analizar_cx.py` deja en `datos/cx_$F/`:
- `resumen.json`: red ACA, región y cada estación, con Y-CX acumulado, 30 días, 30 días anteriores, canales, negativos por tópico, positivos que faltan para el 80%, comentarios negativos y positivos recientes y puesto.
- `negativos_region.csv`: todos los negativos de la región.
- `Informe CX Region dd-mm.xlsx`, con las hojas Resumen, Ranking, Negativos por tópico y Comentarios negativos. Ese archivo es el entregable para el usuario.

Además agrega una fila por estación a `datos/cx_historial.csv`, que guarda la evolución semanal. Usalo para decir "subió/bajó X pp desde la semana pasada".

### Reclasificación (revisión manual, no automática)

1. Leé los negativos de la región (`negativos_region.csv`), priorizando los de los últimos 60 días y los textos cortos, y buscá:
   - **Elogios marcados como negativos**, por ejemplo "muy buena atención", "siempre me atienden muy bien" o "los baños siempre limpios". Son muy comunes en NPS, porque el cliente explica su puntaje ("Porque…"). Van a **Positivo**.
   - **Comentarios que no son sobre la estación:** consultas, quejas sobre otra estación (por ejemplo "YPF San Jorge" cargado a Susana) o texto sin sentido. Van a **Inválido**.
   - **Quejas sobre la App o el sistema** ("página lenta", "lento el sistema", "internet"). Quedan como **Negativo** con tópico **Digital**. Ojo: "el sistema para cobrar con tarjeta es lento y genera cola" es de la estación, así que NO se reclasifica.
   - **Tópico mal asignado**, como "más surtidores" en Stock: corresponde a Imagen e instalaciones.
   - Comentarios mixtos ("buena atención pero lento"): **no** se reclasifican.
2. Cargá las propuestas en `datos/reclasif_$F.json` (`{"ID": ["Sentimiento", "Tópico", "Motivo"]}`). No repitas IDs que ya se mandaron en semanas anteriores: revisá `datos/reclasif_enviados.csv` y, al terminar, agregale las filas nuevas (fecha, ID, sentimiento, tópico; sin texto de clientes).
3. `python3 $SK/reclasificacion.py "$X" datos/reclasif_$F.json "informes/cx_$F/Reclasificacion CX region Bruna dd-mm.xlsx"`. El script valida los valores y muestra el impacto estimado por estación.
4. **Duplicados:** la base de YPF trae IDs repetidos, casi todos positivos. Depurarlos **baja** el Y-CX, así que no los reclames.

### Mails por estación

```bash
python3 $SK/mails_cx.py datos/cx_$F/resumen.json informes/cx_$F/mails --reclasif datos/reclasif_$F.json --xlsx "$X"
```

Sale un `.txt` por estación. Revisá cada uno y ajustá a mano los casos especiales, por ejemplo una estación a un paso del 80% o un equipo roto que los clientes repiten. Después creá un borrador por estación con `outlook_create_draft`: `bodyType: text`, sin la línea "Asunto:", con ese asunto como `subject` y **sin destinatario** salvo que el usuario pida otra cosa. **Nunca envíes.**

**Superposición con otra tarea:** la tarea programada de los lunes "Informes IM – análisis y borradores por estación" ya arma borradores por estación, con destinatarios, para las **14 estaciones propias** a partir de los informes individuales de `informes.im@ypf.com`. Por defecto, esta skill hace los mails por estación **solo para las 11 del NEA** (Posadas, Corrientes, Bernardo de Irigoyen, Clorinda, Eldorado, Formosa, Ingeniero Juárez, Roque Sáenz Peña, Itá Ibaté, Puerto Iguazú y Oberá) y la vista regional consolidada para las 25. Si el usuario pide las 25, hacé las 25.

### Informe visual (HTML + PDF)

```bash
python3 $SK/informe_html.py datos/cx_$F/resumen.json "informes/cx_$F/Informe CX Region dd-mm.html" --red-pdf datos/cx_red_pdf.csv --reclasif datos/reclasif_$F.json --xlsx "$X"
cd informes/cx_$F && NODE_PATH=$(npm root -g) node ../../$SK/html_a_pdf.js "Informe CX Region dd-mm.html" "Informe CX Region dd-mm.pdf"
```

Trae KPIs, ranking con objetivo y 30 días, alertas, canales región contra red, negativos por tópico, evolución de la red, tabla por estación y reclasificación. El PDF sale en A4 apaisado, 3 páginas. Antes de entregarlo mirá las páginas como imagen (`pdftoppm -r 50 -png`). Como tiene datos YPF-Privado, entregalo con `SendUserFile` y no lo publiques como Artifact salvo que el usuario lo pida.

### Cierre

1. **Borrador de reclasificación** a `informes.im@ypf.com`, en HTML simple, con el resumen de lo que se pide. Avisale al usuario que tiene que adjuntar a mano el Excel de reclasificación, porque el conector no adjunta archivos.
2. **Borrador "Resumen CX región – datos al dd/mm"** para Jesus_Bruna@aca.org.ar con:
   - región contra red ACA;
   - ranking de las 25 (acumulado y 30 días);
   - alertas: cerca del 80%, bajando en el último mes, brecha grande, tópico dominante;
   - qué quedó en Borradores.
   Si hay historial, sumá la variación semanal.
3. Marcá el mail de Fernando con la categoría `Procesado CX` (`outlook_modify_labels`).
4. **Commit y push solo de `datos/cx_historial.csv`, `datos/cx_red_pdf.csv` y `datos/reclasif_enviados.csv`.** `datos/cx_*/`, `datos/reclasif_*.json` e `informes/cx_*/` tienen comentarios y contactos de clientes (YPF-Privado) y están en `.gitignore`: no los subas.
5. Mandale al usuario el Excel del informe y el de reclasificación con `SendUserFile`, y resumile en el chat: región, alertas y dónde está cada cosa.

## Modo semanal (tarea programada)

La tarea de los miércoles busca en la carpeta `FERNANDO CANCELMO` un mail nuevo con asunto que contenga "Informe semanal | Reporte CX" y sin la categoría `Procesado CX`.
- **Si hay:** leé los dos PDF y anotá los números de la red en `datos/cx_red_pdf.csv` (fecha del reporte, Y-CX acumulado, 30 días, canales, negativos 30 días, cursada). Dejá un borrador para Jesús, "Llegó el informe CX semanal (datos al dd/mm)", con esos números contra la semana anterior y el pedido: "Subime el Excel 'Comentarios CX red ACA.xlsx' en la conversación para armar el análisis de la región". No marques `Procesado CX` hasta hacer el análisis completo.
- **Si no hay:** terminá sin hacer nada.
