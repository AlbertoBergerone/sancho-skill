# Sancho

**Tu escudero fiel para proyectos de software.** Es una skill para Claude y un plugin para Claude Code: un equipo de siete agentes especializados lleva un proyecto desde la primera idea hasta el lanzamiento en ocho fases, y cada paso lo apruebas tú.

[English](README.md) · [Italiano](README.it.md) · [Español](README.es.md)

**Documentación:** [Guía de instalación](docs/install.es.md) · [Guía de uso](docs/guide.es.md) · [Proyecto de ejemplo](examples/fieldlog/WALKTHROUGH.md)

> Don Quijote sueña. Sancho mantiene recto el camino, se acuerda del presupuesto y nunca da por ganada una batalla sin pruebas.

## Por qué

Los asistentes de programación con IA son rápidos pero olvidadizos. Se saltan la planificación, inventan requisitos, dicen "todos los tests pasan" sin ejecutarlos y con el tiempo se alejan de las convenciones del proyecto. Sancho aporta la disciplina de proyecto que falta, sin enterrar en procesos a los proyectos pequeños:

- **Ocho fases, cada una cerrada por un gate que apruebas tú.** Cada gate tiene una checklist de calidad y un control de trazabilidad.
- **Siete roles especializados** que se pasan el trabajo con handoffs estructurados y verificables.
- **Evidencias, no afirmaciones.** Cada estado es VERIFIED, REPORTED, HYPOTHESIS o NOT RUN.
- **UAT guiados.** Recibes pruebas de aceptación paso a paso, escritas para testers no técnicos, en Markdown y como hoja de cálculo.
- **Pruebas de seguridad con prioridades reales:** checklists OWASP, OSV y NVD, CISA KEV y FIRST EPSS. Las pruebas activas solo se ejecutan sobre sistemas tuyos y aprobados por ti.
- **Coherencia en el tiempo.** Los estándares del proyecto se extraen del código real y se cargan tarea por tarea.
- **Proporcionalidad.** Un script desechable (L0) requiere tres preguntas. Un producto regulado (L3) requiere análisis de impacto y planes de rollback.

## Las fases

| # | Fase | Lidera | Decides tú |
|---|---|---|---|
| 0 | **DISCOVER**: principios, personas, plataformas, restricciones, RGPD, nombre | Analyst/PM | nombre, plataformas, nivel de riesgo |
| 1 | **SPECIFY**: requisitos, historias autosuficientes, criterios de aceptación, alcance del MVP | Analyst/PM | prioridades, qué entra y qué queda fuera |
| 2 | **PLAN**: matriz del stack, arquitectura, ADR, contenedores, marca, modelo de amenazas | Architect + UX/UI + Security | stack, paleta, logo |
| 3 | **TASKS**: tareas con dependencias y complejidad 1-10, checklist UAT | Analyst/PM + QA | orden, hitos |
| 4 | **IMPLEMENT**: una tarea cada vez, guiada por tests, con los estándares aplicados | Developer | cuestiones de alcance |
| 5 | **VERIFY**: tests, UAT guiados contigo, seguridad, accesibilidad | QA + Security + UX/UI | resultados UAT, aceptación de riesgos |
| 6 | **RELEASE**: SemVer, changelog, despliegue y rollback, tiendas, monitorización | Release manager | puesta en producción |
| 7 | **EVOLVE**: estándares desde el código, retrospectiva, siguiente iteración | Release manager + Architect | qué cambiar |

Los proyectos L0-L1 se saltan PLAN, RELEASE y EVOLVE por defecto. Puedes saltarte cualquier fase, pero el motivo queda registrado en un ADR.

## El equipo

Analyst/PM (orquestador) · UX/UI designer · Architect · Developer · QA · Security engineer · Release manager.
En Claude Code trabajan como subagentes (`sancho:developer`, ...). En las apps de Claude la conversación principal interpreta un rol tras otro.

## Instalación

Las instrucciones completas paso a paso, con actualización, desinstalación, herramientas de seguridad opcionales y solución de problemas, están en la **[guía de instalación](docs/install.es.md)**. En resumen:

| Usas | Haz esto |
|---|---|
| Claude Code (recomendado: plugin) | `/plugin marketplace add AlbertoBergerone/sancho-skill`, luego `/plugin install sancho@sancho` |
| Claude Code (solo la skill) | copia `skills/sancho` en `~/.claude/skills/sancho` |
| App de Claude (web, escritorio) | activa la ejecución de código y luego **Customize -> Skills -> + -> Upload a skill** con `sancho.zip` de [Releases](https://github.com/AlbertoBergerone/sancho-skill/releases) |

Requisitos: Python 3.9+ (solo biblioteca estándar) donde se ejecuta Claude Code. Las herramientas de seguridad son opcionales.

Después lee la **[guía de uso](docs/guide.es.md)**: el recorrido, la chuleta de comandos, una sesión de ejemplo, qué decides en cada fase, UAT, seguridad.

## Qué Sancho usar

Sancho existe en tres formas. La skill es la misma en todas: cambia dónde la usas, cómo la llamas y qué la acompaña.

| | Plugin | Solo la skill | ZIP para las apps de Claude |
|---|---|---|---|
| **Dónde** | Claude Code: terminal, pestaña Code de la app de escritorio, VS Code, JetBrains | Claude Code | Chat de claude.ai, apps de escritorio y móvil |
| **Cómo lo llamas** | `/sancho:status`, `/sancho:verify` ... | `/sancho status`, `/sancho verify` ... | `/sancho status`, o con tus palabras |
| **El equipo** | El trabajo va a los 7 subagentes `sancho:<rol>`; las preguntas y aprobaciones se quedan contigo en el chat | La conversación principal asume un rol cada vez | Como solo la skill |
| **Panel** | Franja sobre el prompt, avisos, `/sancho-panel` | No | No |
| **Scripts** | Python en tu ordenador | Python en tu ordenador | En el entorno de Claude, con la ejecución de código activada |
| **Se instala** | `/plugin install sancho@sancho` | Copiando `skills/sancho` | Subiendo `sancho.zip` |

### Con el plugin (recomendado en Claude Code)

1. Abre en Claude Code la carpeta del proyecto, vacía o existente.
2. Escribe `/sancho:discover` para un proyecto nuevo, o `/sancho:assess` para analizar uno existente.
3. Cuando hay un proyecto Sancho, aparece la franja sobre el prompt: fase, estado del gate y siguiente paso. «dettagli» (o `/sancho-panel`) abre el panel con las ocho fases, los problemas abiertos y los botones de comandos.
4. En cada gate lee el resumen y responde "apruebo" o di qué cambiar. Después `/sancho:next` te dice qué sigue.

### Solo con la skill (Claude Code)

Para una instalación mínima, sin plugin. Se trabaja como con el plugin, pero los comandos llevan espacio (`/sancho discover`, `/sancho next`), no hay panel y la conversación principal interpreta los roles, anunciando cada cambio ("Me pongo el sombrero de arquitecto"). El plugin y la skill sola usan la misma carpeta `.sancho/`, así que en el mismo proyecto puedes pasar de uno a otra. En Claude Code instala solo uno, para no tener Sancho dos veces.

### En la app de Claude (chat)

Para quien no usa Claude Code. Sube `sancho.zip` una vez (consulta la [guía de instalación](docs/install.es.md)), abre un chat nuevo y escribe "sancho, quiero crear..." o `/sancho discover`. Los scripts se ejecutan en el entorno de Claude, así que no necesitas nada en tu ordenador, pero la ejecución de código debe estar activada. Aquí no hay panel: pide el estado con `/sancho status`. Para escribir y probar código en tu propio repositorio necesitas Claude Code.

## Comandos

| Plugin | Qué hace |
|---|---|
| `/sancho:help [tema]` | Guía en una pantalla; temas: phases, roles, commands, uat, security, gates, files |
| `/sancho:status` | Fases, tareas, UAT, defectos, seguridad, bloqueos, siguiente paso |
| `/sancho:next` | El siguiente paso concreto y quién lo hace |
| `/sancho:discover` ... `/sancho:evolve` | Ejecuta una fase |
| `/sancho:checkpoint` | Guarda un resumen reanudable de la sesión |
| `/sancho:assess` | Analiza un proyecto existente: primero los riesgos, luego hoja de ruta o ideas reutilizables (solo lectura) |

Apps de Claude (web, escritorio, móvil) y Claude Code solo con la skill: `/sancho <comando>` con espacio, por ejemplo `/sancho status`, `/sancho verify uat`. O simplemente escribe "sancho, ¿cuál es el siguiente paso?".

## Panel (solo plugin)

Con el plugin, la app de Claude (pestaña Code) y Claude Code muestran también el panel de Sancho. No tienes que hacer nada, y aparece solo en carpetas con un proyecto Sancho:

- **una franja sobre el prompt**: fase y gate, bloqueos, el siguiente paso y quién lo hace, un enlace «dettagli»;
- **un aviso** cuando cambian el gate, el siguiente paso o el estado del ZIP;
- **un panel de detalles**, que se abre desde la franja o con `/sancho-panel`: las ocho fases, el siguiente paso, defectos y hallazgos de seguridad por gravedad, tareas y UAT, botones que escriben un comando en el prompt.

Solo lee `state.py status --json`. El ZIP para las apps de Claude no tiene panel, porque esas apps no pueden mostrarlo. De dónde viene cada dato: [hooks/README.md](hooks/README.md).

## Qué escribe en tu proyecto

```
.sancho/state.json  backlog.json  uat.json  handoffs/  standards/  checkpoints/
docs/constitution.md  spec.md  plan.md  adr/  uat/UAT.md  uat/uat.csv  security/
design/tokens.json  logo.svg  wireframes/
```

El ejemplo completo, ficticio, está en [examples/fieldlog](examples/fieldlog/WALKTHROUGH.md): una app Android y web con backend en contenedores, capturada a mitad de la fase VERIFY.

## Scripts de apoyo

| Script | Propósito |
|---|---|
| `state.py` | init, status, next, checklist/submit/approve/reject de los gates, skip con ADR, cambios de nivel, nuevas iteraciones, aprobaciones, decisiones |
| `coherence_check.py` | trazabilidad requisito -> historia -> criterio -> test/UAT, ciclos de dependencias |
| `complexity.py` | puntuaciones deterministas 1-10 de las tareas, recomendaciones de división |
| `uat_export.py` | UAT a Markdown y CSV (EN/IT/ES), reimportación de resultados |
| `cve_enrich.py` | lockfile o SBOM -> OSV -> NVD, KEV, EPSS -> informe; funciona también sin conexión, marcando con honestidad NOT RUN |
| `contrast_check.py` | contraste WCAG 2.x de los pares de design tokens |

## Desarrollo

```bash
python -I tests/validate.py      # 37 comprobaciones sin conexión: esquemas, fixtures, scripts, ejemplo, evals
claude plugin test .            # pruebas del panel (franja, detalles, avisos)
python tools/build.py            # regenera agents/ desde roles/ y construye dist/sancho.zip
python tools/set_owner.py --user <usuario-github> --name "<Nombre Apellido>"   # sustituye los marcadores una vez
```

`skills/sancho/roles/*.md` es la única fuente de los subagentes en `agents/`: la CI falla si divergen. Las evals de comportamiento están en `tests/evals.json` (23 escenarios).

## Créditos

Sancho incorpora y adapta reglas de **[ACP - Agent Communication Protocol](https://github.com/flaz78/agent-communication-protocol)** (MIT): estados de evidencia, niveles de riesgo, guardarraíles de código, el esquema de handoff y las reglas de confianza (ver [NOTICE](NOTICE)). Toma ideas, pero no código, de BMAD-METHOD (agentes por rol, historias autosuficientes), GitHub Spec Kit (spec -> plan -> tasks -> implement, controles entre artefactos), obra/superpowers (TDD, planes en archivos, verificación antes de terminar), Agent OS (estándares del proyecto) y Task Master (puntuación de complejidad y división de tareas). Las indicaciones de seguridad se basan en OWASP ASVS, MASVS y API Security Top 10, NVD, CVE.org, OSV.dev, CISA KEV y FIRST EPSS.

Sancho es un proyecto independiente, no afiliado a ninguno de los proyectos citados ni a Anthropic.

## Licencia

[MIT](LICENSE)
