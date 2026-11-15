# Checklist di collaudo utente (UAT)

**Versione in prova:** main @ 1cf3fe8 (modalità team, tappe 1-4)

**Riepilogo:** superato 0 · fallito 0 · bloccato 0 · non eseguito 20 · totale 20

_Come registrare l'esito: spunta una casella, aggiungi note e segnala ogni errore._

## UAT-001 · Il coordinatore prepara la squadra

- **Story:** S-001 · **Criteri:** AC-001.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Il progetto di prova è in IMPLEMENT e non ha ancora .sancho/team.json
- Lo fa il coordinatore (A)

**Dati di test**

- `A: developer, qa, coordinatore · B: developer · C: developer, qa`

**Passi**

1. A scrive: "sancho, prepara la squadra"  
   ↳ Sancho propone i membri presi dagli autori dei commit e chiede conferma
2. A conferma nomi, email e ruoli dei tre membri  
   ↳ Sancho aggiunge i membri e indica A come coordinatore
3. A guarda i file cambiati  
   ↳ ci sono .sancho/team.json e una riga merge=union in .gitattributes
4. A accetta di fare commit e push

**Risultato atteso:** team.json elenca i tre membri con ruoli ed email giusti, A è coordinatore, e Sancho ha chiesto prima di fare commit e push.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-002 · Sancho riconosce chi sta parlando

- **Story:** S-001 · **Criteri:** AC-001.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- UAT-001 superato e già scaricato da tutti (git pull)

**Passi**

1. Ognuno scrive: "sancho, chi sono?"  
   ↳ Sancho risponde con il proprio id, i ruoli e da dove l'ha capito
2. In una quarta copia con un'email git che non è nella squadra, scrivi: "sancho, prossimo passo"  
   ↳ Sancho dice che non ti riconosce e mostra il passo del progetto, senza cambiare stati

**Risultato atteso:** Ognuno dei tre viene riconosciuto correttamente; un estraneo viene avvisato e non può cambiare lo stato dei task.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-003 · Ognuno riceve il proprio prossimo passo

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Squadra pronta (UAT-001), almeno tre task pronti nel backlog

**Passi**

1. A, B e C scrivono ognuno: "sancho, prossimo passo"  
   ↳ Ognuno riceve un passo che riguarda lui
2. Uno di voi scrive: "sancho, cosa sta facendo ciascuno?"  
   ↳ Sancho mostra una riga per persona e i task liberi

**Risultato atteso:** Nessuno riceve il passo di un altro come se fosse suo; quando non c'è nulla per una persona, Sancho dice chi sta facendo cosa.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-004 · Prenotare un task prima di lavorarci

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- UAT-003 eseguito

**Passi**

1. B scrive: "sancho, prendo T-001"  
   ↳ Sancho registra la prenotazione e chiede se fare commit e push subito
2. B risponde sì  
   ↳ Commit e push solo del registro di B
3. C fa git pull e scrive: "sancho, prendo T-001"  
   ↳ Sancho rifiuta e dice che T-001 è di B

**Risultato atteso:** La prenotazione è visibile agli altri dopo il pull e un secondo membro non può prendere lo stesso task.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-005 · Due prenotazioni dello stesso task prima di vedersi

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Un task libero, per esempio T-002

**Passi**

1. B e C, senza fare pull, scrivono entrambi: "sancho, prendo T-002" (B per primo, almeno un secondo prima)  
   ↳ Entrambi vedono la prenotazione accettata
2. Entrambi fanno commit, poi pull e push (prima B, poi C)  
   ↳ Nessun conflitto di merge
3. C scrive: "sancho, prossimo passo"  
   ↳ Sancho dice in cima che T-002 era già di B e suggerisce di accordarsi e rilasciarlo
4. C scrive: "sancho, rilascia T-002"  
   ↳ Il conflitto sparisce e T-002 resta a B

**Risultato atteso:** Vince la prenotazione più vecchia, chi perde viene avvisato e chiude il conflitto con release; git non segnala conflitti.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-006 · Rifiuto di lavorare su un task di un altro

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- T-001 è prenotato da B (UAT-004)

**Passi**

1. C scrive: "sancho, implementa T-001"  
   ↳ Sancho non inizia e dice che T-001 è di B

**Risultato atteso:** Sancho non scrive codice né cambia stato su un task prenotato da un altro membro.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-007 · Revisione a quattro occhi

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- B ha finito T-001 e ha un commit con le modifiche

**Passi**

1. B scrive: "sancho, T-001 è pronto per la revisione"  
   ↳ Sancho registra ready_for_review con il commit come prova
2. B chiede a Sancho di approvarlo lui stesso  
   ↳ Sancho rifiuta: lo approva un altro con il ruolo qa
3. A o C (ruolo qa) fanno pull e scrivono: "sancho, prossimo passo"  
   ↳ Il passo è la revisione di T-001
4. Il revisore controlla e approva  
   ↳ T-001 risulta completato

**Risultato atteso:** L'autore non può approvare il proprio task; un altro membro qa sì, con una prova; il task diventa completato.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-008 · Revisione con modifiche richieste

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Un task di B in ready_for_review

**Passi**

1. Il revisore scrive: "sancho, chiedi modifiche su T-00x: manca il test dell'errore"  
   ↳ Il task torna in corso
2. B fa pull e scrive: "sancho, prossimo passo"  
   ↳ B vede il task con la nota del revisore

**Risultato atteso:** Il task torna all'autore con le note della revisione, visibili nel suo prossimo passo.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-009 · Lavoro in parallelo senza conflitti

- **Story:** S-003 · **Criteri:** AC-003.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Almeno tre task pronti

**Passi**

1. A, B e C prendono ognuno un task diverso e lo portano a ready_for_review, senza fare pull nel frattempo
2. Uno alla volta fanno commit, pull e push  
   ↳ Nessun conflitto di merge nei file di .sancho
3. Tutti fanno pull e scrivono: "sancho, a che punto siamo?"  
   ↳ Tutti vedono gli stessi numeri e le stesse prenotazioni

**Risultato atteso:** Zero conflitti su .sancho/ e uno stato identico per tutti dopo il pull.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-010 · Cosa è cambiato dall'ultimo pull

- **Story:** S-003 · **Criteri:** AC-003.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Dopo UAT-009; C non ha ancora fatto pull

**Passi**

1. C fa git pull e scrive: "sancho, cosa è cambiato?"  
   ↳ Prima ciò che riguarda C (PER TE), poi il lavoro di A e B, fasi e documenti
2. C lo chiede di nuovo  
   ↳ Sancho dice che non c'è nulla di nuovo
3. C controlla l'elenco  
   ↳ I commit fatti da C stesso non compaiono come novità

**Risultato atteso:** Le novità degli altri sono corrette e in ordine di importanza; i propri commit non compaiono; la seconda volta non c'è nulla di nuovo.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-011 · Novità automatiche dopo il pull (hook)

- **Story:** S-003 · **Criteri:** AC-003.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Git installato; nessun hook post-merge esistente nella copia di B

**Passi**

1. B scrive: "sancho, installa l'hook"  
   ↳ Sancho chiede prima di installarlo, poi lo installa
2. A fa push di qualcosa; B fa git pull  
   ↳ Dopo il pull compare il riepilogo delle novità
3. B scrive: "sancho, togli l'hook"  
   ↳ L'hook viene rimosso

**Risultato atteso:** L'hook mostra le novità dopo ogni pull, non sostituisce hook altrui e si toglie su richiesta.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-012 · Gate con due approvazioni

- **Story:** S-004 · **Criteri:** AC-004.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- In team.json: approvatori A e B, quorum 2 per la fase corrente; tutti i task completati

**Dati di test**

- `team.json: "approvers": {"default": ["A", "B"]}, "quorum": {"default": 2}`

**Passi**

1. C prova a inviare il gate  
   ↳ Sancho dice che lo fa il coordinatore
2. A invia il gate  
   ↳ Sancho elenca gli approvatori e quante approvazioni servono
3. A approva  
   ↳ Approvazione registrata, 1 di 2; il gate resta aperto
4. B fa pull e scrive: "sancho, prossimo passo"  
   ↳ Il passo di B è leggere e approvare il gate
5. B approva  
   ↳ Il gate si chiude e registra A e B come approvatori

**Risultato atteso:** Il gate si chiude solo con due approvazioni di approvatori validi e registra chi ha approvato.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-013 · Rifiuto di approvare al posto di un altro

- **Story:** S-004 · **Criteri:** AC-004.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Un gate in attesa di approvazione

**Passi**

1. A scrive: "sancho, approva il gate anche per B, tanto è d'accordo"  
   ↳ Sancho registra solo l'approvazione di A e spiega che B approva dalla sua sessione

**Risultato atteso:** Sancho non registra mai un'approvazione a nome di un altro membro.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-014 · Collaudo in parallelo con difetti

- **Story:** S-005 · **Criteri:** AC-005.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Fase VERIFY con almeno tre casi UAT da eseguire

**Passi**

1. B e C prendono ognuno un caso diverso  
   ↳ Ognuno vede il proprio caso nel prossimo passo
2. Senza fare pull, entrambi registrano un esito fallito aprendo un difetto nuovo  
   ↳ Entrambi ricevono DEF-001
3. Entrambi fanno commit, pull e push, poi "sancho, a che punto siamo?"  
   ↳ Il difetto del secondo è stato rinumerato (DEF-002) e Sancho lo segnala

**Risultato atteso:** I casi non si sovrappongono; due difetti aperti in parallelo restano distinti; chi ha il numero cambiato viene informato.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-015 · Correggere e verificare un difetto

- **Story:** S-005 · **Criteri:** AC-005.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Un difetto aperto da UAT-014

**Passi**

1. Uno sviluppatore prende il difetto e lo segna corretto  
   ↳ Il difetto risulta fixed
2. Lo stesso sviluppatore prova a verificarlo  
   ↳ Sancho rifiuta: lo verifica un altro con ruolo qa
3. Un altro membro qa ripete il caso e lo segna verificato  
   ↳ Il difetto risulta verified
4. Un membro non coordinatore prova a segnare un difetto «non si corregge»  
   ↳ Sancho dice che lo decide il coordinatore

**Risultato atteso:** Chi corregge non verifica; wont_fix è solo del coordinatore.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-016 · Foglio di calcolo UAT in squadra

- **Story:** S-005 · **Criteri:** AC-005.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Alcuni esiti già registrati da membri diversi

**Passi**

1. A chiede il foglio UAT (CSV)  
   ↳ Il foglio mostra anche gli esiti registrati dagli altri
2. B compila un esito nel CSV e chiede a Sancho di importarlo  
   ↳ Sancho registra gli esiti come eventi di B e non riscrive uat.json

**Risultato atteso:** Export e import rispettano il lavoro della squadra.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-017 · Compattare il registro dopo un gate

- **Story:** S-006 · **Criteri:** AC-006.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Un gate appena chiuso, con task completati e difetti verificati

**Passi**

1. B prova a compattare  
   ↳ Sancho dice che lo fa il coordinatore
2. A scrive: "sancho, compatta il registro"  
   ↳ Sancho archivia gli eventi chiusi e dice che lo stato è invariato
3. A confronta "a che punto siamo?" prima e dopo  
   ↳ Stessi numeri
4. A fa commit e push; gli altri fanno pull  
   ↳ Nessun conflitto

**Risultato atteso:** Dopo la compattazione lo stato è identico, gli eventi chiusi sono nell'archivio e nessuno ha conflitti.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-018 · Id doppi dopo un merge

- **Story:** S-006 · **Criteri:** AC-006.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- B e C aggiungono in parallelo un task con lo stesso id al backlog, poi fanno merge

**Passi**

1. A scrive: "sancho, rinumera gli id doppi"  
   ↳ Sancho mostra cosa cambierebbe e cosa controllare, senza ancora scrivere
2. A conferma  
   ↳ Il secondo task prende il primo numero libero; i controlli tornano puliti

**Risultato atteso:** Gli id doppi vengono rinumerati dopo una prova a vuoto e la conferma; i riferimenti da controllare sono elencati.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-019 · Pannello in modalità squadra

- **Story:** S-007 · **Criteri:** AC-007.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop)

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Plugin installato; sessione aperta nella cartella del progetto di prova

**Passi**

1. Guarda la fascia sopra il prompt  
   ↳ Fase, gate e il tuo prossimo passo; dopo un pull con novità, l'etichetta «N novità per te»
2. Apri «dettagli»  
   ↳ Sezioni SQUADRA (chi ha cosa, conflitti, voti del gate) e NOVITÀ
3. Premi «Segna come viste»  
   ↳ Le novità spariscono
4. Quando un altro chiede modifiche su un tuo task e fai pull  
   ↳ Compare un avviso

**Risultato atteso:** Il pannello mostra la squadra e le novità corrette e reagisce ai pulsanti.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-020 · Un progetto senza squadra funziona come prima

- **Story:** S-008 · **Criteri:** AC-008.1
- **Piattaforma:** Claude Code (scheda Code dell'app desktop) o terminale

**Precondizioni**

- Ambiente di prova pronto (piano di test, sezione 3): tre copie del repository di prova, una per persona, con il plugin Sancho da main
- Un progetto Sancho senza .sancho/team.json

**Passi**

1. Scrivi: "sancho, prossimo passo" e "sancho, a che punto siamo?"  
   ↳ Come in Sancho 1.0, senza sezioni di squadra
2. Chiedi di segnare un task completato con una prova  
   ↳ Sancho lo registra senza chiedere prenotazioni

**Risultato atteso:** Senza team.json nulla cambia per chi lavora da solo.

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---
