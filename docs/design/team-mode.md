# Sancho in squadra - progetto della modalità team

Stato: **tappa 1 implementata** (non ancora rilasciata): squadra, registro eventi, `claim`/`release`/`task`/`review`, `next` personale e `--team`. Tappe 2-4 da fare. Versione di partenza: Sancho 1.0.0.

## 1. Il problema

Sancho 1.0 accompagna **una persona**: c'è un solo "utente", un solo prossimo passo, e lo stato vive in pochi file JSON riscritti per intero. In tre sullo stesso repository succede questo:

| Oggi | Effetto in squadra |
|---|---|
| `backlog.json` e `uat.json` sono file unici, riscritti a ogni modifica di stato (il modello li modifica a mano: "Set it `in_progress` in the backlog") | Due persone chiudono due task in parallelo: conflitto di merge su righe vicine, da risolvere a mano |
| `task.owner` è un ruolo (`developer`, `qa`), non una persona | Nessuno sa chi sta facendo cosa; non si può "prendere" un task |
| `state.py next` restituisce un solo passo | Tutti e tre ricevono lo stesso task e ci lavorano insieme |
| Approvazioni con `granted_by: user`, gate con solo `approved_at` | Non si sa chi ha approvato; chiunque può approvare |
| Lo stato si legge "com'è adesso" | Dopo un `git pull` nessuno ti dice cosa è cambiato e cosa ti riguarda |

## 2. Obiettivi e limiti

**Obiettivi**
1. Ognuno sa **cosa deve fare lui** (`next` personale) e **cosa hanno fatto gli altri** dall'ultimo pull.
2. **Nessun conflitto di merge** sui file di stato di Sancho nel lavoro normale.
3. **Un task, una persona**: si prenota, si vede chi l'ha preso, i doppioni vengono segnalati.
4. Gate e approvazioni **con un nome**, e solo da chi è autorizzato.
5. **Compatibile**: un progetto senza squadra funziona esattamente come oggi.

**Limiti dichiarati**
- La coordinazione passa da **git**: Sancho vede il lavoro degli altri solo dopo che è stato pushato e tu hai fatto pull. Non è un sistema in tempo reale.
- L'identità viene da `git config user.email`: serve a **coordinarsi**, non è una protezione. Chi vuole può fingersi un altro.
- Le fasi restano **una sequenza unica per il progetto**: il lavoro in parallelo avviene dentro IMPLEMENT e VERIFY (e nella stesura dei documenti), non tra fasi diverse.

## 3. Le idee chiave

### 3.1 La squadra: `.sancho/team.json`

La sua presenza attiva la modalità team; senza, Sancho resta in modalità singola.

```json
{
  "protocol": "sancho/1.1",
  "members": [
    { "id": "danilo", "name": "Danilo", "emails": ["danilo@example.com"], "roles": ["analyst-pm", "qa"], "coordinator": true },
    { "id": "luca",   "name": "Luca",   "emails": ["luca@example.com"],   "roles": ["developer", "architect"] },
    { "id": "sara",   "name": "Sara",   "emails": ["sara@example.com"],   "roles": ["developer", "ux-ui-designer"] }
  ],
  "approvers": { "default": ["danilo"], "release": ["danilo", "luca"] },
  "quorum": { "default": 1, "release": 2 },
  "four_eyes": true,
  "claim_stale_days": 3
}
```

- **Chi sono io**: `git config user.email` confrontato con `emails`; in alternativa la variabile `SANCHO_USER=<id>`. Email sconosciuta: Sancho lo dice e lavora in sola lettura.
- **`roles`**: quali cappelli porta ciascuno. Il `next` personale propone solo lavoro di quei ruoli.
- **`coordinator`**: chi apre e chiude le fasi (`start`, `submit`) e compatta il registro (3.3).
- **`approvers` / `quorum`**: chi approva i gate, per fase, e quante approvazioni servono.
- **`four_eyes`**: chi ha scritto un task non può essere chi lo revisiona come QA.

### 3.2 Il registro degli eventi: un file per persona

Il cuore della proposta. Invece di modificare `backlog.json` e `uat.json`, ogni cambiamento di stato **si aggiunge in fondo** a un file personale:

```
.sancho/log/danilo.jsonl
.sancho/log/luca.jsonl
.sancho/log/sara.jsonl
```

Una riga per evento, solo aggiunte, mai modifiche:

```json
{"at":"2026-11-14T09:12:03+01:00","by":"luca","event":"claim","task":"T-007","branch":"t-007-login-offline"}
{"at":"2026-11-14T11:40:55+01:00","by":"luca","event":"task_status","task":"T-007","status":"ready_for_review","evidence":[{"kind":"commit","ref":"a1b2c3d"}]}
{"at":"2026-11-14T15:02:10+01:00","by":"danilo","event":"uat_result","case":"UAT-004","result":"fail","defects":["DEF-003"]}
{"at":"2026-11-14T15:30:00+01:00","by":"danilo","event":"gate_approve","phase":"verify"}
```

Perché funziona:
- **Ognuno scrive solo il proprio file**, quindi due persone non toccano mai lo stesso file di stato: niente conflitti.
- Se la stessa persona lavora da due computer, il suo file riceve aggiunte da due parti: `.gitattributes` con `.sancho/log/*.jsonl merge=union` fa unire a git le righe di entrambi senza conflitto.
- Lo stato **corrente** si ottiene così: `backlog.json` / `uat.json` (il piano) + tutti gli eventi in ordine di `at`. Lo calcolano `status` e `next`; nessuno lo scrive.
- È anche la **storia**: chi ha fatto cosa e quando, senza scavare nei commit.

Eventi previsti:

| Evento | Campi | Chi |
|---|---|---|
| `claim` / `release` | `task`, `branch` | chi prende o lascia il task |
| `task_status` | `task`, `status`, `evidence`, `blocked_reason`, `note` | chi lavora o revisiona |
| `review` | `task`, `outcome` (`approved`/`changes`), `findings` | QA, diverso dall'autore se `four_eyes` |
| `uat_assign` / `uat_result` | `case`, `to` / `result`, `defects`, `notes` | coordinatore / collaudatore |
| `defect_open` / `defect_status` | `defect`, `severity`, `status` | chiunque / chi lo corregge |
| `decision` | `summary`, `adr` | chi ha deciso (al posto di `decided_by: user`) |
| `gate_submit` / `gate_approve` / `gate_reject` | `phase`, `reason` | coordinatore / approvatori |

### 3.3 Compattazione al gate

Il registro cresce. Alla chiusura di un gate il **coordinatore** esegue `state.py compact`:
1. riporta lo stato calcolato dentro `backlog.json` e `uat.json`;
2. sposta le righe in `.sancho/log/archive/<fase>-<iterazione>.jsonl`;
3. fa un commit unico `chore(sancho): compact log at <fase> gate`.

È l'unico momento in cui si riscrivono i file condivisi, ed è uno solo a farlo. Se qualcuno pusha un evento dopo la compattazione, l'evento resta nel suo file e viene applicato normalmente.

### 3.4 Prenotare un task

```
state.py claim T-007            # prende il task e annota il ramo corrente
state.py release T-007          # lo lascia
```

- `claim` rifiuta un task già preso da un altro, con dipendenze aperte o di un ruolo che non hai.
- **Prenotazioni concorrenti** (due persone prendono T-007 prima di vedere il push dell'altro): dopo il pull vince il `claim` con `at` più vecchio (a parità, l'`id` in ordine alfabetico). Chi perde se lo vede in testa a `next`: "T-007 era già di Luca dalle 09:12: lascialo con `release` o mettetevi d'accordo".
- Il claim conta solo se gli altri lo vedono: Sancho **propone** di fare commit e push subito ("Faccio commit e push della prenotazione?"). Non pusha mai senza chiedere.
- Una prenotazione senza eventi da più di `claim_stale_days` compare come **ferma** nella vista di squadra.

Nel piano (fase TASKS) il coordinatore può già proporre un `assignee` per task: nuovo campo facoltativo in `backlog.json`. È un suggerimento: fa fede il `claim`.

### 3.5 Il prossimo passo per ciascuno

Con la squadra, `state.py next` risponde **per te** (`--me`, predefinito) in quest'ordine:

1. **Problemi**: file non validi, prenotazione persa (3.4), un tuo task respinto in revisione.
2. **Il tuo lavoro in corso**: task prenotati da te in `in_progress`.
3. **Revisioni per te** (se hai il ruolo `qa`): task `ready_for_review` di altri.
4. **Approvazioni per te**: gate in `awaiting_approval` di cui sei approvatore e non hai ancora approvato.
5. **Difetti** blocker e major assegnati a te o non assegnati, se sei `developer`.
6. **Casi UAT** assegnati a te.
7. **Un nuovo task**: il primo pronto, non prenotato, di un tuo ruolo (stesso ordine di oggi: priorità della storia, poi id), con l'invito a prenderlo.
8. Niente per te: lo dice, e dice chi sta bloccando cosa ("Aspetti l'approvazione di Luca sul gate VERIFY").

`state.py next --team` dà una riga per persona:

```
danilo  approva il gate VERIFY (1 di 1)
luca    T-007 in revisione da Danilo · T-009 pronto per te
sara    T-008 in corso da 2 giorni (ramo t-008-sync)
libero  T-010, T-011 pronti, nessuno li ha presi
```

### 3.6 Cosa è cambiato dall'ultimo pull

```
state.py since            # dal tuo ultimo "visto"
state.py since v1.2.0     # da un riferimento git qualsiasi
```

- Il punto "visto" è personale e **fuori da git**: `.git/sancho/last-seen` (commit ed eventi letti).
- Legge `git log <visto>..HEAD` per `.sancho/` e i documenti (`docs/spec.md`, `docs/plan.md`, ADR) e gli eventi nuovi; raggruppa per persona e mette in cima ciò che ti riguarda:

```
Da ieri 18:20 (7 commit):
  Ti riguarda: Danilo ha respinto T-007 in revisione (2 findings) · nuovo difetto DEF-003 major su UAT-004
  Luca: T-009 completato · ADR-0004 "Coda offline con SQLite"
  Sara: ha preso T-008 · spec.md modificata (S-012, 2 criteri)
  Gate: nessun cambiamento (IMPLEMENT in corso)
```

- **Hook git facoltativo**: `state.py hooks install` aggiunge un `post-merge` che dopo ogni `git pull` stampa `since` ed esegue `validate`. Va installato da ciascuno, Sancho chiede prima di farlo.
- **Pannello del plugin**: una sezione "Novità" e un avviso quando arrivano eventi che ti riguardano, più una sezione "Squadra" con la vista di `next --team`.

### 3.7 Gate e approvazioni con un nome

- `submit` lo può fare solo il coordinatore; `approve` / `reject` solo gli approvatori di quella fase.
- Il gate passa ad `approved` quando gli `gate_approve` raggiungono il `quorum`; un solo `gate_reject` lo rimanda indietro (con motivo).
- Nello stato: `gate.approved_by: ["danilo", "luca"]`, `approvals[].granted_by` con l'id del membro, `decisions[].decided_by` con l'id.
- Le regole di sicurezza restano: i test attivi in produzione richiedono comunque approvazione, ambito e finestra, ora con il nome di chi li ha concessi.

### 3.8 Documenti e fasi di scrittura

DISCOVER, SPECIFY e PLAN producono documenti (`spec.md`, `plan.md`, ADR), già gestiti bene da git e dalle pull request. Regole:
- L'intervista di una fase la conduce **una persona** (di solito il coordinatore); gli altri rivedono il documento in PR.
- Dopo ogni merge che tocca questi file, `validate` e il controllo di coerenza (`coherence_check.py`) dicono se il documento unito è ancora coerente con backlog e criteri. L'hook `post-merge` lo fa da solo.
- ID nuovi (`S-0xx`, `T-0xx`, `DEF-0xx`) presi in parallelo possono collidere: il controllo C0 "duplicate id" già esistente lo segnala; `state.py renumber` propone la correzione.

### 3.9 Rami

Già oggi Sancho chiede commit Conventional con l'id del task. In squadra:
- un ramo per task, `t-007-<titolo-breve>`, registrato dal `claim`;
- la PR cita il task; il merge su `main` porta con sé gli eventi del registro;
- `complete` vuole come prova un commit raggiungibile da `main` (o la PR unita), non solo dal ramo.

## 4. Modifiche ai file

| File | Modifica |
|---|---|
| `schemas/team.schema.json` | nuovo |
| `schemas/event.schema.json` | nuovo, una riga del registro |
| `schemas/state.schema.json` | `protocol` 1.1; `gate.approved_by`; `granted_by` e `decided_by` accettano anche un id membro |
| `schemas/backlog.schema.json` | `task.assignee` facoltativo |
| `schemas/uat.schema.json` | `case.assignee`, `defect.assignee` facoltativi |
| `scripts/state.py` | lettura di team ed eventi; `claim`, `release`, `task`, `review`, `uat-result`, `since`, `compact`, `team init`, `hooks install`, `renumber`; `next --me/--team`; controlli di ruolo su `submit`/`approve` |
| `scripts/_common.py` | `append_event()` (append con newline, mai riscrittura) |
| `references/team.md` | nuovo: le regole per il modello in modalità team |
| `references/phases/04-implement.md`, `05-verify.md` | "aggiorna lo stato con `state.py task ...`" invece di modificare il backlog a mano |
| `SKILL.md` | una riga: se esiste `.sancho/team.json`, leggi `references/team.md` |
| `hooks/` (pannello) | sezioni Squadra e Novità, avviso sugli eventi che ti riguardano |
| `docs/` | capitolo "Lavorare in squadra" nella guida, in tre lingue |

Un effetto utile anche per chi lavora da solo: con `state.py task` gli stati dei task passano da uno script validato invece che da modifiche a mano del JSON.

## 5. Compatibilità e migrazione

- **Senza `team.json` non cambia nulla**: stessi comandi, stessi output, stessi test.
- `state.py team init` crea `team.json` proponendo i membri dagli autori di `git log` (nomi ed email); il coordinatore conferma. Gli stati attuali restano in `backlog.json`, il registro parte vuoto.
- Il protocollo passa a `sancho/1.1`; gli script 1.1 leggono i file 1.0.
- La skill nell'app Claude (ZIP) segue le stesse regole, ma senza git locale `since` e l'hook non sono disponibili: lì la modalità team serve a poco e la guida lo dirà.

## 6. Come lo verificheremo

Nuovi controlli in `tests/validate.py`, offline, con repository git temporanei:
1. **Nessun conflitto**: tre cloni, ognuno prende e completa task diversi, merge in qualsiasi ordine: zero conflitti e stato finale uguale.
2. **Prenotazione contesa**: due claim su T-007 in cloni diversi; dopo il merge vince il più vecchio, l'altro lo vede in `next`.
3. **Quattro occhi**: l'autore non può revisionare il proprio task.
4. **Quorum**: con quorum 2 il gate resta aperto dopo un'approvazione.
5. **Compattazione**: lo stato prima e dopo `compact` è identico; un evento arrivato dopo viene applicato.
6. **Since**: dopo un pull elenca esattamente gli eventi nuovi, divisi per persona.
7. **Modalità singola**: tutti i 37 controlli esistenti passano senza modifiche.

E le eval di comportamento: "chi sta facendo cosa?", "prendo io il prossimo task", "approva il gate" detto da chi non è approvatore, "cosa è cambiato da ieri?".

## 7. Tappe proposte

1. **Fondamenta** (il grosso): `team.json`, registro eventi, stato calcolato, `claim`/`release`/`task`, `next --me/--team`, test 1-3 e 7.
2. **Gate in squadra**: approvatori, quorum, `compact`, test 4-5.
3. **Consapevolezza**: `since`, hook `post-merge`, `renumber`, test 6.
4. **Pannello e documentazione**: sezioni Squadra e Novità, guida in tre lingue, eval.

Ogni tappa è rilasciabile da sola (1.1.0, 1.2.0...), e la modalità singola non cambia mai.

## 8. Domande aperte

1. **Quorum predefinito**: basta un'approvazione per tutte le fasi tranne RELEASE, o ne vuoi due ovunque?
2. **Push della prenotazione**: Sancho propone commit e push su `main` subito dopo il claim. Va bene, o preferite tenere le prenotazioni solo nei rami (si vedono più tardi)?
3. **Chi può aprire le fasi**: solo il coordinatore, o chiunque abbia il ruolo che guida la fase (per esempio l'architetto per PLAN)?
4. **Assegnazione dei casi UAT**: li distribuisce il coordinatore, o ognuno prende i casi della piattaforma che ha in mano (Android, web...)?
5. **Nomi nel registro**: gli id dei membri finiscono nella storia git del progetto. Per progetti pubblici serve un'opzione con pseudonimi?
