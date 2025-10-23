# MongoDB Alarm Checker - Setup e Utilizzo

## 📋 Panoramica

Il sistema di verifica allarmi MongoDB permette di validare gli allarmi dei sensori di tiro interrogando direttamente il database MongoDB di produzione attraverso un tunnel SSH.

## 🔧 Setup

### 1. Installazione Dipendenze

Installa le nuove dipendenze necessarie:

```bash
pip install pymongo sshtunnel python-dotenv
```

Oppure installa tutto da requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Configurazione File .env

1. Copia il file `.env.example` in `.env`:
   ```bash
   copy .env.example .env
   ```

2. Apri il file `.env` e inserisci le credenziali reali:
   ```env
   SSH_HOST=10.147.131.41
   SSH_PORT=22
   SSH_USER=reply
   SSH_PASSWORD=inserisci_password_ssh_qui
   
   MONGO_URI=mongodb://iot_sre:inserisci_password_mongodb_qui@epmvlmngiotcfg3.servizi.prv:27017,...
   MONGO_DATABASE=ibm_iot
   MONGO_COLLECTION=unsolicited
   ```

3. **IMPORTANTE**: Mai committare il file `.env` su Git!

### 3. Test Connessione

Per testare la connessione MongoDB:

```bash
python mongodb_checker.py
```

Output atteso:
```
🧪 Testing MongoDB Alarm Checker

🔌 Connecting to SSH bridge: reply@10.147.131.41:22
✅ SSH tunnel established on local port: 12345
✅ MongoDB connection established to database: ibm_iot

🔍 Checking alarm boolean state for:
   Device: 1:1:2:15:21:DIGIL_IND_0015
   Metric: EAM_OUT_ALG_19_VAR_20_calc

📊 Result:
   Found: True
   Active: True
   Timestamp: 23/10/25 - 14:30:15
   Metric Checked: EAM_OUT_ALG_19_VAR_20_calc

✅ Alarm boolean is TRUE - test would be VALIDATED!
```

## 🎯 Come Funziona

### Logica di Validazione

Per ogni sensore di tiro monitorato:

1. **Priorità 1**: Il sistema cerca il valore della metrica EGM (es: `EGM_OUT_SENS_23_VAR_42`)
2. **Priorità 2**: Se il valore non arriva, verifica il booleano MongoDB della metrica EAM corrispondente (es: `EAM_OUT_ALG_19_VAR_20_calc`)

**Il test è VALIDATO se:**
- Viene trovato il valore dell'allarme OPPURE
- Viene trovato il `true` del booleano in MongoDB

### Mappatura Sensori → Allarmi

Ogni sensore EGM ha due allarmi EAM associati (Min e Max):

```
EGM_OUT_SENS_23_VAR_42 (TC_F8B_L1) → ['EAM_OUT_ALG_19_VAR_19', 'EAM_OUT_ALG_19_VAR_20']
                                       (Min alarm)              (Max alarm)
```

La query MongoDB cerca la metrica con suffisso `_calc`:
```javascript
{
  clientId: "1:1:2:15:21:DIGIL_IND_0015",
  "payload.metrics.EAM_OUT_ALG_19_VAR_20_calc.value": {$eq: true}
}
```

### Esempio Pratico

**Scenario**: Test per device `1:1:2:15:21:DIGIL_IND_0015` con 6 sensori

**Sensori attesi**:
- `EGM_OUT_SENS_23_VAR_32` - TC_F12A_L1
- `EGM_OUT_SENS_23_VAR_34` - TC_F12B_L1
- `EGM_OUT_SENS_23_VAR_36` - TC_F4A_L1
- `EGM_OUT_SENS_23_VAR_38` - TC_F4B_L1
- `EGM_OUT_SENS_23_VAR_40` - TC_F8A_L1
- `EGM_OUT_SENS_23_VAR_42` - TC_F8B_L1

**Monitoraggio**:
1. Ogni 5 secondi il sistema verifica se sono arrivati i valori delle metriche EGM
2. Per ogni metrica mancante, interroga MongoDB per verificare i booleani delle EAM corrispondenti
3. Appena trova un `true`, marca quel sensore come validato

**Visualizzazione**:
```
EGM_OUT_SENS_23_VAR_42 - TC_F8B_L1
📍 23/10/25 - 10:58:39 - Valore: 126.2475
✓ Allarme TRUE rilevato via MongoDB (EAM_OUT_ALG_19_VAR_20_calc)
```

## 🗂️ Struttura Files

```
tool-report/
├── mongodb_checker.py          # Modulo principale MongoDB
├── monitoring_service.py       # Servizio monitoraggio (INTEGRATO)
├── .env                        # Credenziali (NON committare!)
├── .env.example                # Template credenziali
├── requirements.txt            # Dipendenze Python
└── README_MONGODB.md          # Questa documentazione
```

## 🔍 Troubleshooting

### Errore: "Missing required environment variables"

**Causa**: File `.env` mancante o incompleto

**Soluzione**: 
1. Verifica che esista il file `.env` nella root del progetto
2. Controlla che contenga tutte le variabili richieste
3. Riavvia l'applicazione

### Errore: "Connection timeout" o "SSH tunnel failed"

**Causa**: Problemi di connessione SSH o credenziali errate

**Soluzione**:
1. Verifica di essere nella rete aziendale o VPN
2. Controlla username/password SSH nel file `.env`
3. Prova a connetterti manualmente via SSH: `ssh reply@10.147.131.41`

### Errore: "MongoDB authentication failed"

**Causa**: Password MongoDB errata

**Soluzione**:
1. Verifica la password nel `MONGO_URI` del file `.env`
2. Assicurati che non ci siano spazi o caratteri speciali mal codificati

### Query MongoDB non trova risultati

**Possibili cause**:
1. L'allarme non è ancora stato attivato
2. Il device ID è errato
3. La metrica EAM cercata non esiste per quel sensore

**Debug**:
```python
# Test manuale
from mongodb_checker import MongoDBAlarmChecker

checker = MongoDBAlarmChecker()
checker.connect()

# Prova query
result = checker.check_alarm_boolean("DEVICE_ID", "EAM_OUT_ALG_19_VAR_20")
print(result)

checker.disconnect()
```

## 📊 Monitoraggio Performance

Il sistema logga ogni operazione:
- Tempo di connessione SSH
- Tempo di query MongoDB
- Numero di allarmi verificati

Logs importanti:
```
🔌 Connecting to SSH bridge: reply@10.147.131.41:22
✅ SSH tunnel established on local port: 54321
✅ MongoDB connection established
🔍 Checking alarm: EAM_OUT_ALG_19_VAR_20_calc
✅ Alarm TRUE found at 23/10/25 - 10:58:39
```

## 🚀 Prossimi Sviluppi

- [ ] Cache risultati MongoDB per ridurre query ripetute
- [ ] Retry automatico su errori di connessione
- [ ] Dashboard statistiche query MongoDB
- [ ] Export log query per analisi

## 📞 Supporto

Per problemi o domande:
1. Verifica questa documentazione
2. Controlla i log dell'applicazione
3. Testa la connessione con `python mongodb_checker.py`

---

**Versione**: 2.0  
**Ultimo aggiornamento**: Ottobre 2025