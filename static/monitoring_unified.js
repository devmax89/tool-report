// static/monitoring_unified.js
let socket = null;
let timerInterval = null;
let startTime = null;

// Dati per metriche
let foundMetricsData = {};
let expectedMetrics = [];

// Dati per allarmi
let foundAlarmsData = {};
let otherAlarmsData = {};
let expectedAlarms = [];

// Filtri variabili storico
let historicalMode = false;
let timeWindowMinutes = 10; // Default 10 minuti
let filteredMetrics = {};
let filteredAlarms = {};

// Ottieni parametri dall'URL
const urlParams = new URLSearchParams(window.location.search);
const deviceId = urlParams.get('device_id');
const numSensors = parseInt(urlParams.get('num_sensors') || '6');
const ui = urlParams.get('ui') || 'Lazio';
const timeout = parseInt(urlParams.get('timeout') || '120');

const alarmDescriptions = {
    'EGM_OUT_SENS_23_VAR_32': 'TC_F12A_L1',
    'EGM_OUT_SENS_23_VAR_33': 'TC_F12A_L2',
    'EGM_OUT_SENS_23_VAR_34': 'TC_F12B_L1',
    'EGM_OUT_SENS_23_VAR_35': 'TC_F12B_L2',
    'EGM_OUT_SENS_23_VAR_36': 'TC_F4A_L1',
    'EGM_OUT_SENS_23_VAR_37': 'TC_F4A_L2',
    'EGM_OUT_SENS_23_VAR_38': 'TC_F4B_L1',
    'EGM_OUT_SENS_23_VAR_39': 'TC_F4B_L2',
    'EGM_OUT_SENS_23_VAR_40': 'TC_F8A_L1',
    'EGM_OUT_SENS_23_VAR_41': 'TC_F8A_L2',
    'EGM_OUT_SENS_23_VAR_42': 'TC_F8B_L1',
    'EGM_OUT_SENS_23_VAR_43': 'TC_F8B_L2',
    'EGM_OUT_SENS_23_VAR_30': 'Inc_X',
    'EGM_OUT_SENS_23_VAR_31': 'Inc_Y',
    'EGM_OUT_SENS_23_VAR_7': 'Channel'
};

function getCurrentDateFormatted() {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const year = String(now.getFullYear()).slice(-2);
    return `${day}/${month}/${year}`;
}

// Inizializza connessione WebSocket
function initSocket() {
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connesso al server');
        updateStatus('Connesso al server', 'info');
        
        // Mostra info dispositivo
        document.getElementById('deviceInfo').textContent = 
            `Device: ${deviceId} | Sensori: ${numSensors} | UI: ${ui} | Timeout: ${timeout} min`;
        
        // Imposta metriche e allarmi attesi
        setExpectedItems();
    });
    
    socket.on('monitoring_started', function(data) {
        console.log('Monitoraggio avviato:', data);
        updateStatus('Monitoraggio avviato - In attesa dati...', 'info');
        startTimer();
    });
    
    // Handler per metriche
    socket.on('metric_found', function(data) {
        console.log('Nuova metrica trovata:', data);
        addFoundMetric(data);
    });
    
    socket.on('metrics_update', function(data) {
        updateMetricsProgress(data);
    });
    
    // Handler per allarmi
    socket.on('alarm_found', function(data) {
        console.log('Nuovo allarme trovato:', data);
        addFoundAlarm(data);
        playNotificationSound();
    });
    
    socket.on('other_alarm_found', function(data) {
        console.log('Altro allarme trovato:', data);
        addOtherAlarm(data);
    });
    
    socket.on('alarms_update', function(data) {
        updateAlarmsProgress(data);
    });
    
    // Handler comuni
    socket.on('monitoring_complete', function(data) {
        console.log('Monitoraggio completato:', data);
        stopTimer();
        updateStatus('✅ Monitoraggio completato! Tutti i dati ricevuti.', 'success');
        document.getElementById('stopBtn').disabled = true;
        playSuccessSound();
    });
    
    socket.on('monitoring_timeout', function(data) {
        console.log('Timeout raggiunto:', data);
        stopTimer();
        updateStatus(`⏱️ Timeout raggiunto. Dati parziali ricevuti.`, 'error');
        document.getElementById('stopBtn').disabled = true;
    });
    
    socket.on('monitoring_error', function(data) {
        console.error('Errore:', data);
        updateStatus(`Errore: ${data.error}`, 'error');
    });

    socket.on('config_detected', function(data) {
        console.log('Configurazione rilevata:', data.message);
        // Opzionale: mostra un messaggio all'utente
        const statusDiv = document.getElementById('statusMessage');
        const currentMessage = statusDiv.textContent;
        statusDiv.textContent = currentMessage + ' - ' + data.message;
    });
}

function setExpectedItems() {
    // Imposta metriche attese per categoria
    const weatherMetrics = [
        'EIT_WINDVEL', 'EIT_WINDDIR1', 'EIT_HUMIDITY', 
        'EIT_TEMPERATURE', 'EIT_PIROMETER'
    ];
    
    const junctionBoxMetrics = [
        'EIT_ACCEL_X', 'EIT_ACCEL_Y', 'EIT_ACCEL_Z',
        'EIT_INCLIN_X', 'EIT_INCLIN_Y'
    ];
    
    let loadMetrics = [];
    
    if (numSensors === 3) {
        loadMetrics = ['EIT_LOAD_04_A_L1', 'EIT_LOAD_08_A_L1', 'EIT_LOAD_12_A_L1'];
        expectedAlarms = ['VAR_32', 'VAR_36', 'VAR_40'];
    } else if (numSensors === 6) {
        loadMetrics = [
            'EIT_LOAD_04_A_L1', 'EIT_LOAD_04_B_L1',
            'EIT_LOAD_08_A_L1', 'EIT_LOAD_08_B_L1',
            'EIT_LOAD_12_A_L1', 'EIT_LOAD_12_B_L1'
        ];
        expectedAlarms = ['VAR_32', 'VAR_34', 'VAR_36', 'VAR_38', 'VAR_40', 'VAR_42'];
    } else {
        // 12 sensori
        for (let load of ['04', '08', '12']) {
            for (let side of ['A', 'B']) {
                for (let line of ['L1', 'L2']) {
                    loadMetrics.push(`EIT_LOAD_${load}_${side}_${line}`);
                }
            }
        }
        expectedAlarms = [
            'VAR_32', 'VAR_33', 'VAR_34', 'VAR_35',
            'VAR_36', 'VAR_37', 'VAR_38', 'VAR_39',
            'VAR_40', 'VAR_41', 'VAR_42', 'VAR_43'
        ];
    }
    
    // Combina tutte le metriche
    expectedMetrics = [...weatherMetrics, ...junctionBoxMetrics, ...loadMetrics];
    
    // Salva le categorie per uso futuro
    window.metricCategories = {
        weather: weatherMetrics,
        junctionBox: junctionBoxMetrics,
        load: loadMetrics
    };
    
    // Inizializza liste in attesa
    updateWaitingMetrics(expectedMetrics);
    updateWaitingAlarms(expectedAlarms.map(a => `EGM_OUT_SENS_23_${a}`));
}

function startMonitoring() {
    if (!deviceId) {
        alert('Device ID mancante!');
        return;
    }
    
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    
    socket.emit('start_unified_monitoring', {
        device_id: deviceId,
        num_sensors: numSensors,
        ui: ui,
        timeout_minutes: timeout
    });
}

function stopMonitoring() {
    socket.emit('stop_monitoring');
    stopTimer();
    updateStatus('Monitoraggio interrotto', 'info');
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
}

// Funzioni timer
function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function updateTimer() {
    if (!startTime) return;
    
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    
    document.getElementById('timer').textContent = 
        `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// Funzioni per metriche
function addFoundMetric(data) {
    const foundDiv = document.getElementById('foundMetrics');
    
    // Determina la categoria della metrica
    let category = '📊';
    if (window.metricCategories) {
        if (window.metricCategories.weather.includes(data.metric_type)) {
            category = '🌤️';
        } else if (window.metricCategories.junctionBox.includes(data.metric_type)) {
            category = '📦';
        } else if (window.metricCategories.load.includes(data.metric_type)) {
            category = '⚡';
        }
    }
    
    const sourceIcon = data.source === 'lastval' ? '📌' : '📡';
    const dateFormatted = getCurrentDateFormatted();
    
    // Controlla se la metrica esiste già
    let existingItem = document.getElementById(`metric-${data.metric_type}`);
    
    if (existingItem) {
        // Aggiorna l'elemento esistente
        existingItem.innerHTML = `
            <strong>${category} ${data.metric_type} [${sourceIcon} ${data.source}]</strong><br>
            📍 ${dateFormatted} - ${data.timestamp} - Valore: ${data.value}
        `;
        // Flash per indicare aggiornamento
        existingItem.style.backgroundColor = '#ccffcc';
        setTimeout(() => {
            existingItem.style.backgroundColor = '';
        }, 500);
    } else {
        // Crea nuovo elemento
        const itemDiv = document.createElement('div');
        itemDiv.id = `metric-${data.metric_type}`;
        itemDiv.className = 'item found';
        itemDiv.innerHTML = `
            <strong>${category} ${data.metric_type} [${sourceIcon} ${data.source}]</strong><br>
            📍 ${dateFormatted} - ${data.timestamp} - Valore: ${data.value}
        `;
        foundDiv.appendChild(itemDiv);
    }
    
    // Salva i dati SEMPRE
    foundMetricsData[data.metric_type] = data;
    
    // Controlla se deve essere nascosta visivamente (solo per display locale)
    if (isDataTooOld(data.timestamp) && !historicalMode) {
        const element = document.getElementById(`metric-${data.metric_type}`);
        if (element) {
            element.style.display = 'none';
            console.log(`Metrica ${data.metric_type} nascosta visivamente (troppo vecchia)`);
        }
    }
    
    // Aggiorna contatori
    updateFilteredCounts();
}

function updateMetricsProgress(data) {
    // Usa conteggi locali filtrati invece di quelli del server
    const visibleMetrics = Object.values(foundMetricsData)
        .filter(m => !isDataTooOld(m.timestamp)).length;
    
    const percentage = (visibleMetrics / data.total_expected) * 100;
    const progressFill = document.getElementById('metricsProgress');
    progressFill.style.width = `${percentage}%`;
    progressFill.textContent = `${visibleMetrics} / ${data.total_expected}`;
    
    updateWaitingMetrics(data.missing_list);
}

function updateWaitingMetrics(missingList) {
    const waitingDiv = document.getElementById('waitingMetrics');
    waitingDiv.innerHTML = '';
    
    missingList.forEach(metric => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'item waiting';
        itemDiv.innerHTML = `<strong>${metric}</strong><br>⏳ In attesa...`;
        waitingDiv.appendChild(itemDiv);
    });
}

// Funzioni per allarmi
function addFoundAlarm(data) {
    const foundDiv = document.getElementById('foundAlarms');
    const friendlyName = alarmDescriptions[data.alarm_type] || data.alarm_type;
    const dateFormatted = getCurrentDateFormatted();
    
    // Controlla se l'allarme esiste già
    let existingItem = document.getElementById(`alarm-${data.alarm_type}`);
    
    if (existingItem) {
        // Aggiorna l'elemento esistente
        existingItem.innerHTML = `
            <strong>🚨 ${data.alarm_type} - ${friendlyName}</strong><br>
            📍 ${dateFormatted} - ${data.timestamp} - Valore: ${data.value}
        `;
        // Flash per indicare aggiornamento
        existingItem.style.backgroundColor = '#ffffcc';
        setTimeout(() => {
            existingItem.style.backgroundColor = '';
        }, 500);
    } else {
        // Crea nuovo elemento
        const itemDiv = document.createElement('div');
        itemDiv.id = `alarm-${data.alarm_type}`;
        itemDiv.className = 'item found';
        itemDiv.innerHTML = `
            <strong>🚨 ${data.alarm_type} - ${friendlyName}</strong><br>
            📍 ${dateFormatted} - ${data.timestamp} - Valore: ${data.value}
        `;
        foundDiv.appendChild(itemDiv);
    }
    
    // Salva i dati SEMPRE
    foundAlarmsData[data.alarm_type] = data;
    
    // Controlla se deve essere nascosto visualmente (solo per display locale)
    if (isDataTooOld(data.timestamp) && !historicalMode) {
        const element = document.getElementById(`alarm-${data.alarm_type}`);
        if (element) {
            element.style.display = 'none';
            console.log(`Allarme ${data.alarm_type} nascosto visualmente (troppo vecchio)`);
        }
    }
    
    // Aggiorna contatori
    updateFilteredCounts();
}

function addOtherAlarm(data) {
    document.getElementById('otherAlarmsSection').style.display = 'block';
    
    const otherDiv = document.getElementById('otherAlarms');
    const itemDiv = document.createElement('div');
    itemDiv.className = 'item other';
    
    const friendlyName = alarmDescriptions[data.alarm_type] || data.alarm_type;
    const dateFormatted = getCurrentDateFormatted();
    
    itemDiv.innerHTML = `
        <strong>${data.alarm_type} - ${friendlyName}</strong><br>
        📍 ${dateFormatted} - ${data.timestamp} - Valore: ${data.value}
    `;
    otherDiv.appendChild(itemDiv);
    
    otherAlarmsData[data.alarm_type] = data;
}

function updateAlarmsProgress(data) {
    const percentage = (data.found_count / data.total_expected) * 100;
    const progressFill = document.getElementById('alarmsProgress');
    progressFill.style.width = `${percentage}%`;
    progressFill.textContent = `${data.found_count} / ${data.total_expected}`;
    
    updateWaitingAlarms(data.missing_list);
}

function updateWaitingAlarms(missingList) {
    const waitingDiv = document.getElementById('waitingAlarms');
    waitingDiv.innerHTML = '';
    
    missingList.forEach(alarm => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'item waiting';
        const friendlyName = alarmDescriptions[alarm] || alarm;
        itemDiv.innerHTML = `<strong>${alarm} - ${friendlyName}</strong><br>⏳ In attesa...`;
        waitingDiv.appendChild(itemDiv);
    });
}

// Funzioni comuni
function updateStatus(message, type) {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.textContent = message;
    statusDiv.className = `status-message status-${type}`;
    statusDiv.style.display = 'block';
}

function playNotificationSound() {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.value = 800;
    oscillator.type = 'sine';
    gainNode.gain.value = 0.1;
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.1);
}

function toggleHistoricalMode() {
    const checkbox = document.getElementById('historicalMode');
    const timeWindowContainer = document.getElementById('timeWindowContainer');
    const modeDescription = document.getElementById('modeDescription');
    
    historicalMode = checkbox.checked;
    
    console.log('📊 Toggle Historical Mode:', {
        checked: checkbox.checked,
        historicalMode: historicalMode,
        timeWindow: timeWindowMinutes
    });
    
    if (historicalMode) {
        // Modalità storica
        timeWindowContainer.style.opacity = '0.5';
        timeWindowContainer.style.pointerEvents = 'none';
        modeDescription.innerHTML = '📚 Modalità Storica: mostra tutti i dati disponibili';
        modeDescription.style.color = '#17a2b8';
    } else {
        // Modalità live
        timeWindowContainer.style.opacity = '1';
        timeWindowContainer.style.pointerEvents = 'auto';
        const minutes = document.getElementById('timeWindow').value;
        modeDescription.innerHTML = `🔄 Modalità Live: mostra solo dati degli ultimi ${minutes} minuti`;
        modeDescription.style.color = '#6c757d';
    }
    
    // Invia aggiornamento al server
    if (socket && socket.connected) {
        console.log('📤 Invio update_time_filter al server con:', {
            historical_mode: historicalMode,
            time_window_minutes: timeWindowMinutes
        });
        
        socket.emit('update_time_filter', {
            historical_mode: historicalMode,
            time_window_minutes: timeWindowMinutes
        });
        
        // Aspetta conferma
        socket.once('filter_updated', function(data) {
            console.log('✅ Conferma dal server - Filtro aggiornato:', data);
        });
    } else {
        console.error('❌ Socket non connesso! Impossibile aggiornare filtro sul server');
    }
    
    // Riapplica il filtro ai dati esistenti localmente
    refilterExistingData();
}

function updateTimeWindow() {
    const select = document.getElementById('timeWindow');
    timeWindowMinutes = parseInt(select.value);
    
    const modeDescription = document.getElementById('modeDescription');
    let timeText;
    
    if (timeWindowMinutes === 60) {
        timeText = '1 ora';
    } else if (timeWindowMinutes === 120) {
        timeText = '2 ore';
    } else if (timeWindowMinutes === 150) {
        timeText = '2 ore e 30 minuti';
    } else {
        timeText = `${timeWindowMinutes} minuti`;
    }
    
    modeDescription.innerHTML = `🔄 Modalità Live: mostra solo dati degli ultimi ${timeText}`;
    
    // Invia aggiornamento al server
    if (socket) {
        socket.emit('update_time_filter', {
            historical_mode: historicalMode,
            time_window_minutes: timeWindowMinutes
        });
    }
    
    // Riapplica il filtro ai dati esistenti
    refilterExistingData();
}

function isDataTooOld(timestampStr) {
    // Se siamo in modalità storica, accetta tutto
    if (historicalMode) {
        return false;
    }
    
    // Parsing del timestamp (formato "HH:MM:SS" o timestamp unix)
    let dataTime;
    
    if (timestampStr.includes(':')) {
        // Formato HH:MM:SS - assumiamo sia di oggi
        const [hours, minutes, seconds] = timestampStr.split(':').map(Number);
        dataTime = new Date();
        dataTime.setHours(hours, minutes, seconds, 0);
    } else {
        // Timestamp unix
        dataTime = new Date(parseInt(timestampStr));
    }
    
    const now = new Date();
    const diffMinutes = (now - dataTime) / (1000 * 60);
    
    return diffMinutes > timeWindowMinutes;
}

function refilterExistingData() {
    // Rifiltra metriche
    const foundMetricsDiv = document.getElementById('foundMetrics');
    const waitingMetricsDiv = document.getElementById('waitingMetrics');
    
    // Nascondi/mostra metriche basandosi sul timestamp
    for (const [metric, data] of Object.entries(foundMetricsData)) {
        const element = document.getElementById(`metric-${metric}`);
        if (element) {
            if (isDataTooOld(data.timestamp)) {
                element.style.display = 'none';
                // Aggiungi di nuovo alla lista waiting se filtrato
                if (!historicalMode) {
                    const waitingItem = document.createElement('div');
                    waitingItem.className = 'item waiting';
                    waitingItem.id = `waiting-metric-${metric}`;
                    waitingItem.innerHTML = `<strong>${metric}</strong><br>⏳ In attesa di dati recenti...`;
                    waitingMetricsDiv.appendChild(waitingItem);
                }
            } else {
                element.style.display = 'block';
                // Rimuovi dalla lista waiting se presente
                const waitingElement = document.getElementById(`waiting-metric-${metric}`);
                if (waitingElement) {
                    waitingElement.remove();
                }
            }
        }
    }
    
    // Rifiltra allarmi
    const foundAlarmsDiv = document.getElementById('foundAlarms');
    const waitingAlarmsDiv = document.getElementById('waitingAlarms');
    
    for (const [alarm, data] of Object.entries(foundAlarmsData)) {
        const element = document.getElementById(`alarm-${alarm}`);
        if (element) {
            if (isDataTooOld(data.timestamp)) {
                element.style.display = 'none';
                // Aggiungi di nuovo alla lista waiting se filtrato
                if (!historicalMode) {
                    const waitingItem = document.createElement('div');
                    waitingItem.className = 'item waiting';
                    waitingItem.id = `waiting-alarm-${alarm}`;
                    const friendlyName = alarmDescriptions[alarm] || alarm;
                    waitingItem.innerHTML = `<strong>${alarm} - ${friendlyName}</strong><br>⏳ In attesa di dati recenti...`;
                    waitingAlarmsDiv.appendChild(waitingItem);
                }
            } else {
                element.style.display = 'block';
                // Rimuovi dalla lista waiting se presente
                const waitingElement = document.getElementById(`waiting-alarm-${alarm}`);
                if (waitingElement) {
                    waitingElement.remove();
                }
            }
        }
    }
    
    // Aggiorna contatori
    updateFilteredCounts();
}

function updateFilteredCounts() {
    // Conta elementi visibili
    let visibleMetrics = 0;
    let visibleAlarms = 0;
    
    for (const [metric, data] of Object.entries(foundMetricsData)) {
        if (!isDataTooOld(data.timestamp)) {
            visibleMetrics++;
        }
    }
    
    for (const [alarm, data] of Object.entries(foundAlarmsData)) {
        if (!isDataTooOld(data.timestamp)) {
            visibleAlarms++;
        }
    }
    
    // Aggiorna progress bars
    const metricsProgress = document.getElementById('metricsProgress');
    const alarmsProgress = document.getElementById('alarmsProgress');
    
    const metricsPercentage = (visibleMetrics / expectedMetrics.length) * 100;
    const alarmsPercentage = (visibleAlarms / expectedAlarms.length) * 100;
    
    metricsProgress.style.width = `${metricsPercentage}%`;
    metricsProgress.textContent = `${visibleMetrics} / ${expectedMetrics.length}`;
    
    alarmsProgress.style.width = `${alarmsPercentage}%`;
    alarmsProgress.textContent = `${visibleAlarms} / ${expectedAlarms.length}`;
}

function playSuccessSound() {
    for (let i = 0; i < 3; i++) {
        setTimeout(playNotificationSound, i * 200);
    }
}

// Inizializza al caricamento
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
});