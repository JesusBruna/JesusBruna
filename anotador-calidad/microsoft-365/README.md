# 📋 Anotador de Gestión de Calidad, versión Microsoft 365

Usa la cuenta del trabajo (`@aca.org.ar`):

- **Excel en OneDrive**: el anotador. Una tabla llamada `Tareas`. Las columnas **Días** y **Alerta** se calculan solas.
- **Power Automate**: todos los días a las 8 hs lee la tabla y, si hay algo vencido, que vence hoy o que está por vencer, manda un mail al equipo con la lista.
- Opcional: el mismo aviso en **Teams** (chat o canal del equipo), en forma automática.

```
 Encargado/a ──carga──▶  Excel en OneDrive  ◀──ve── Equipo (archivo compartido / pestaña en Teams)
                              │
                    Power Automate 8 hs
                              ▼
                   Mail al equipo (+ Teams opcional) ──copiar──▶ Grupo de WhatsApp
```

`armar_excel.py` genera el Excel inicial (`python3 armar_excel.py "Anotador Gestión de Calidad.xlsx" tu@mail`).

---

## 1. El Excel

Archivo: equipo de Teams **GO.Gestion de Calidad → canal General → Archivos → Anotador Gestión de Calidad.xlsx**
(sitio de SharePoint `https://acacloud.sharepoint.com/sites/GOGestiondeCalidad`, carpeta `Documentos compartidos/General`).
Todos los miembros del equipo ya lo pueden ver y editar sin compartir nada.

- Cargar tareas en la primera fila vacía **justo debajo de la tabla**. La tabla se agranda sola y copia las fórmulas.
- **No escribir en Días ni en Alerta.**
- *Avisar días antes* vacío = 3 días.
- Estado **Hecho** → deja de avisarse y queda tachado.
- Borrar las filas que dicen **PRUEBA** cuando todo funcione.

**Tenerlo a mano en Teams:** en el canal General, **＋ (agregar pestaña) → Excel → elegir el archivo**.

---

## 2. El aviso automático (Power Automate, ~10 minutos)

Entrar a **https://make.powerautomate.com** con la cuenta `@aca.org.ar`.
(Si no aparece o no deja crear flujos, la licencia de ACA no lo incluye. En ese caso hay que consultar a Sistemas.)

**Crear → Flujo de nube programado**
- Nombre: `Avisos Anotador Calidad`
- Comenzar: mañana, 08:00 · Repetir cada: **1 Día** → **Crear**.
- En el paso *Recurrence*, abrir los parámetros: **Zona horaria** = *(UTC-03:00) Buenos Aires*, **En estas horas** = `8`.

**＋ Paso 2 – Excel Online (Business) → "Enumerar filas presentes en una tabla"** (*List rows present in a table*)
- Ubicación: **Group - GO.Gestion de Calidad** (si no aparece en la lista: *Escribir un valor personalizado* → `https://acacloud.sharepoint.com/sites/GOGestiondeCalidad`)
- Biblioteca de documentos: **Documentos** (o *Documentos compartidos*)
- Archivo: carpeta 📁 → `General` → `Anotador Gestión de Calidad.xlsx` · Tabla: **Tareas**
- Parámetros avanzados → **Formato de fecha y hora (DateTime Format)** = **ISO 8601**.

**＋ Paso 3 – Operación de datos → "Filtrar matriz"** (*Filter array*)
- Desde: `value` (contenido dinámico del paso 2)
- Condición: `Alerta` (contenido dinámico) **no es igual a** *(dejar vacío)*

**＋ Paso 4 – Operación de datos → "Seleccionar"** (*Select*)
- Desde: `Body` de *Filtrar matriz*
- Asignación (pasar a modo texto con el botón 🔁 y pegar):
  ```
  {
    "Alerta": "@{item()?['Alerta']}",
    "Tarea": "@{item()?['Tarea']}",
    "Responsable": "@{item()?['Responsable']}",
    "Vence": "@{formatDateTime(item()?['Vence'], 'dd/MM/yyyy')}",
    "Notas": "@{item()?['Notas']}"
  }
  ```

**＋ Paso 5 – Control → "Condición"**
- Izquierda: *expresión* → escribir `length(` y elegir `Body` de *Filtrar matriz* en el contenido dinámico, cerrar `)`.
- Operador: **es mayor que** · Derecha: `0`

**En la rama "Verdadero":**
1. **Operación de datos → "Crear tabla HTML"**. Desde: `Output` de *Seleccionar*.
2. **Office 365 Outlook → "Enviar correo electrónico (V2)"**
   - Para: los mails del equipo separados por `;`
   - Asunto: `📋 Gestión de Calidad: tareas vencidas o por vencer`
   - Cuerpo: un texto corto + `Output` de *Crear tabla HTML* + el link al Excel.
     Ejemplo: *"Buen día, estas son las tareas del anotador que necesitan atención:"*

Dejar la rama **"Falso"** vacía: ese día no se manda nada.

**Guardar → Probar → Manualmente → Probar.** El mail tiene que traer 3 filas de prueba: 🔴 vencida, 🟠 vence hoy y 🟡 por vencer.

### Opcional
- **Teams automático:** en la rama *Verdadero*, agregar **Microsoft Teams → "Publicar mensaje en un chat o canal"** con el mismo `Output` de *Crear tabla HTML*.
- **Resumen semanal de los lunes:** duplicar el flujo (**… → Guardar como**). En la copia: Recurrence = semanal, lunes; borrar *Filtrar matriz* y usar `value` del paso 2 en *Seleccionar*.
- **WhatsApp:** no hay forma oficial de que un sistema escriba solo en un grupo de WhatsApp. La persona encargada copia la lista del mail (o de Teams) y la pega en el grupo.
