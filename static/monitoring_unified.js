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
    const itemDiv = document.createElement('div');
    itemDiv.className = 'item found';
    
    // Determina la categoria della metrica
    let category = '📊';
    if (window.metricCategories) {
        if (window.metricCategories.weather.includes(data.metric_type)) {
            category = '🌤️'; // Centralina Meteo
        } else if (window.metricCategories.junctionBox.includes(data.metric_type)) {
            category = '📦'; // Smart Junction Box
        } else if (window.metricCategories.load.includes(data.metric_type)) {
            category = '⚡'; // Sensori di Tiro
        }
    }
    
    // Mostra anche la fonte se disponibile
    const sourceIcon = data.source === 'lastval' ? '📌' : '📡';
    const sourceText = data.source ? ` [${sourceIcon} ${data.source}]` : '';
    
    itemDiv.innerHTML = `
        <strong>${category} ${data.metric_type}${sourceText}</strong><br>
        📍 ${data.timestamp} - Valore: ${data.value}
    `;
    foundDiv.appendChild(itemDiv);
    
    foundMetricsData[data.metric_type] = data;
}

function updateMetricsProgress(data) {
    const percentage = (data.found_count / data.total_expected) * 100;
    const progressFill = document.getElementById('metricsProgress');
    progressFill.style.width = `${percentage}%`;
    progressFill.textContent = `${data.found_count} / ${data.total_expected}`;
    
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
    const itemDiv = document.createElement('div');
    itemDiv.className = 'item found';
    
    const friendlyName = alarmDescriptions[data.alarm_type] || data.alarm_type;
    
    itemDiv.innerHTML = `
        <strong>🚨 ${data.alarm_type} - ${friendlyName}</strong><br>
        📍 ${data.timestamp} - Valore: ${data.value}
    `;
    foundDiv.appendChild(itemDiv);
    
    foundAlarmsData[data.alarm_type] = data;
}

function addOtherAlarm(data) {
    document.getElementById('otherAlarmsSection').style.display = 'block';
    
    const otherDiv = document.getElementById('otherAlarms');
    const itemDiv = document.createElement('div');
    itemDiv.className = 'item other';
    
    const friendlyName = alarmDescriptions[data.alarm_type] || data.alarm_type;
    
    itemDiv.innerHTML = `
        <strong>${data.alarm_type} - ${friendlyName}</strong><br>
        📍 ${data.timestamp} - Valore: ${data.value}
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

function playSuccessSound() {
    for (let i = 0; i < 3; i++) {
        setTimeout(playNotificationSound, i * 200);
    }
}

// Inizializza al caricamento
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
});