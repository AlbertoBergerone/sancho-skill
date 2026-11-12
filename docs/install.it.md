# Sancho - guida all'installazione

[English](install.en.md) · [Italiano](install.it.md) · [Español](install.es.md) · Poi: [guida d'uso](guide.it.md)

## 1. Scegli la tua configurazione

| Usi | Installa | Cosa ottieni |
|---|---|---|
| **Claude Code** (terminale, scheda Code dell'app desktop, VS Code, JetBrains) | **A. Plugin** (consigliato) | skill + 7 subagenti + comandi `/sancho:...` + pannello Sancho |
| Claude Code, ma vuoi un'installazione minima | **B. Solo skill** | skill; i ruoli li interpreta la conversazione principale; comando `/sancho` |
| **App Claude** (claude.ai web, desktop, mobile) | **C. Carica lo ZIP** | skill; le parli in linguaggio naturale |

Tutte e tre usano la stessa skill. Puoi installarla anche in più posti.

## 2. Requisiti

- **Python 3.9 o superiore** sul computer dove gira Claude Code. Gli script di supporto usano solo la libreria standard, quindi non serve `pip install`. Nell'app Claude gli script girano nell'ambiente di Claude e in locale non ti serve nulla.
  - Verifica: `python --version` (Windows) o `python3 --version` (macOS/Linux).
  - Windows: installalo da [python.org](https://www.python.org/downloads/) spuntando **Add python.exe to PATH**, oppure esegui `winget install Python.Python.3.12`.
- **Claude Code**, per le opzioni A e B. I comandi dei plugin qui sotto richiedono una versione recente.
- **App Claude**, per l'opzione C: qualsiasi piano. L'**esecuzione di codice** deve essere attiva (vedi 5).
- **Facoltativi:** git e gli strumenti di sicurezza della sezione 6.

## 3. Opzione A - Plugin per Claude Code (consigliata)

### Da GitHub

> **Dove scrivere i comandi.** I comandi che iniziano con `/` (come `/plugin ...`) si scrivono **dentro una sessione di Claude Code**, non in PowerShell o nel Terminale: prima esegui `claude`, poi scrivili al suo prompt. Da PowerShell o dal Terminale usa invece i comandi equivalenti `claude plugin ...` riportati più sotto. Se `claude` non viene riconosciuto, Claude Code non è ancora installato: vedi la pagina ufficiale di installazione di Claude Code (su Windows: `irm https://claude.ai/install.ps1 | iex`).

1. Apri un terminale nella cartella del progetto e avvia Claude Code: `claude`
2. Aggiungi il marketplace di Sancho (una volta per computer):
   ```
   /plugin marketplace add AlbertoBergerone/sancho-skill
   ```
   Dovresti vedere `Successfully added marketplace: sancho`.
3. Installa il plugin:
   ```
   /plugin install sancho@sancho
   ```
   Si apre il pannello del plugin. Scegli l'ambito:
   - **Install for you (user scope)**: Sancho è disponibile in tutti i progetti. Consigliato.
   - **Install for all collaborators on this repository (project scope)**: lo riceve tutto il team. Ogni collega esegue comunque l'installazione una volta.
   - **Install for you, in this repo only (local scope)**.
4. Se il riepilogo dice `Run /reload-plugins to apply`, Claude Code esegue il ricaricamento da solo. Altrimenti il plugin è subito attivo.
5. Verifica: digita `/sancho:` e compaiono i comandi (`/sancho:help`, `/sancho:next`, ...). Poi lancia `/sancho:help`.

Dalla shell, senza aprire una sessione:

```bash
claude plugin marketplace add AlbertoBergerone/sancho-skill
claude plugin install sancho@sancho
```

Nell'**app desktop** (scheda Code, sessione locale): aggiungi il marketplace come sopra, poi clicca **+** accanto alla casella del prompt, scegli **Add plugins** (oppure **Plugins**, poi **Browse plugins**) e seleziona Sancho.

### Il pannello Sancho

Il plugin aggiunge anche un pannello nell'app Claude (scheda Code) e in Claude Code: una fascia sopra il prompt con fase, gate e prossimo passo, avvisi quando cambiano e un pannello dei dettagli (`/sancho-panel`). Compare da solo nelle cartelle con un progetto Sancho e usa lo stesso Python. Le opzioni B e C non lo hanno.

### Da una copia locale (per provarlo prima di pubblicarlo)

```
/plugin marketplace add ./sancho-skill
/plugin install sancho@sancho
```

Inizia il percorso relativo con `./` o `../`: un semplice `nome/nome` viene interpretato come repository GitHub. Per caricarlo per una sola sessione, senza installarlo, avvia Claude Code con `claude --plugin-dir ./sancho-skill`.

## 4. Opzione B - Solo skill (Claude Code)

Copia la cartella `skills/sancho` di questo repository nella tua cartella delle skill.

**Windows (PowerShell)**, dalla cartella del repository:
```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
Copy-Item -Recurse -Force .\skills\sancho "$env:USERPROFILE\.claude\skills\sancho"
```

**macOS / Linux**:
```bash
mkdir -p ~/.claude/skills && cp -R skills/sancho ~/.claude/skills/
```

Per un solo progetto, copiala invece in `<progetto>/.claude/skills/sancho`. Riavvia Claude Code, poi scrivi `/sancho help`.

Senza il plugin non ci sono subagenti né comandi `/sancho:...`. La conversazione principale interpreta i sette ruoli uno dopo l'altro, e tu scrivi `/sancho next`, `/sancho verify uat` e così via.

## 5. Opzione C - App Claude (claude.ai, desktop, mobile)

1. Procurati `sancho.zip`:
   - dalla pagina [Releases](https://github.com/AlbertoBergerone/sancho-skill/releases) del repository, oppure
   - generandolo: `python tools/build.py` crea `dist/sancho.zip`.

   **Non** usare il pulsante verde di GitHub "Code -> Download ZIP": quell'archivio contiene tutto il repository e il caricamento fallisce, perché `SKILL.md` non si trova in una cartella `sancho/` di primo livello.
2. Attiva l'esecuzione di codice: **Impostazioni -> Funzionalità (Capabilities) -> Esecuzione di codice e creazione di file** (nella nuova interfaccia si chiama **Create and edit files**).
3. Carica: **Customize -> Skills -> "+" -> Create skill -> Upload a skill**, poi scegli `sancho.zip`.
4. Controlla che l'interruttore accanto a Sancho sia acceso.
5. Prova in una nuova chat: "sancho, aiuto".

Piani Team ed Enterprise: skill ed esecuzione di codice devono essere consentite per l'organizzazione. In Enterprise le attiva un owner in **Organization settings -> Plugins & skills**. Un owner può anche disattivare la creazione di skill da parte degli utenti. I nomi dei menu possono cambiare tra una versione e l'altra dell'app.

## 6. Strumenti facoltativi per i test di sicurezza

Sancho funziona anche senza. Ciò che manca viene segnalato come **NOT RUN**, con il comando per eseguirlo in seguito. Installali dalle pagine ufficiali:

| Strumento | A cosa serve | Sito ufficiale |
|---|---|---|
| gitleaks | segreti nel repository e nella sua storia | github.com/gitleaks/gitleaks |
| Semgrep | analisi statica (SAST) | semgrep.dev |
| osv-scanner | vulnerabilità delle dipendenze | google.github.io/osv-scanner |
| Syft | SBOM in formato CycloneDX | github.com/anchore/syft |
| Trivy | scansione di immagini container e configurazioni | trivy.dev |
| OWASP ZAP | DAST sul tuo ambiente locale o di test (immagine Docker) | zaproxy.org |
| MobSF | analisi delle app Android/iOS (immagine Docker) | github.com/MobSF/Mobile-Security-Framework-MobSF |
| Docker Desktop | esegue container, ZAP e MobSF | docker.com |

**Chiave API NVD (facoltativa).** Con una chiave il limite di richieste NVD è più alto. Richiedila su nvd.nist.gov (Developers -> Request an API key), poi impostala come variabile d'ambiente. Non incollarla mai in chat.
- Windows: `setx NVD_API_KEY "la-tua-chiave"`, poi apri un nuovo terminale.
- macOS/Linux: aggiungi `export NVD_API_KEY="la-tua-chiave"` al profilo della shell.

## 7. Verifica l'installazione

- In Claude Code: `/sancho:help` (plugin) o `/sancho help` (solo skill). Deve comparire il tour delle 8 fasi.
- Nell'app Claude: scrivi "sancho, aiuto".
- Da un clone del repository: `python -I tests/validate.py` deve indicare tutti i controlli superati.

## 8. Aggiornamento

| Configurazione | Come |
|---|---|
| Plugin | `/plugin` -> scheda **Marketplaces** -> sancho -> **Update marketplace**, oppure `claude plugin update sancho@sancho` dalla shell. L'aggiornamento automatico è disattivato di default per i marketplace di terzi; puoi attivarlo nella stessa scheda. |
| Solo skill | Sostituisci la cartella `~/.claude/skills/sancho` con quella nuova. |
| App Claude | Rimuovi la vecchia skill in **Customize -> Skills** e carica il nuovo ZIP. |

Gli aggiornamenti non toccano i file dei tuoi progetti (`.sancho/`, `docs/`, `design/`).

## 9. Disinstallazione

- Plugin: `/plugin uninstall sancho@sancho` (oppure `claude plugin uninstall sancho@sancho`). Per rimuovere anche il marketplace: `/plugin marketplace remove sancho`.
- Solo skill: cancella `~/.claude/skills/sancho`.
- App Claude: spegni l'interruttore, oppure elimina la skill in **Customize -> Skills**.

Le cartelle `.sancho/` dei tuoi progetti restano dove sono: appartengono ai progetti.

## 10. Risoluzione dei problemi

| Problema | Soluzione |
|---|---|
| `Termine '/plugin' non riconosciuto` in PowerShell | Hai scritto un comando di Claude Code in PowerShell. Esegui prima `claude` e scrivilo lì, oppure usa `claude plugin marketplace add .\sancho-skill` da PowerShell. |
| I comandi `/sancho:` non compaiono | Esegui `/reload-plugins`; apri `/plugin` e guarda la scheda **Errors**; verifica che `claude plugin list` mostri sancho come abilitato. |
| `/plugin marketplace add sancho-skill` fallisce | Per una cartella locale, inizia il percorso con `./`. Per GitHub, usa `utente/repo` senza `https://github.com/`. |
| "python non trovato", oppure `python3` apre il Microsoft Store (Windows) | Installa Python da python.org con **Add to PATH**. Sancho usa `python` quando `python3` non è disponibile. |
| Il caricamento dello ZIP viene rifiutato | Usa `sancho.zip` dalle Releases o da `tools/build.py`: l'archivio deve contenere `sancho/SKILL.md`. |
| I controlli di sicurezza risultano NOT RUN | Lo strumento non è installato o la rete è bloccata. Installalo (sezione 6) e rilancia `/sancho:verify security`. |
| I subagenti non vengono mai usati | Esistono solo con il plugin (opzione A). Con l'opzione B i ruoli li interpreta la conversazione principale, ed è normale. |

Poi: [guida d'uso](guide.it.md).
