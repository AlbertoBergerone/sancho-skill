# Sancho - guía de uso

[English](guide.en.md) · [Italiano](guide.it.md) · [Español](guide.es.md) · ¿Aún no lo has instalado? [Guía de instalación](install.es.md)

Esta guía es para quien dirige el proyecto: tú, no los agentes. Explica qué te preguntará Sancho, qué decides tú y cómo retomar el hilo después de una pausa.

## 1. Para empezar

1. Instala Sancho (ver la [guía de instalación](install.es.md)).
2. Abre en Claude Code una carpeta vacía o tu proyecto existente (o inicia un chat en la app de Claude).
3. Escribe `/sancho:discover` (Claude Code con el plugin), `/sancho discover` (app de Claude o solo la skill) o simplemente "sancho, quiero crear...".

En el primer uso Sancho muestra un breve recorrido y crea la carpeta `.sancho/`, que guarda la memoria del proyecto. **Inclúyela en git**: así la siguiente sesión sabe en qué punto estás.

¿Te has perdido? Escribe **`next`** para ver el siguiente paso concreto, o **`status`** para ver el panorama completo.

## 2. El recorrido típico

```
discover -> gate -> specify -> gate -> plan -> gate -> tasks -> gate
        -> implement (tarea a tarea) -> gate -> verify (tú ejecutas los UAT) -> gate
        -> release (tú apruebas la puesta en producción) -> gate -> evolve -> gate
```

Cada fase termina con un **resumen del gate**: qué se ha producido, resultados de la checklist, problemas abiertos y qué *no* se ha verificado. Responde "apruebo", o di qué cambiar. Sancho nunca aprueba en tu nombre.

## 3. Chuleta de comandos

| Qué quieres hacer | Claude Code con el plugin | App de Claude (y Claude Code solo con la skill) | Con palabras, en cualquier sitio |
|---|---|---|---|
| Recorrido y ayuda | `/sancho:help` | `/sancho help` | "sancho, ayuda" |
| Ayuda sobre un tema | `/sancho:help uat` | `/sancho help uat` | "sancho, explícame los UAT" |
| ¿En qué punto estamos? | `/sancho:status` | `/sancho status` | "sancho, ¿en qué punto estamos?" |
| ¿Qué hago ahora? | `/sancho:next` | `/sancho next` | "sancho, ¿siguiente paso?" |
| Ejecutar una fase | `/sancho:discover` ... `/sancho:evolve` | `/sancho plan` | "sancho, hagamos el plan" |
| Implementar una tarea concreta | `/sancho:implement T-007` | `/sancho implement T-007` | "sancho, implementa T-007" |
| UAT guiados | `/sancho:verify uat` | `/sancho verify uat` | "sancho, hagamos los UAT" |
| Solo comprobaciones de seguridad | `/sancho:verify security` | `/sancho verify security` | "sancho, haz las comprobaciones de seguridad" |
| Guardar antes de parar | `/sancho:checkpoint` | `/sancho checkpoint` | "sancho, checkpoint" |
| Analizar un proyecto existente | `/sancho:assess` | `/sancho assess` | "sancho, analiza este proyecto" |

<!-- invocation-forms -->
**Dos formas, según dónde uses Sancho.**
- **Claude Code con el plugin:** `/sancho:<comando>`, todo junto (`/sancho:status`). El plugin registra un comando por cada entrada y el formato `plugin:comando` es el estándar de Claude Code.
- **App de Claude** (web, escritorio, móvil) **y Claude Code solo con la skill:** `/sancho <comando>`, con espacio (`/sancho status`). Hay un único comando, `/sancho`: al elegirlo en el menú la app añade un espacio y el comando se escribe justo después. `/sancho:status` no existe ahí; si por costumbre escribes `/sancho :status`, Sancho lo entiende igual.

Tus respuestas en un gate: "apruebo" (o "ok", "adelante") · "no apruebo: <motivo>" · "apruebo igualmente, acepto <riesgo>" (se registra como override).

## 4. Tu primera sesión (ejemplo)

```
Tú:     /sancho:discover Quiero una app para que los técnicos registren los trabajos de mantenimiento
Sancho: Sancho a tu servicio. Cuatro preguntas rápidas para empezar:
        1. ¿Quién registra los trabajos, y desde qué dispositivo? ...
Tú:     (respuestas)
Sancho: (dos rondas más: restricciones, datos personales; cuatro propuestas de nombre)
        Propongo el nivel L2: datos personales de clientes, dos plataformas. ¿De acuerdo?
Tú:     sí, y me gusta "FieldLog"
Sancho: GATE DISCOVER - listo para tu aprobación
        Producido: docs/constitution.md · Checklist: 8 pass, 1 n/a · Decisiones: nombre, L2
        No verificado: costes de hosting (HYPOTHESIS)
        ¿Apruebas, o me dices qué cambiar?
Tú:     apruebo
Sancho: Gate aprobado. Siguiente paso: SPECIFY - requisitos e historias de usuario (/sancho:specify).
```

Un proyecto completo de ejemplo está en [examples/fieldlog](../examples/fieldlog/WALKTHROUGH.md).

## 5. Qué decides tú, fase por fase

| Fase | Sancho te pregunta | Consejos |
|---|---|---|
| DISCOVER | el problema, los usuarios, las plataformas, presupuesto y plazos, los datos personales, el nombre del producto, el nivel de riesgo | Indica 2-3 tipos reales de usuario, no "todo el mundo". Si hay cuentas, correos o fotos de personas, se aplica el RGPD. |
| SPECIFY | prioridades (must/should/could/won't), qué queda FUERA de la primera versión, preguntas abiertas | Lee con atención la lista OUT: es la protección de tu alcance. |
| PLAN | stack (recibes una recomendación y dos alternativas con puntuaciones), contenedores, paleta, logo, riesgos aceptados | Si ya sabes qué tecnología usar, dilo: Sancho la acepta y solo enumera sus riesgos. |
| TASKS | orden de ejecución e hitos | Las tareas grandes se dividen automáticamente (complejidad superior a 7). |
| IMPLEMENT | solo cuestiones de alcance y tareas bloqueadas | Pide `status` cada pocas tareas; antes de parar, acepta el checkpoint. |
| VERIFY | aprobación de las pruebas de seguridad activas, resultados UAT, aceptación de riesgos residuales | Los UAT los ejecutas tú: Sancho te guía caso por caso. |
| RELEASE | puesta en producción, publicación en tiendas, migraciones en producción | Cada paso irreversible requiere tu sí explícito. |
| EVOLVE | retrospectiva, cómo resolver las diferencias entre código y estándares | Mantiene el proyecto coherente para la siguiente vuelta. |

## 6. Niveles: cuánto proceso

| Nivel | Cuándo | Qué cambia |
|---|---|---|
| L0 | script desechable, demo | tres preguntas, gates de palabra, sin PLAN/RELEASE/EVOLVE |
| L1 | app pequeña, una plataforma, sin datos sensibles | PLAN, RELEASE, EVOLVE omitidas; elección rápida del stack en DISCOVER |
| L2 | producto real, varias plataformas, datos personales | las ocho fases |
| L3 | pagos, salud, sectores regulados, migraciones de datos reales | todas las fases + análisis de impacto, planes de rollback, revisión de seguridad adicional |

Puedes cambiar de nivel más adelante: Sancho te explica qué implica.

## 7. UAT: probar el producto tú mismo

En TASKS, QA escribe las pruebas de aceptación en lenguaje sencillo: precondiciones, datos de prueba, pasos numerados, resultado esperado, una plataforma o un dispositivo por caso. Las recibes como `docs/uat/UAT.md` (imprimible, con casillas) y como `docs/uat/uat.csv` (hoja de cálculo).

En VERIFY puedes elegir entre dos modalidades:
- **Guiada:** `/sancho:verify uat`. Sancho te muestra un caso, lo ejecutas en el dispositivo y respondes superado, fallido o bloqueado, con notas.
- **Hoja de cálculo:** rellena el CSV (Resultado, Ejecutado por, Notas), también con tus compañeros, y devuélvelo. Sancho lo importa.

Cada fallo se convierte en un defecto con una gravedad, una tarea de corrección y una nueva prueba. La fase no se cierra con defectos blocker o major abiertos, salvo que aceptes el riesgo de forma explícita.

## 8. Seguridad: qué esperar

- En PLAN, un modelo de amenazas enumera qué puede salir mal y cómo se evita.
- En VERIFY, Sancho ejecuta (o te pide instalar) la búsqueda de secretos, el análisis estático, el control de dependencias, el escaneo de contenedores y, para móvil, el análisis de la app. Las vulnerabilidades se priorizan por **CISA KEV** (explotadas activamente), después por **EPSS** (probabilidad de explotación) y después por **CVSS**.
- Las **pruebas activas** (por ejemplo un escaneo con OWASP ZAP) se ejecutan en tu entorno local, de pruebas o de staging, después de que apruebes el objetivo exacto. En tu producción solo con tu aprobación explícita y una ventana horaria acordada, ambas registradas. Sancho rechaza objetivos de terceros.
- Todo lo que no se ha podido ejecutar se marca como **NOT RUN**, con el comando para ejecutarlo más tarde. "Sin hallazgos" nunca se presenta como "seguro".

## 9. Volver atrás, pausar, retomar

- **Cambio de idea:** "reabre SPECIFY, quiero añadir X". Sancho reabre la fase, actualiza el backlog y comprueba el impacto en tareas y UAT.
- **Saltar una fase:** es posible. Sancho registra el motivo en un ADR (registro de decisiones).
- **Pausa:** `/sancho:checkpoint` guarda un breve resumen. La próxima vez, `status` lo retoma.

## 10. Marca e imágenes

Sancho diseña los logos en SVG y las paletas como design tokens con contraste verificado. Para fotos o ilustraciones complejas puede usar un servicio de generación de imágenes que hayas configurado (clave API en una variable de entorno, o un servidor MCP). Si no, te entrega un prompt listo para pegar en la herramienta que prefieras.

## 11. Trabajar en equipo

Sancho funciona también con varias personas en el mismo proyecto, cada una con su propia copia del repositorio. El modo equipo se activa cuando existe `.sancho/team.json`; sin él, todo sigue como para una sola persona.

**Preparar el equipo (una vez, el coordinador).** Pide "sancho, prepara el equipo": Sancho propone los miembros a partir de los autores de los commits y los añade con nombre, email de git y roles (por ejemplo `developer`, `qa`). El primer coordinador abre y cierra las fases. Opcional: en `team.json` decidís quién aprueba cada gate y cuántas aprobaciones hacen falta. Haz commit de `team.json` y `.gitattributes`.

**Cada día.**
1. `git pull`, después "sancho, ¿qué ha cambiado?": ves lo que han hecho los demás, primero lo que te afecta. Con el hook ("sancho, instala el hook") lo ves solo después de cada pull.
2. "sancho, ¿siguiente paso?": el paso es **tuyo**, no del proyecto. Si no hay nada para ti, Sancho dice quién está haciendo qué.
3. Reserva una tarea, un caso UAT o un defecto antes de trabajar en él: "sancho, me quedo con T-007". Sancho registra la reserva y propone hacer commit y push enseguida, para que los demás la vean.
4. Al terminar una tarea la marcas lista para revisión; la aprueba otro miembro con el rol `qa` (cuatro ojos).

**Gates.** El coordinador envía el resumen; cada aprobador aprueba desde su propia sesión. El gate se cierra cuando hay suficientes aprobaciones. Después de un gate el coordinador compacta el registro ("sancho, compacta el registro").

**Si algo se cruza.** Dos reservas de la misma tarea: gana la primera y se avisa a la otra persona. Dos defectos con el mismo número: el segundo se renumera. Dos historias o tareas con el mismo id tras un merge: "sancho, renumera los id duplicados".

**Límites.** Sancho ve el trabajo de los demás solo después de push y pull, y ordena los eventos con el reloj de los ordenadores. La identidad viene del email de git: sirve para coordinarse, no para proteger. En la app de Claude (chat) el modo equipo no sirve: allí no hay git.

En el plugin, el panel muestra la sección **Squadra** (equipo: quién tiene qué, reservas en conflicto, votos del gate) y **Novità** (novedades), con el botón **Segna come viste** (marcar como vistas).

## 12. Preguntas frecuentes

**¿Necesita internet?** Solo para búsquedas y para los datos de vulnerabilidades (OSV, NVD, KEV, EPSS). Sin conexión, esas comprobaciones quedan como NOT RUN.

**Falta Python (Windows).** Instala Python 3.9+ desde python.org marcando "Add to PATH", o usa el lanzador `py`. Los scripts no necesitan paquetes adicionales.

**¿Puedo usarlo en un proyecto existente?** Sí. En DISCOVER primero extrae las convenciones existentes como estándares, para que el trabajo nuevo sea coherente con el código que ya tienes.

**¿De quién son las decisiones?** Tuyas. Nombre, plataformas, stack, marca, alcance, cada gate y la puesta en producción los decides tú. Sancho propone, explica y registra.
