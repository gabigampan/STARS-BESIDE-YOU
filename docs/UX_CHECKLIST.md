# UX launch checklist (acceptance gate)

Source: "Ruta de lanzamiento", the design self-assessment sheet handed out at the
Málaga local event of the NASA Space Apps Challenge 2026 (UX desk, Ladies That UX
Málaga). Transcribed from the paper sheet and translated; the Spanish wording is
kept next to each item because that is what the local jury uses.

The demo is ready only when every required item passes and no red alert appears.
Items marked "Extra" add points and are treated as required for this project.

## 01 Purpose at first sight (Propósito a primera vista)

- The first screen makes clear what it is and who it is for. *(La primera pantalla deja claro qué es y a quién va dirigido.)*
- The most prominent thing is the main action. *(Lo que más destaca es la acción principal.)*
- Extra: someone from another team understands it in 5 seconds. *(Alguien de otro equipo lo entiende en 5 segundos.)*

## 02 Main flow (Flujo principal)

- The key task can be completed from start to finish. *(La tarea clave se completa de principio a fin.)*
- From every screen you can continue or go back. *(Desde cada pantalla se puede seguir o volver atrás.)*
- Extra: you know which step you are on. *(Se sabe en qué paso se está.)*

## 03 Hierarchy and patterns (Jerarquía y patrones)

- One main action per screen; secondary actions are more discreet. *(Una acción principal por pantalla. Lo secundario, más discreto.)*
- Whatever repeats (buttons, cards, menu) looks the same on every screen. *(Lo que se repite es igual en todas las pantallas.)*
- Extra: known patterns are used, for example a magnifier to search, an X to close. *(Usáis patrones conocidos.)*

## 04 Legibility (Legibilidad)

- Main text reads without effort, at least 14 px. *(El texto principal se lee sin esfuerzo, con al menos 14 px.)*
- Buttons and titles use words the user understands. *(Botones y títulos usan palabras que entiende quien lo usa.)*
- Extra: at most 3 typefaces. *(Como máximo, 3 tipografías.)*

## 05 Contrast and colour (Contraste y color)

- Text reads well on its background, also with low screen brightness. *(El texto se lee bien sobre su fondo, también con el brillo de la pantalla bajo.)*
- Nothing important depends on colour alone; it also carries text or an icon. *(Lo importante no depende solo del color, lleva también texto o icono.)*
- Extra: in greyscale everything is still understood. *(En escala de grises, todo se sigue entendiendo.)*

## 06 Touch sizes (Tamaños para pulsar)

- Buttons and links are easy to press with a finger. *(Botones y enlaces se pulsan fácilmente con el dedo.)*
- There is enough space not to press the neighbour. *(Hay espacio suficiente para no pulsar el de al lado.)*
- Extra: it reads well from 2 metres with the laptop on the table. *(Se lee bien desde 2 metros, con el portátil sobre la mesa.)*

## 07 System response (Respuesta del sistema)

- Every action has a visible response: a change, a message or a loading indicator. *(Cada acción tiene una respuesta visible, un cambio, un mensaje o un indicador de carga.)*
- Errors say what happened and how to continue. *(Los errores dicen qué ha pasado y cómo seguir.)*
- Extra: empty screens say what to do. *(Las pantallas vacías dicen qué hacer.)*

## Red alerts: must not appear in the demo (Alerta roja)

- Filler text or data: "lorem ipsum", "Title here", "asdf". *(Textos o datos de relleno.)*
- Buttons that do nothing in the flow that will be shown. *(Botones que no hacen nada en el flujo que vais a enseñar.)*
- Technical errors in view: "Error 500", "undefined". *(Errores técnicos a la vista.)*
- States told apart only by colour, with no text or icon. *(Estados que solo se distinguen por el color, sin texto ni icono.)*

## How each item is measured in this project

| Item | Measured by |
|---|---|
| 01 | First screen read by a reviewer who has not seen the project; the main action is the largest interactive element in the first viewport |
| 02 | Scripted browser run of the key task (choose a mission, pick a ranked point, read the comparison, start the mission video, go back) with mouse and with keyboard only |
| 03 | One primary button style per view; repeated components share one implementation |
| 04 | Computed font size of every visible text node is 14 px or more; at most 3 font families in computed styles |
| 05 | Computed contrast ratio of text against its background is 4.5:1 or more; every state has text or an icon; greyscale screenshots reviewed |
| 06 | Every interactive element is at least 44 x 44 px with 8 px between neighbours; headline figures legible in a screenshot scaled to the size seen from 2 m |
| 07 | Every control produces a visible change within 100 ms or shows a loading indicator; forced failures (blocked imagery, missing data file) show a message that says what happened and what to do; empty states carry an instruction |
| Red alerts | Text scan of every view for filler strings, "undefined", "NaN", "null", error codes; every button exercised; every state checked for a non-colour cue |
