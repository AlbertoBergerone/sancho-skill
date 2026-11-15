# Modalità squadra - piano di test

Cosa si prova: la modalità squadra di Sancho (tappe 1-4, `docs/design/team-mode.md`), da `main` a partire dal commit `1cf3fe8`. Obiettivo: decidere se pubblicarla come **v1.1.0**.

## 1. Tre livelli

| Livello | Cosa verifica | Chi | Stato |
|---|---|---|---|
| **Controlli automatici** | Gli script: eventi, prenotazioni, gate, VERIFY, compattazione, novità, hook, fogli UAT, modalità singola invariata. 46 controlli (`python -I tests/validate.py`) più 12 test del pannello (`claude plugin test .`), su Windows e Linux con Python 3.9 e 3.13 in GitHub Actions | automatico | verdi |
| **Eval di comportamento** | Che il modello usi davvero i comandi della squadra: passo personale, prenotare prima di lavorare, non approvare per altri, riassumere le novità (eval 24-27 in `tests/evals.json`, etichetta `team`) | Claude, su richiesta | da eseguire |
| **UAT** | L'esperienza vera, a parole, nell'app: 20 casi in [team-mode-UAT.md](team-mode-UAT.md) (foglio: [team-mode-uat.csv](team-mode-uat.csv)) | voi, in tre o da soli | da eseguire |

## 2. Chi fa cosa negli UAT

Tre ruoli, sempre gli stessi in tutti i casi:

| Nei casi | Nella sandbox | Ruoli Sancho |
|---|---|---|
| **A** | anna | developer, qa, **coordinatore** |
| **B** | bruno | developer |
| **C** | carla | developer, qa |

## 3. Preparare l'ambiente

**Plugin.** Installate (o aggiornate) il plugin Sancho da GitHub in Claude Code: `/plugin marketplace add AlbertoBergerone/sancho-skill`, poi `/plugin install sancho@sancho` (se è già installato: `/plugin` -> scheda **Marketplaces** -> sancho -> **Update marketplace**, oppure `claude plugin update sancho@sancho` dalla shell; vedi la [guida all'installazione](../install.it.md), sezione 8). Chi ha anche la mod di prova del pannello in `~/.claude/dev-mods` la tolga, per non vedere due fasce.

**Progetto di prova, due modi:**

- **Da soli, su un computer** (consigliato per il primo giro): `python tools/team_sandbox.py C:\sancho-prova` crea un "server" git locale e tre cartelle, `anna`, `bruno`, `carla`, ognuna con la propria email git. Aprite una sessione di Claude Code per cartella (tre sessioni affiancate nella scheda Code) e fate la parte di ciascuno nella sessione giusta. Il "push" e il "pull" vanno al server locale.
- **In tre, su tre computer**: create un repository di prova su GitHub con il contenuto di una delle cartelle della sandbox (o un vostro progetto vero di prova), ognuno lo clona con la propria email git, e si eseguono gli stessi casi.

Il progetto di prova ("Bacheca") è in IMPLEMENT, con 5 task e 4 casi UAT, e **non ha ancora la squadra**: crearla è il caso UAT-001.

## 4. Ordine e durata

I casi seguono l'avanzare del progetto, quindi vanno eseguiti in ordine:

1. **Squadra e task** (UAT-001 ... UAT-009): prenotazioni, revisioni, lavoro in parallelo. Circa 45 minuti.
2. **Novità** (UAT-010, UAT-011). 10 minuti.
3. **Gate** (UAT-012, UAT-013): servono tutti i task completati; per i task di prova basta un commit qualsiasi come prova. 15 minuti.
4. **VERIFY** (UAT-014 ... UAT-016). 20 minuti.
5. **Manutenzione** (UAT-017, UAT-018). 10 minuti.
6. **Pannello e modalità singola** (UAT-019, UAT-020): si possono fare in qualsiasi momento. 10 minuti.

Prima di ogni caso, chi lo esegue fa `git pull` (o lo chiede a Sancho).

## 5. Come registrare esiti e difetti

- Per ogni caso: **superato**, **fallito** (scrivete cosa avete visto), **bloccato** (scrivete perché). Nel Markdown con le caselle, oppure nel CSV (colonne Esito, Eseguito da, Note).
- Un difetto: id del caso, cosa avete scritto a Sancho, cosa ha risposto, cosa vi aspettavate. Se possibile, l'output di `state.py status` e i file `.sancho/log/*.jsonl` coinvolti. Si possono aprire come issue su GitHub con il titolo `UAT-0xx: ...`.
- Gravità: **blocker** (impedisce di usare la squadra o rompe lo stato), **major** (risultato sbagliato con un aggiramento), **minor**, **nit**.
- Il CSV compilato si può riportare qui: lo importo e tengo traccia dei difetti.

## 6. Quando è pronta per la v1.1.0

- Tutti i 20 casi eseguiti; nessun difetto **blocker** o **major** aperto.
- Le 4 eval di comportamento passano.
- I controlli automatici restano verdi su GitHub.
- Nessun conflitto di merge sui file di `.sancho/` in tutto il giro (UAT-005, UAT-009, UAT-014, UAT-017).

Poi: data nel CHANGELOG, versione 1.1.0 in `plugin.json` e `marketplace.json`, tag `v1.1.0`.
