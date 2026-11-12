# Sancho - guía de instalación

[English](install.en.md) · [Italiano](install.it.md) · [Español](install.es.md) · Después: [guía de uso](guide.es.md)

## 1. Elige tu configuración

| Usas | Instala | Qué obtienes |
|---|---|---|
| **Claude Code** (terminal, pestaña Code de la app de escritorio, VS Code, JetBrains) | **A. Plugin** (recomendado) | skill + 7 subagentes + comandos `/sancho:...` + panel de Sancho |
| Claude Code, pero quieres una instalación mínima | **B. Solo la skill** | skill; los roles los interpreta la conversación principal; comando `/sancho` |
| **App de Claude** (claude.ai web, escritorio, móvil) | **C. Subir el ZIP** | skill; le hablas en lenguaje natural |

Las tres usan la misma skill. Puedes instalarla en más de un sitio.

## 2. Requisitos

- **Python 3.9 o superior** en el ordenador donde se ejecuta Claude Code. Los scripts de apoyo solo usan la biblioteca estándar, así que no hace falta `pip install`. En la app de Claude los scripts se ejecutan en el entorno de Claude y en local no necesitas nada.
  - Comprobación: `python --version` (Windows) o `python3 --version` (macOS/Linux).
  - Windows: instálalo desde [python.org](https://www.python.org/downloads/) marcando **Add python.exe to PATH**, o ejecuta `winget install Python.Python.3.12`.
- **Claude Code**, para las opciones A y B. Los comandos de plugins de abajo requieren una versión reciente.
- **App de Claude**, para la opción C: cualquier plan. La **ejecución de código** debe estar activada (ver 5).
- **Opcionales:** git y las herramientas de seguridad de la sección 6.

## 3. Opción A - Plugin para Claude Code (recomendada)

### Desde GitHub

> **Dónde escribir los comandos.** Los comandos que empiezan por `/` (como `/plugin ...`) se escriben **dentro de una sesión de Claude Code**, no en PowerShell ni en el Terminal: primero ejecuta `claude` y luego escríbelos en su prompt. Desde PowerShell o el Terminal usa los comandos equivalentes `claude plugin ...` que aparecen más abajo. Si `claude` no se reconoce, Claude Code aún no está instalado: consulta la página oficial de instalación de Claude Code (en Windows: `irm https://claude.ai/install.ps1 | iex`).

1. Abre un terminal en la carpeta del proyecto e inicia Claude Code: `claude`
2. Añade el marketplace de Sancho (una vez por ordenador):
   ```
   /plugin marketplace add AlbertoBergerone/sancho-skill
   ```
   Deberías ver `Successfully added marketplace: sancho`.
3. Instala el plugin:
   ```
   /plugin install sancho@sancho
   ```
   Se abre el panel del plugin. Elige el ámbito:
   - **Install for you (user scope)**: Sancho está disponible en todos los proyectos. Recomendado.
   - **Install for all collaborators on this repository (project scope)**: lo recibe todo el equipo. Cada compañero ejecuta igualmente la instalación una vez.
   - **Install for you, in this repo only (local scope)**.
4. Si el resumen dice `Run /reload-plugins to apply`, Claude Code hace la recarga por ti. Si no, el plugin queda activo de inmediato.
5. Comprobación: escribe `/sancho:` y aparecen los comandos (`/sancho:help`, `/sancho:next`, ...). Después ejecuta `/sancho:help`.

Desde la shell, sin abrir una sesión:

```bash
claude plugin marketplace add AlbertoBergerone/sancho-skill
claude plugin install sancho@sancho
```

En la **app de escritorio** (pestaña Code, sesión local): añade el marketplace como arriba, luego pulsa **+** junto al cuadro del prompt, elige **Add plugins** (o **Plugins** y después **Browse plugins**) y selecciona Sancho.

### El panel de Sancho

El plugin añade también un panel en la app de Claude (pestaña Code) y en Claude Code: una franja sobre el prompt con fase, gate y siguiente paso, avisos cuando cambian y un panel de detalles (`/sancho-panel`). Aparece solo en carpetas con un proyecto Sancho y usa el mismo Python. Las opciones B y C no lo tienen.

### Desde una copia local (para probarlo antes de publicarlo)

```
/plugin marketplace add ./sancho-skill
/plugin install sancho@sancho
```

Empieza la ruta relativa con `./` o `../`: un simple `nombre/nombre` se interpreta como un repositorio de GitHub. Para cargarlo en una sola sesión, sin instalarlo, inicia Claude Code con `claude --plugin-dir ./sancho-skill`.

## 4. Opción B - Solo la skill (Claude Code)

Copia la carpeta `skills/sancho` de este repositorio en tu carpeta de skills.

**Windows (PowerShell)**, desde la carpeta del repositorio:
```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\sancho "$env:USERPROFILE\.claude\skills\sancho"
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/skills && cp -R skills/sancho ~/.claude/skills/
```

Para un solo proyecto, cópiala en `<proyecto>/.claude/skills/sancho`. Reinicia Claude Code y escribe `/sancho help`.

Sin el plugin no hay subagentes ni comandos `/sancho:...`. La conversación principal interpreta los siete roles uno tras otro, y tú escribes `/sancho next`, `/sancho verify uat`, etc.

## 5. Opción C - App de Claude (claude.ai, escritorio, móvil)

1. Consigue `sancho.zip`:
   - desde la página [Releases](https://github.com/AlbertoBergerone/sancho-skill/releases) del repositorio, o
   - generándolo: `python tools/build.py` crea `dist/sancho.zip`.

   **No** uses el botón verde de GitHub "Code -> Download ZIP": ese archivo contiene todo el repositorio y la subida falla, porque `SKILL.md` no está en una carpeta `sancho/` de primer nivel.
2. Activa la ejecución de código: **Configuración -> Capacidades (Capabilities) -> Ejecución de código y creación de archivos** (en la interfaz nueva se llama **Create and edit files**).
3. Sube la skill: **Customize -> Skills -> "+" -> Create skill -> Upload a skill**, y elige `sancho.zip`.
4. Comprueba que el interruptor junto a Sancho esté activado.
5. Prueba en un chat nuevo: "sancho, ayuda".

Planes Team y Enterprise: las skills y la ejecución de código deben estar permitidas para la organización. En Enterprise las activa un owner en **Organization settings -> Plugins & skills**. Un owner también puede desactivar la creación de skills por parte de los usuarios. Los nombres de los menús pueden cambiar entre versiones de la app.

## 6. Herramientas opcionales para las pruebas de seguridad

Sancho funciona sin ellas. Lo que falte se indica como **NOT RUN**, con el comando para ejecutarlo más tarde. Instálalas desde sus páginas oficiales:

| Herramienta | Para qué sirve | Sitio oficial |
|---|---|---|
| gitleaks | secretos en el repositorio y en su historial | github.com/gitleaks/gitleaks |
| Semgrep | análisis estático (SAST) | semgrep.dev |
| osv-scanner | vulnerabilidades de las dependencias | google.github.io/osv-scanner |
| Syft | SBOM en formato CycloneDX | github.com/anchore/syft |
| Trivy | escaneo de imágenes de contenedor y configuraciones | trivy.dev |
| OWASP ZAP | DAST en tu entorno local o de pruebas (imagen Docker) | zaproxy.org |
| MobSF | análisis de apps Android/iOS (imagen Docker) | github.com/MobSF/Mobile-Security-Framework-MobSF |
| Docker Desktop | ejecuta contenedores, ZAP y MobSF | docker.com |

**Clave API de NVD (opcional).** Con una clave, el límite de peticiones a NVD es más alto. Solicítala en nvd.nist.gov (Developers -> Request an API key) y configúrala como variable de entorno. Nunca la pegues en el chat.
- Windows: `setx NVD_API_KEY "tu-clave"`, y luego abre un terminal nuevo.
- macOS/Linux: añade `export NVD_API_KEY="tu-clave"` al perfil de tu shell.

## 7. Comprueba la instalación

- En Claude Code: `/sancho:help` (plugin) o `/sancho help` (solo la skill). Debe aparecer el recorrido por las 8 fases.
- En la app de Claude: escribe "sancho, ayuda".
- Desde un clon del repositorio: `python -I tests/validate.py` debe indicar que todas las comprobaciones pasan.

## 8. Actualización

| Configuración | Cómo |
|---|---|
| Plugin | `/plugin` -> pestaña **Marketplaces** -> sancho -> **Update marketplace**, o `claude plugin update sancho@sancho` desde la shell. La actualización automática está desactivada por defecto en los marketplaces de terceros; puedes activarla en la misma pestaña. |
| Solo la skill | Sustituye la carpeta `~/.claude/skills/sancho` por la nueva. |
| App de Claude | Elimina la skill antigua en **Customize -> Skills** y sube el ZIP nuevo. |

Las actualizaciones no tocan los archivos de tus proyectos (`.sancho/`, `docs/`, `design/`).

## 9. Desinstalación

- Plugin: `/plugin uninstall sancho@sancho` (o `claude plugin uninstall sancho@sancho`). Para olvidar también el marketplace: `/plugin marketplace remove sancho`.
- Solo la skill: borra `~/.claude/skills/sancho`.
- App de Claude: apaga el interruptor, o elimina la skill en **Customize -> Skills**.

Las carpetas `.sancho/` de tus proyectos se quedan donde están: pertenecen a tus proyectos.

## 10. Solución de problemas

| Problema | Solución |
|---|---|
| `'/plugin' no se reconoce` en PowerShell | Escribiste un comando de Claude Code en PowerShell. Ejecuta primero `claude` y escríbelo allí, o usa `claude plugin marketplace add .\sancho-skill` desde PowerShell. |
| No aparecen los comandos `/sancho:` | Ejecuta `/reload-plugins`; abre `/plugin` y revisa la pestaña **Errors**; comprueba que `claude plugin list` muestra sancho como habilitado. |
| `/plugin marketplace add sancho-skill` falla | Para una carpeta local, empieza la ruta con `./`. Para GitHub, usa `usuario/repo` sin `https://github.com/`. |
| "python no encontrado", o `python3` abre la Microsoft Store (Windows) | Instala Python desde python.org con **Add to PATH**. Sancho usa `python` cuando `python3` no está disponible. |
| La subida del ZIP es rechazada | Usa `sancho.zip` de Releases o de `tools/build.py`: el archivo debe contener `sancho/SKILL.md`. |
| Las comprobaciones de seguridad salen como NOT RUN | La herramienta no está instalada o la red está bloqueada. Instálala (sección 6) y vuelve a ejecutar `/sancho:verify security`. |
| Nunca se usan los subagentes | Solo existen con el plugin (opción A). Con la opción B los roles los interpreta la conversación principal, y es lo esperado. |

Después: [guía de uso](guide.es.md).
