# Sancho - guida d'uso

[English](guide.en.md) · [Italiano](guide.it.md) · [Español](guide.es.md) · Non l'hai ancora installato? [Guida all'installazione](install.it.md)

Questa guida è per chi guida il progetto: tu, non gli agenti. Spiega cosa ti chiederà Sancho, cosa decidi tu e come ritrovare il filo dopo una pausa.

## 1. Per iniziare

1. Installa Sancho (vedi la [guida all'installazione](install.it.md)).
2. Apri in Claude Code una cartella vuota o il tuo progetto esistente (oppure avvia una chat nell'app Claude).
3. Scrivi `/sancho:discover` (Claude Code con il plugin), `/sancho discover` (app Claude o sola skill) o semplicemente "sancho, voglio creare...".

Al primo avvio Sancho mostra un breve tour e crea la cartella `.sancho/`, che contiene la memoria del progetto. **Mettila sotto git**: è così che la sessione successiva sa a che punto sei.

Ti sei perso? Scrivi **`next`** per il prossimo passo concreto, oppure **`status`** per il quadro completo.

## 2. Il percorso tipico

```
discover -> gate -> specify -> gate -> plan -> gate -> tasks -> gate
        -> implement (un task alla volta) -> gate -> verify (tu esegui gli UAT) -> gate
        -> release (tu approvi il go-live) -> gate -> evolve -> gate
```

Ogni fase termina con un **riepilogo del gate**: cosa è stato prodotto, esiti della checklist, problemi aperti e cosa *non* è stato verificato. Rispondi "approvo", oppure di' cosa cambiare. Sancho non approva mai al posto tuo.

## 3. Promemoria dei comandi

| Cosa vuoi fare | Claude Code con il plugin | App Claude (e Claude Code con la sola skill) | A parole, ovunque |
|---|---|---|---|
| Tour e aiuto | `/sancho:help` | `/sancho help` | "sancho, aiuto" |
| Aiuto su un argomento | `/sancho:help uat` | `/sancho help uat` | "sancho, spiegami gli UAT" |
| A che punto siamo? | `/sancho:status` | `/sancho status` | "sancho, a che punto siamo?" |
| Cosa faccio adesso? | `/sancho:next` | `/sancho next` | "sancho, prossimo passo?" |
| Eseguire una fase | `/sancho:discover` ... `/sancho:evolve` | `/sancho plan` | "sancho, facciamo il plan" |
| Implementare un task preciso | `/sancho:implement T-007` | `/sancho implement T-007` | "sancho, implementa T-007" |
| UAT guidati | `/sancho:verify uat` | `/sancho verify uat` | "sancho, facciamo gli UAT" |
| Solo controlli di sicurezza | `/sancho:verify security` | `/sancho verify security` | "sancho, fai i controlli di sicurezza" |
| Salvare prima di fermarsi | `/sancho:checkpoint` | `/sancho checkpoint` | "sancho, checkpoint" |
| Analizzare un progetto esistente | `/sancho:assess` | `/sancho assess` | "sancho, analizza questo progetto" |

<!-- invocation-forms -->
**Due forme, a seconda di dove usi Sancho.**
- **Claude Code con il plugin:** `/sancho:<comando>`, tutto attaccato (`/sancho:status`). Il plugin registra un comando per ogni voce e il formato `plugin:comando` è lo standard di Claude Code.
- **App Claude** (web, desktop, mobile) **e Claude Code con la sola skill:** `/sancho <comando>`, con lo spazio (`/sancho status`). Esiste un solo comando, `/sancho`: quando lo scegli dal menu l'app aggiunge uno spazio, e il comando si scrive subito dopo. `/sancho:status` qui non esiste; se per abitudine scrivi `/sancho :status`, Sancho capisce lo stesso.

Le tue risposte a un gate: "approvo" (oppure "ok", "vai") · "non approvo: <motivo>" · "approvo comunque, accetto <rischio>" (registrato come override).

## 4. La tua prima sessione (esempio)

```
Tu:     /sancho:discover Voglio un'app per far registrare ai tecnici gli interventi di manutenzione
Sancho: Sancho al tuo servizio. Quattro domande veloci per cominciare:
        1. Chi registra gli interventi, e da quale dispositivo? ...
Tu:     (risposte)
Sancho: (altri due giri: vincoli, dati personali; quattro proposte di nome)
        Propongo il livello L2: dati personali dei clienti, due piattaforme. Sei d'accordo?
Tu:     sì, e mi piace "FieldLog"
Sancho: GATE DISCOVER - pronto per la tua approvazione
        Prodotto: docs/constitution.md · Checklist: 8 pass, 1 n/a · Decisioni: nome, L2
        Non verificato: costi di hosting (HYPOTHESIS)
        Approvi, o mi dici cosa cambiare?
Tu:     approvo
Sancho: Gate approvato. Prossimo passo: SPECIFY - requisiti e user story (/sancho:specify).
```

Un progetto completo d'esempio è in [examples/fieldlog](../examples/fieldlog/WALKTHROUGH.md).

## 5. Cosa decidi tu, fase per fase

| Fase | Sancho ti chiede | Consigli |
|---|---|---|
| DISCOVER | il problema, gli utenti, le piattaforme, budget e scadenze, i dati personali, il nome del prodotto, il livello di rischio | Indica 2-3 tipi reali di utente, non "tutti". Se ci sono account, email o foto di persone, si applica il GDPR. |
| SPECIFY | priorità (must/should/could/won't), cosa resta FUORI dalla prima versione, domande aperte | Leggi bene la lista OUT: è la protezione del tuo perimetro. |
| PLAN | stack (ricevi una raccomandazione e due alternative con punteggi), container, palette, logo, rischi accettati | Se conosci già la tecnologia da usare, dillo: Sancho la accetta e ne elenca solo i rischi. |
| TASKS | ordine di esecuzione e milestone | I task grandi vengono scomposti automaticamente (complessità sopra 7). |
| IMPLEMENT | solo questioni di scope e task bloccati | Chiedi `status` ogni tanto; prima di fermarti, accetta il checkpoint. |
| VERIFY | approvazione dei test di sicurezza attivi, esiti UAT, accettazione dei rischi residui | Gli UAT li esegui tu: Sancho ti guida un caso alla volta. |
| RELEASE | go-live, pubblicazione sugli store, migrazioni in produzione | Ogni passo irreversibile richiede un tuo sì esplicito. |
| EVOLVE | retrospettiva, come risolvere le differenze tra codice e standard | Mantiene il progetto coerente per il giro successivo. |

## 6. Livelli: quanto processo

| Livello | Quando | Cosa cambia |
|---|---|---|
| L0 | script usa e getta, demo | tre domande, gate a voce, niente PLAN/RELEASE/EVOLVE |
| L1 | app piccola, una piattaforma, nessun dato sensibile | PLAN, RELEASE, EVOLVE saltati; scelta rapida dello stack in DISCOVER |
| L2 | prodotto reale, più piattaforme, dati personali | tutte e otto le fasi |
| L3 | pagamenti, sanità, settori regolamentati, migrazioni di dati reali | tutte le fasi + analisi d'impatto, piani di rollback, review di sicurezza aggiuntiva |

Puoi cambiare livello in seguito: Sancho ti spiega cosa comporta.

## 7. UAT: collaudare il prodotto di persona

In TASKS il QA scrive i test di accettazione in linguaggio semplice: precondizioni, dati di test, passi numerati, risultato atteso, una piattaforma o un dispositivo per caso. Li ricevi come `docs/uat/UAT.md` (stampabile, con caselle da spuntare) e come `docs/uat/uat.csv` (foglio di calcolo).

In VERIFY puoi scegliere tra due modalità:
- **Guidata:** `/sancho:verify uat`. Sancho ti mostra un caso, lo esegui sul dispositivo e rispondi superato, fallito o bloccato, con eventuali note.
- **Foglio di calcolo:** compila il CSV (Esito, Eseguito da, Note), anche con i colleghi, e rimandalo. Sancho lo importa.

Ogni fallimento diventa un difetto con una gravità, un task di correzione e un nuovo test. La fase non si chiude con difetti blocker o major aperti, a meno che tu non accetti esplicitamente il rischio.

## 8. Sicurezza: cosa aspettarsi

- In PLAN, un threat model elenca cosa può andare storto e come si previene.
- In VERIFY, Sancho esegue (o ti chiede di installare) la ricerca di segreti, l'analisi statica, il controllo delle dipendenze, la scansione dei container e, per il mobile, l'analisi dell'app. Le vulnerabilità sono ordinate per **CISA KEV** (sfruttate attivamente), poi per **EPSS** (probabilità di sfruttamento), poi per **CVSS**.
- I **test attivi** (ad esempio una scansione OWASP ZAP) girano sul tuo ambiente locale, di test o di staging, dopo che hai approvato il target esatto. Sulla tua produzione solo con la tua approvazione esplicita e una finestra oraria concordata, entrambe registrate. Sancho rifiuta target di terzi.
- Tutto ciò che non è stato possibile eseguire viene segnato **NOT RUN**, con il comando per eseguirlo in seguito. "Nessun problema trovato" non viene mai presentato come "sicuro".

## 9. Tornare indietro, fermarsi, riprendere

- **Cambio di idea:** "riapri SPECIFY, voglio aggiungere X". Sancho riapre la fase, aggiorna il backlog e verifica l'impatto su task e UAT.
- **Saltare una fase:** si può. Sancho registra il motivo in un ADR (registro delle decisioni).
- **Pausa:** `/sancho:checkpoint` salva un breve riepilogo. La volta successiva, `status` lo riprende.

## 10. Brand e immagini

Sancho disegna i loghi in SVG e le palette come design token con contrasto verificato. Per foto o illustrazioni complesse può usare un servizio di generazione immagini che hai configurato (chiave API in una variabile d'ambiente, oppure un server MCP). Altrimenti ti consegna un prompt pronto da incollare nello strumento che preferisci.

## 11. Domande frequenti

**Serve internet?** Solo per le ricerche e per i dati sulle vulnerabilità (OSV, NVD, KEV, EPSS). Senza connessione quei controlli risultano NOT RUN.

**Manca Python (Windows).** Installa Python 3.9+ da python.org spuntando "Add to PATH", oppure usa il launcher `py`. Gli script non richiedono pacchetti aggiuntivi.

**Posso usarlo su un progetto esistente?** Sì. In DISCOVER estrae prima le convenzioni esistenti come standard, così il lavoro nuovo resta coerente con il codice che hai già.

**Di chi sono le decisioni?** Tue. Nome, piattaforme, stack, brand, scope, ogni gate e il go-live li decidi tu. Sancho propone, spiega e registra.
