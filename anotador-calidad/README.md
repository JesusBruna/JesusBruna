# 📋 Anotador del equipo de Gestión de Calidad

Un anotador compartido para los temas importantes del equipo (relevamientos, auditorías, documentos, reuniones, recordatorios), con **fecha de vencimiento** y **avisos automáticos**.

- **Una persona encargada** carga los temas, desde el celular o la compu.
- **Todo el equipo** ve la lista con un link fijado en el grupo de WhatsApp.
- **Todos los días a las 8 hs** llega un mail con lo vencido, lo que vence hoy y lo que está por vencer. **Los lunes** llega el resumen completo de la semana.
- El mail trae un botón **"📲 Reenviar al grupo de WhatsApp"**: la persona encargada lo toca, elige el grupo y listo, el mensaje ya está armado.

Es gratis: usa una planilla de Google y un script de Google (Apps Script). No hay que instalar nada.

```
 Encargado/a ──carga──▶  Planilla de Google  ◀──ve── Todo el equipo (link en el grupo)
                              │
                     todos los días 8 hs
                              ▼
                 Mail al equipo + botón "Reenviar a WhatsApp" ──▶ Grupo de WhatsApp
```

---

## Cómo se ve el mensaje en el grupo

```
📋 *Anotador – Gestión de Calidad*
_22/10/2026_

*🔴 Vencidas*
• Relevamiento estación Rafaela — Relevamiento · Ana · 20/10/2026 (venció hace 2 días)

*🟠 Vencen hoy*
• Auditoría interna ISO 9001 — Auditoría · Luis · 22/10/2026 (vence HOY)

*🟡 Por vencer*
• Actualizar procedimiento — Documento · 24/10/2026 (vence en 2 días)

🔗 Ver anotador: https://script.google.com/...
```

---

## Instalación (una sola vez, unos 10 minutos)

La hace la persona encargada, con su cuenta de Google.

1. **Crear la planilla.** Entrar a <https://sheets.new> y ponerle de nombre *Anotador Gestión de Calidad*.
2. **Pegar el script.** En la planilla: menú **Extensiones → Apps Script**.
   - Borrar lo que haya en `Código.gs` y pegar todo el contenido de [`Codigo.gs`](Codigo.gs).
   - Tocar **＋ → HTML**, ponerle de nombre `Web` (sin `.html`) y pegar el contenido de [`Web.html`](Web.html).
   - En `Codigo.gs`, cambiar `CLAVE_CARGA: 'calidad2026'` por una clave propia.
   - **⚙️ Configuración del proyecto → Zona horaria:** elegir *(GMT-03:00) Buenos Aires*.
   - Guardar (💾).
3. **Activarlo.** Volver a la planilla y recargar la página. Aparece el menú **📋 Anotador → Configurar anotador**.
   Google va a pedir permisos (*"Esta app no está verificada" → Configuración avanzada → Ir a…*). Es normal: el script es tuyo y solo usa tu planilla y tu mail.
   Esto crea las hojas **Tareas** y **Equipo**, con colores y listas desplegables, y deja programado el aviso diario.
4. **Cargar al equipo** en la hoja **Equipo**: nombre y mail de cada persona.
5. **Probar:** menú **📋 Anotador → Enviar resumen por mail ahora**.

### Página para el celular (recomendado)

Así nadie tiene que abrir la planilla: todos ven la lista desde el link, y la persona encargada carga tareas con un formulario.

1. En Apps Script: **Implementar → Nueva implementación → ⚙️ Aplicación web**.
2. *Ejecutar como:* **Yo**. *Quién tiene acceso:* **Cualquier usuario**.
3. **Implementar** y copiar el link que termina en `/exec`.
4. **Fijar ese link en el grupo de WhatsApp** (en la descripción del grupo o en un mensaje fijado).

Desde ese link cualquiera ve las tareas. Para **cargar** o marcar **✅ Hecho / ⏳ En curso** se pide la clave de carga (solo la tiene la persona encargada). Desde que esté implementada, el link también aparece al final de cada aviso.

> Si después cambiás el código, para que la página use la versión nueva: **Implementar → Gestionar implementaciones → ✏️ → Versión: Nueva → Implementar**. El link no cambia.

---

## Uso diario

**Persona encargada**
- Cargar un tema: botón **＋ Cargar** en la página, o una fila nueva en la hoja *Tareas*. El N°, la fecha de carga y el estado se completan solos.
- Columnas: *Tema / Tarea* (obligatoria), *Tipo*, *Responsable*, *Vence*, *Avisar (días antes)* (si se deja vacía son 3 días), *Estado*, *Notas*.
- Cuando se termina algo, marcarlo **Hecho**. Deja de avisarse y queda tachado como historial.
- Cuando llega el mail, tocar **📲 Reenviar al grupo de WhatsApp**.
  También se puede usar en cualquier momento el menú **📋 Anotador → Ver mensaje para WhatsApp**.

**Todo el equipo**
- Ver el link fijado en el grupo y revisar el mail de las 8 hs.
- Los pedidos se le mandan a la persona encargada para que los cargue. Así el grupo no se llena de mensajes sueltos.

**Colores en la planilla:** 🔴 vencida · 🟡 por vencer · gris tachado = hecha.

---

## ¿Y WhatsApp automático directo al grupo?

WhatsApp **no permite** que un sistema publique solo en un grupo común, salvo con programas no oficiales que pueden hacer que **bloqueen el número**. Por eso la opción segura es el botón *Reenviar al grupo*: un toque por día.

**Opcional: WhatsApp automático individual (gratis, con CallMeBot).** Cada persona que quiera recibir el aviso en su WhatsApp personal:
1. Agenda el número de CallMeBot que aparece en <https://www.callmebot.com/blog/free-api-whatsapp-messages/>.
2. Le manda por WhatsApp el mensaje `I allow callmebot to send me messages`.
3. Recibe una *apikey*. La carga en la hoja **Equipo** junto con su número (formato `549` + característica + número, sin 0 ni 15. Ej.: `5493415551234`).

Desde ese día le llega el mismo aviso por WhatsApp, además del mail. Es un servicio externo gratuito, sin garantías: para lo importante, el mail es el respaldo.

---

## Ajustes rápidos (al principio de `Codigo.gs`)

| Opción | Para qué |
|---|---|
| `HORA_AVISO: 8` | Hora del aviso diario |
| `DIAS_AVISO_DEFECTO: 3` | Con cuántos días de anticipación avisar si no se indica |
| `RESUMEN_SEMANAL_DIA: 1` | Día del resumen completo (0 = domingo, 1 = lunes…) |
| `CLAVE_CARGA` | Clave para cargar desde la página web |
| `TIPOS` | Lista de tipos de tarea (agregar o quitar) |

Si se cambia `HORA_AVISO`, volver a ejecutar **📋 Anotador → Configurar anotador** (no borra datos).

---

## Mensaje sugerido para fijar en el grupo

```
📋 *Anotador del equipo*
Todos los temas con fecha (relevamientos, auditorías, documentos, reuniones) están acá:
👉 <link de la página>

• La carga la hace <nombre>. Si necesitás que se agende algo, mandale el tema, el responsable y la fecha.
• Todos los días a las 8 hs llega por mail lo vencido y lo que está por vencer, y se comparte acá.
• Cuando termines algo, avisale a <nombre> para marcarlo como hecho ✅
```
