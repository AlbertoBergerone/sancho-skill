# Sancho

**Il tuo scudiero fedele per i progetti software.** È una skill per Claude e un plugin per Claude Code: un team di sette agenti specializzati porta un progetto dalla prima idea alla release attraverso otto fasi, e ogni passaggio lo approvi tu.

[English](README.md) · [Italiano](README.it.md) · [Español](README.es.md)

**Documentazione:** [Guida all'installazione](docs/install.it.md) · [Guida d'uso](docs/guide.it.md) · [Progetto d'esempio](examples/fieldlog/WALKTHROUGH.md)

> Don Chisciotte sogna. Sancho tiene dritta la strada, si ricorda del budget e non dichiara mai vinta una battaglia senza le prove.

## Perché

Gli assistenti di programmazione con IA sono veloci ma smemorati. Saltano la pianificazione, inventano requisiti, dicono "i test passano" senza averli eseguiti e col tempo si allontanano dalle convenzioni del progetto. Sancho aggiunge la disciplina di progetto che manca, senza sommergere di processo i progetti piccoli:

- **Otto fasi, ognuna chiusa da un gate che approvi tu.** Ogni gate ha una checklist di qualità e un controllo di tracciabilità.
- **Sette ruoli specializzati** che si passano il lavoro con handoff strutturati e verificabili.
- **Prove, non dichiarazioni.** Ogni stato è VERIFIED, REPORTED, HYPOTHESIS o NOT RUN.
- **UAT guidati.** Ricevi test di accettazione passo per passo, scritti per tester non tecnici, in Markdown e come foglio di calcolo.
- **Security testing con priorità reali:** checklist OWASP, OSV e NVD, CISA KEV e FIRST EPSS. I test attivi girano solo su sistemi tuoi e approvati da te.
- **Coerenza nel tempo.** Gli standard di progetto vengono estratti dal codice reale e caricati task per task.
- **Proporzionalità.** Uno script usa e getta (L0) richiede tre domande. Un prodotto regolamentato (L3) richiede analisi d'impatto e piani di rollback.

## Le fasi

| # | Fase | Guida | Decidi tu |
|---|---|---|---|
| 0 | **DISCOVER**: principi, personas, piattaforme, vincoli, GDPR, nome | Analyst/PM | nome, piattaforme, livello di rischio |
| 1 | **SPECIFY**: requisiti, story autosufficienti, criteri di accettazione, scope MVP | Analyst/PM | priorità, cosa entra e cosa resta fuori |
| 2 | **PLAN**: matrice dello stack, architettura, ADR, container, brand, threat model | Architect + UX/UI + Security | stack, palette, logo |
| 3 | **TASKS**: task con dipendenze e complessità 1-10, checklist UAT | Analyst/PM + QA | ordine, milestone |
| 4 | **IMPLEMENT**: un task alla volta, test-driven, con gli standard applicati | Developer | questioni di scope |
| 5 | **VERIFY**: test, UAT guidati con te, sicurezza, accessibilità | QA + Security + UX/UI | esiti UAT, accettazione dei rischi |
| 6 | **RELEASE**: SemVer, changelog, deploy e rollback, store, monitoraggio | Release manager | go-live |
| 7 | **EVOLVE**: standard dal codice, retrospettiva, iterazione successiva | Release manager + Architect | cosa cambiare |

I progetti L0-L1 saltano PLAN, RELEASE ed EVOLVE di default. Puoi saltare qualsiasi fase, ma il motivo viene registrato in un ADR.

## Il team

Analyst/PM (orchestratore) · UX/UI designer · Architect · Developer · QA · Security engineer · Release manager.
In Claude Code lavorano come subagenti (`sancho:developer`, ...). Nelle app Claude la conversazione principale interpreta un ruolo dopo l'altro.

## Installazione

Le istruzioni complete passo per passo, con aggiornamento, disinstallazione, strumenti di sicurezza facoltativi e risoluzione dei problemi, sono nella **[guida all'installazione](docs/install.it.md)**. In breve:

| Usi | Fai così |
|---|---|
| Claude Code (consigliato: plugin) | `/plugin marketplace add AlbertoBergerone/sancho-skill`, poi `/plugin install sancho@sancho` |
| Claude Code (solo skill) | copia `skills/sancho` in `~/.claude/skills/sancho` |
| App Claude (web, desktop) | attiva l'esecuzione di codice, poi **Customize -> Skills -> + -> Upload a skill** con `sancho.zip` dalle [Releases](https://github.com/AlbertoBergerone/sancho-skill/releases) |

Requisiti: Python 3.9+ (solo libreria standard) dove gira Claude Code. Gli strumenti di sicurezza sono facoltativi.

Poi leggi la **[guida d'uso](docs/guide.it.md)**: il percorso, il promemoria dei comandi, una sessione d'esempio, cosa decidi in ogni fase, UAT, sicurezza.

## Quale Sancho usare

Sancho esiste in tre forme. La skill è la stessa: cambiano dove la usi, come la chiami e cosa c'è intorno.

| | Plugin | Solo skill | ZIP per le app Claude |
|---|---|---|---|
| **Dove** | Claude Code: terminale, scheda Code dell'app desktop, VS Code, JetBrains | Claude Code | Chat di claude.ai, app desktop e mobile |
| **Come lo chiami** | `/sancho:status`, `/sancho:verify` ... | `/sancho status`, `/sancho verify` ... | `/sancho status`, oppure a parole |
| **Il team** | Il lavoro va ai 7 subagenti `sancho:<ruolo>`; domande e approvazioni restano a te nella chat | La conversazione principale indossa un ruolo alla volta | Come la sola skill |
| **Pannello** | Fascia sopra il prompt, avvisi, `/sancho-panel` | No | No |
| **Script** | Python sul tuo computer | Python sul tuo computer | Nell'ambiente di Claude, con l'esecuzione di codice attiva |
| **Si installa** | `/plugin install sancho@sancho` | Copiando `skills/sancho` | Caricando `sancho.zip` |

### Con il plugin (consigliato in Claude Code)

1. Apri in Claude Code la cartella del progetto, vuota o esistente.
2. Scrivi `/sancho:discover` per un progetto nuovo, oppure `/sancho:assess` per analizzarne uno esistente.
3. Quando c'è un progetto Sancho, sopra il prompt compare la fascia: fase, stato del gate e prossimo passo. «dettagli» (o `/sancho-panel`) apre il pannello con le otto fasi, i problemi aperti e i pulsanti dei comandi.
4. A ogni gate leggi il riepilogo e rispondi "approvo" o di' cosa cambiare. Poi `/sancho:next` ti dice cosa viene dopo.

### Con la sola skill (Claude Code)

Per chi vuole un'installazione minima, senza plugin. Si lavora come con il plugin ma i comandi hanno lo spazio (`/sancho discover`, `/sancho next`), non c'è il pannello, e i ruoli li interpreta la conversazione principale, annunciando ogni cambio ("Cappello da architetto"). Plugin e sola skill usano la stessa cartella `.sancho/`, quindi sullo stesso progetto puoi passare dall'uno all'altra. In Claude Code installane uno solo, per non avere Sancho due volte.

### Nell'app Claude (chat)

Per chi non usa Claude Code. Carica `sancho.zip` una volta (vedi la [guida all'installazione](docs/install.it.md)), poi apri una nuova chat e scrivi "sancho, voglio creare..." oppure `/sancho discover`. Gli script girano nell'ambiente di Claude, quindi sul tuo computer non serve nulla, ma l'esecuzione di codice deve essere attiva. Qui non c'è il pannello: lo stato lo chiedi con `/sancho status`. Per scrivere e collaudare il codice nel tuo repository serve Claude Code.

## Comandi

| Plugin | Cosa fa |
|---|---|
| `/sancho:help [argomento]` | Guida su una schermata; argomenti: phases, roles, commands, uat, security, gates, files |
| `/sancho:status` | Fasi, task, UAT, difetti, sicurezza, blocchi, prossimo passo |
| `/sancho:next` | Il prossimo passo concreto e chi lo esegue |
| `/sancho:discover` ... `/sancho:evolve` | Esegue una fase |
| `/sancho:checkpoint` | Salva un riepilogo riprendibile della sessione |
| `/sancho:assess` | Analizza un progetto esistente: prima i rischi, poi roadmap o spunti da riusare (sola lettura) |

App Claude (web, desktop, mobile) e Claude Code con la sola skill: `/sancho <comando>` con lo spazio, per esempio `/sancho status`, `/sancho verify uat`. Oppure scrivi semplicemente "sancho, qual è il prossimo passo?".

## In squadra

Più persone sullo stesso progetto, ognuna con la propria copia: con `.sancho/team.json` ognuno ha il proprio prossimo passo, prenota task, casi UAT e difetti, vede cosa hanno fatto gli altri dopo un pull, e i gate hanno approvatori con nome. Lo stato di Sancho non va mai in conflitto nei merge. Vedi la [guida d'uso](docs/guide.it.md), capitolo 11.

## Pannello (solo plugin)

Con il plugin, l'app Claude (scheda Code) e Claude Code mostrano anche il pannello Sancho. Non devi fare nulla, e compare solo nelle cartelle con un progetto Sancho:

- **una fascia sopra il prompt**: fase e gate, blocchi, il prossimo passo e chi lo esegue, un link «dettagli»;
- **un avviso** quando cambiano il gate, il prossimo passo o lo stato dello ZIP;
- **un pannello dei dettagli**, che si apre dalla fascia o con `/sancho-panel`: le otto fasi, il prossimo passo, difetti e problemi di sicurezza per gravità, task e UAT, pulsanti che scrivono un comando nel prompt.

Legge soltanto `state.py status --json`. Lo ZIP per le app Claude non ha il pannello, perché quelle app non possono mostrarlo. Da dove viene ogni dato: [hooks/README.md](hooks/README.md).

## Cosa scrive nel tuo progetto

```
.sancho/state.json  backlog.json  uat.json  handoffs/  standards/  checkpoints/
docs/constitution.md  spec.md  plan.md  adr/  uat/UAT.md  uat/uat.csv  security/
design/tokens.json  logo.svg  wireframes/
```

L'esempio completo, fittizio, è in [examples/fieldlog](examples/fieldlog/WALKTHROUGH.md): un'app Android e web con backend in container, fotografata a metà della fase VERIFY.

## Script di supporto

| Script | Scopo |
|---|---|
| `state.py` | init, status, next, checklist/submit/approve/reject dei gate, skip con ADR, cambi di livello, nuove iterazioni, approvazioni, decisioni |
| `coherence_check.py` | tracciabilità requisito -> story -> criterio -> test/UAT, cicli nelle dipendenze |
| `complexity.py` | punteggi deterministici 1-10 dei task, suggerimenti di scomposizione |
| `uat_export.py` | UAT in Markdown e CSV (EN/IT/ES), reimportazione degli esiti |
| `cve_enrich.py` | lockfile o SBOM -> OSV -> NVD, KEV, EPSS -> report; funziona anche offline, marcando onestamente NOT RUN |
| `contrast_check.py` | contrasto WCAG 2.x delle coppie di design token |

## Sviluppo

```bash
python -I tests/validate.py      # 45 controlli offline: schemi, fixture, script, esempio, eval
claude plugin test .            # test del pannello (fascia, dettagli, avvisi)
python tools/build.py            # rigenera agents/ da roles/ e costruisce dist/sancho.zip
python tools/set_owner.py --user <utente-github> --name "<Nome Cognome>"   # sostituisce i segnaposto una volta
```

`skills/sancho/roles/*.md` è l'unica fonte dei subagenti in `agents/`: la CI fallisce se divergono. Le eval comportamentali sono in `tests/evals.json` (23 scenari).

## Riconoscimenti

Sancho incorpora e adatta regole da **[ACP - Agent Communication Protocol](https://github.com/flaz78/agent-communication-protocol)** (MIT): stati di evidenza, livelli di rischio, guardrail di coding, schema di handoff e regole di fiducia (vedi [NOTICE](NOTICE)). Riprende idee, ma non codice, da BMAD-METHOD (agenti per ruolo, story autosufficienti), GitHub Spec Kit (spec -> plan -> tasks -> implement, controlli tra artefatti), obra/superpowers (TDD, piani su file, verifica prima del completamento), Agent OS (standard di progetto) e Task Master (punteggio di complessità e scomposizione dei task). Le indicazioni di sicurezza si basano su OWASP ASVS, MASVS e API Security Top 10, NVD, CVE.org, OSV.dev, CISA KEV e FIRST EPSS.

Sancho è un progetto indipendente, non affiliato a nessuno dei progetti citati né ad Anthropic.

## Licenza

[MIT](LICENSE)
