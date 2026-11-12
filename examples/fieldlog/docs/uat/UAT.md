# Checklist di collaudo utente (UAT)

**Versione in prova:** 0.9.0-rc.1 (commit 4f2a9c1)

**Riepilogo:** superato 2 · fallito 1 · bloccato 0 · non eseguito 2 · totale 5

_Come registrare l'esito: spunta una casella, aggiungi note e segnala ogni errore._

## UAT-001 · Wrong password shows a generic error

- **Story:** S-001 · **Criteri:** AC-001.2
- **Piattaforma:** android (Samsung Galaxy A54, Android 14)

**Precondizioni**

- FieldLog is installed from the test build
- The account tecnico1@example.com exists

**Dati di test**

- `email: tecnico1@example.com`
- `wrong password: Sbagliata!2026`
- `unknown email: nessuno@example.com`

**Passi**

1. Open FieldLog
2. Type the email tecnico1@example.com and the wrong password, tap Sign in  
   ↳ A message says the email or password is not correct
3. Type the unknown email nessuno@example.com and any password, tap Sign in  
   ↳ Exactly the same message as in step 2

**Risultato atteso:** Both attempts show the same message; nothing reveals whether the email is registered

**Esito:** [ ] superato [x] fallito [ ] bloccato [ ] non eseguito

Eseguito da: Danilo · Eseguito il: 2026-10-22T11:20:00+02:00 · Difetti: DEF-001

**Note:** Step 3 shows 'User not found'

---

## UAT-002 · Job logged offline is synced when back online

- **Story:** S-002 · **Criteri:** AC-002.1
- **Piattaforma:** android (Samsung Galaxy A54, Android 14) + web (Chrome)

**Precondizioni**

- Signed in as tecnico1@example.com
- Back-office dashboard open in Chrome as ufficio@example.com

**Dati di test**

- `customer: Condominio Aurora, Via Roma 10`
- `activity: monthly inspection, 45 minutes`
- `one photo`

**Passi**

1. Turn on airplane mode on the phone
2. Tap New job, fill in the test data, add a photo, tap Save  
   ↳ The job appears in the list with a 'waiting to sync' badge
3. Turn off airplane mode and wait one minute
4. Refresh the dashboard in Chrome  
   ↳ The job is listed with the photo

**Risultato atteso:** The job saved offline appears on the dashboard within one minute of reconnecting, with its photo

**Esito:** [x] superato [ ] fallito [ ] bloccato [ ] non eseguito

Eseguito da: Danilo · Eseguito il: 2026-10-22T11:45:00+02:00

**Note:** 

---

## UAT-003 · Filter jobs by date and technician

- **Story:** S-003 · **Criteri:** AC-003.1
- **Piattaforma:** web (Chrome 130, desktop)

**Precondizioni**

- Signed in as ufficio@example.com
- Test data loaded: 30 jobs by 3 technicians over October

**Dati di test**

- `date range: 1-15 October 2026`
- `technician: Tecnico Uno`

**Passi**

1. Open Jobs
2. Set the date range 1-15 October 2026
3. Choose the technician 'Tecnico Uno'  
   ↳ The counter above the list updates

**Risultato atteso:** Only Tecnico Uno's jobs between 1 and 15 October are listed (8 jobs in the test data)

**Esito:** [x] superato [ ] fallito [ ] bloccato [ ] non eseguito

Eseguito da: Danilo · Eseguito il: 2026-10-22T12:05:00+02:00

**Note:** 

---

## UAT-004 · Dashboard usable with the keyboard only

- **Story:** S-003 · **Criteri:** AC-003.2
- **Piattaforma:** web (Edge, desktop)

**Precondizioni**

- Signed in as ufficio@example.com
- Mouse or touchpad not used during the test

**Passi**

1. Press Tab repeatedly from the top of the Jobs page  
   ↳ A clearly visible outline moves through filters, list and buttons in reading order
2. Reach the date filter and set a range with the keyboard only
3. Open a job with Enter and close it with Esc

**Risultato atteso:** Every action is possible without a mouse and the focus is always visible

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## UAT-005 · Customer signature appears in the PDF

- **Story:** S-004 · **Criteri:** AC-004.1
- **Piattaforma:** android (Samsung Galaxy A54) + web (Chrome)

**Precondizioni**

- A synced job exists for Condominio Aurora

**Passi**

1. On the phone open the job and tap Customer signature
2. Hand the phone to the customer, let them sign, tap Confirm
3. On the dashboard open the job and download the PDF  
   ↳ The PDF opens

**Risultato atteso:** The PDF shows the signature in the signature box with date and customer name

**Esito:** [ ] superato [ ] fallito [ ] bloccato [x] non eseguito

**Note:** 

---

## Difetti

| ID | UAT | Gravità | Stato | Descrizione |
|---|---|---|---|---|
| DEF-001 | UAT-001 | major | open | Sign-in error reveals that an email is not registered ('User not found'), enabling account enumeration (TM-01) |
