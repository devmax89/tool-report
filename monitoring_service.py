# monitoring_service.py
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import time
from datetime import datetime, timedelta
from digil_test_service import digil_test_service
from mongodb_checker import MongoDBAlarmChecker, get_alarm_metrics_for_sensor

class AlarmMonitor:
    def __init__(self, socketio):
        self.socketio = socketio
        self.monitoring_threads = {}
        self.stop_events = {}
        
        # 🆕 NUOVO: Inizializza MongoDB checker
        self.mongo_checker = None
        try:
            self.mongo_checker = MongoDBAlarmChecker()
            if self.mongo_checker.connect():
                print("✅ MongoDB checker inizializzato e connesso")
            else:
                print("⚠️  MongoDB checker non disponibile - fallback su solo valori EGM")
                self.mongo_checker = None
        except Exception as e:
            print(f"⚠️  MongoDB checker init failed: {e} - fallback su solo valori EGM")
            self.mongo_checker = None
    
    def start_unified_monitoring(self, sid, device_id, num_sensors, ui, timeout_minutes=10):
        """Avvia il monitoraggio unificato per metriche e allarmi"""
        
        # INIZIALIZZA session_filters SE NON ESISTE
        if not hasattr(self, 'session_filters'):
            self.session_filters = {}
        
        # CREA FILTRO CON VALORI DI DEFAULT
        # Controlla se ci sono parametri nel thread config (passati dal frontend)
        if sid in self.monitoring_threads:
            thread_config = self.monitoring_threads[sid]
            historical_mode = thread_config.get('historical_mode', False)
            time_window = thread_config.get('time_window', 10)
        else:
            # Default: modalità live con 10 minuti
            historical_mode = False
            time_window = 10
        
        self.session_filters[sid] = {
            'historical_mode': historical_mode,
            'time_window_minutes': time_window,
            'start_time': datetime.now()
        }
        
        print(f"📝 Filtro inizializzato per sid {sid}:")
        print(f"   Historical mode: {historical_mode}")
        print(f"   Time window: {time_window} minuti")
        
        # Crea evento di stop per questo client
        stop_event = Event()
        self.stop_events[sid] = stop_event
        
        # Avvia thread di monitoraggio unificato
        thread = Thread(
            target=self._unified_monitor_loop,
            args=(sid, device_id, num_sensors, ui, timeout_minutes, stop_event)
        )
        thread.daemon = True
        thread.start()
        self.monitoring_threads[sid] = thread
    
    def start_monitoring(self, sid, device_id, num_sensors, ui, timeout_minutes=10):
        """Mantieni per compatibilità - ora chiama unified"""
        self.start_unified_monitoring(sid, device_id, num_sensors, ui, timeout_minutes)
        
    def stop_monitoring(self, sid):
        """Ferma il monitoraggio per una sessione"""
        if sid in self.stop_events:
            self.stop_events[sid].set()
            del self.stop_events[sid]
        if sid in self.monitoring_threads:
            del self.monitoring_threads[sid]
        
        # MongoDB rimane connesso per tutto il lifetime dell'applicazione
        # Si disconnetterà automaticamente alla chiusura dell'app
        print(f"✅ Monitoraggio fermato per {sid} - Thread attivi: {len(self.monitoring_threads)}")            

    def update_time_filter(self, sid, historical_mode, time_window_minutes):
        """Aggiorna le impostazioni del filtro temporale per una sessione"""
        
        # Salva le impostazioni per questa sessione
        if not hasattr(self, 'session_filters'):
            self.session_filters = {}
        
        self.session_filters[sid] = {
            'historical_mode': historical_mode,
            'time_window_minutes': time_window_minutes
        }
        
        print(f"📅 Filtro temporale aggiornato per {sid}: "
            f"{'Modalità Storica' if historical_mode else f'Live {time_window_minutes} min'}")

    def should_filter_data(self, sid, timestamp):
        """Determina se un dato deve essere filtrato in base al timestamp"""

        # Se non ci sono impostazioni, usa default (no filter)
        if not hasattr(self, 'session_filters') or sid not in self.session_filters:
            print(f"   ⚠️ Nessuna impostazione per sid {sid}, uso default")
            return False
        
        settings = self.session_filters[sid]
        
        # Se siamo in modalità storica, non filtrare nulla
        if settings['historical_mode']:
            return False
        
        # Calcola la differenza temporale
        from datetime import datetime
        
        # Se timestamp è in millisecondi, convertilo
        if timestamp > 10000000000:  # Probabilmente in millisecondi
            data_time = datetime.fromtimestamp(timestamp / 1000)
        else:
            data_time = datetime.fromtimestamp(timestamp)
        
        current_time = datetime.now()
        diff_minutes = (current_time - data_time).total_seconds() / 60
        
        # Filtra se il dato è più vecchio della finestra temporale
        return diff_minutes > settings['time_window_minutes']
    
    def check_mongodb_alarm(self, device_id, egm_sensor_metric):
        """
        Verifica il booleano MongoDB per un sensore specifico.
        🆕 MODIFICA: Cerca SOLO il Max alarm per sensori di tiro (Min è inaffidabile)
        """
        result = {
            'found': False,
            'active': False,
            'timestamp': None,
            'timestamp_unix': None,  # Assicurati che ci sia questo campo!
            'metric_found': None
        }
        
        if self.mongo_checker is None:
            return result
        
        # Ottieni le metriche EAM corrispondenti (Min e Max)
        eam_metrics = get_alarm_metrics_for_sensor(egm_sensor_metric)
        
        if not eam_metrics:
            return result
        
        # 🆕 NUOVO: Per sensori di tiro, cerca SOLO il Max alarm (più affidabile)
        if len(eam_metrics) == 2:
            # Ha sia Min che Max → prendi solo Max (indice 1)
            eam_metrics = [eam_metrics[1]]
            print(f"   🎯 Sensore tiro: cerco solo Max alarm {eam_metrics[0]}")
        
        # Controlla le metriche (ora solo Max per sensori tiro)
        for eam_metric in eam_metrics:
            try:
                mongo_result = self.mongo_checker.check_alarm_boolean(
                    device_id, 
                    eam_metric,
                    timeout=5
                )
                
                if mongo_result['active']:
                    # Trovato un true!
                    result['found'] = True
                    result['active'] = True
                    result['timestamp'] = mongo_result['timestamp']
                    result['timestamp_unix'] = mongo_result.get('timestamp_unix')  # ← usa .get()
                    result['metric_found'] = mongo_result['metric_checked']
                    print(f"   ✅ MongoDB TRUE found: {eam_metric}_calc")
                    return result  # Ritorna subito
                    
            except Exception as e:
                print(f"   ⚠️  MongoDB query error for {eam_metric}: {e}")
                continue
        
        return result
    
    def _unified_monitor_loop(self, sid, device_id, num_sensors, ui, timeout_minutes, stop_event):
        """Loop principale di monitoraggio unificato con tripla verifica metriche e validazione allarmi"""
        print(f"🔍 Monitoraggio avviato con sid: {sid}")
        monitoring_start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        check_interval = 5
        
        # Mappatura allarmi
        alarm_mapping = {
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
            'EGM_OUT_SENS_23_VAR_31': 'Inc_Y'
        }
        
        # Traccia quali metriche hanno almeno una lettura (per progress)
        metrics_with_data = set()
        expected_metrics = self._get_expected_metrics(num_sensors)
        
        # Dati per allarmi
        found_alarms = {}
        other_alarms = {}
        alarm_config = self._get_expected_alarms(num_sensors)
        
        if isinstance(alarm_config, dict):
            expected_alarms = alarm_config['primary']
            is_flexible = alarm_config.get('flexible', False)
        else:
            expected_alarms = alarm_config
            is_flexible = False
        
        event_history = []
        all_received_alarms = {}
        
        while not stop_event.is_set():
            current_time = datetime.now()
            elapsed = current_time - monitoring_start_time
            
            # Controlla timeout
            if elapsed > timeout:
                self.socketio.emit('monitoring_timeout', {
                    'message': f'Timeout raggiunto ({timeout_minutes} minuti)',
                    'metrics': {
                        'found': list(metrics_with_data),
                        'missing': [m for m in expected_metrics if m not in metrics_with_data]
                    },
                    'alarms': {
                        'found': list(found_alarms.keys()),
                        'missing': [a for a in expected_alarms if a not in found_alarms],
                        'other': other_alarms
                    },
                    'history': event_history
                }, room=sid)
                break
            
            try:
                
                # STEP 1 - CARICA API AGGREGATA per metriche mancanti
                agg_data = None
                success_agg, agg_data = digil_test_service.get_device_aggregated_data(device_id)
                
                if not success_agg or not agg_data:
                    print(f"⚠️ API aggregata non disponibile (elapsed: {elapsed.total_seconds():.0f}s)")
                    agg_data = {'measures': {}}  # Crea struttura vuota
                else:
                    measures_count = len(agg_data.get('measures', {}))
                    print(f"✅ API aggregata OK: {measures_count} measures")
                
                # Calcola range temporale
                end_timestamp = int(current_time.timestamp())
                start_timestamp = end_timestamp - 300  # Ultimi 5 minuti
                
                # STEP 2 - CHECK METRICHE DALLA TELEMETRIA
                success_tm, tm_data = digil_test_service.get_telemetry_data(
                    device_id, ui, start_timestamp, end_timestamp
                )

                if success_tm and 'tm' in tm_data and tm_data['tm']:
                    for tm_entry in tm_data['tm']:
                        packet_timestamp = tm_entry.get('timestamp', 0) / 1000
                        
                        if self.should_filter_data(sid, packet_timestamp):
                            continue
                        
                        # Formatta timestamp con data e ora
                        packet_datetime = datetime.fromtimestamp(packet_timestamp)
                        formatted_timestamp = packet_datetime.strftime('%d/%m/%y - %H:%M:%S')
                        
                        if 'metrics' in tm_entry:
                            for idx, metric in enumerate(tm_entry['metrics']):
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                
                                # Formatta timestamp con progressivo se necessario
                                if len(tm_entry['metrics']) > 1:
                                    display_time = f"{formatted_timestamp}.{idx:02d}"
                                else:
                                    display_time = formatted_timestamp
                                
                                if metric_type in expected_metrics:
                                    metrics_with_data.add(metric_type)
                                    
                                    metric_entry = {
                                        'metric_type': metric_type,
                                        'value': metric_val,
                                        'timestamp': display_time,
                                        'elapsed': str(elapsed).split('.')[0],
                                        'source': 'telemetry'
                                    }
                                    event_history.append(('metric', metric_entry))
                                    self.socketio.emit('metric_found', metric_entry, room=sid)

                # 🔥 STEP 4: CHECK LASTVAL PER METRICHE E ALLARMI
                success_lv, lastval_data = digil_test_service.get_lastval_data(device_id, ui)

                if success_lv and 'lastVal' in lastval_data:
                    current_received_alarms = {}
                    
                    for entry in lastval_data.get('lastVal', []):
                        # 🆕 SMART: Rileva formato timestamp automaticamente
                        raw_timestamp = entry.get('timestamp', 0)
                        relative_timestamp = raw_timestamp / 1000  # Converti millisecondi a secondi
                        
                        # Distingui tra timestamp assoluto (Unix epoch) e relativo (dall'inizio test)
                        # Threshold: 1000000000 secondi = 9 settembre 2001
                        if relative_timestamp > 1000000000:
                            # Timestamp assoluto Unix (es: 1761638447.598)
                            packet_timestamp = relative_timestamp
                        else:
                            # Timestamp relativo (es: 220.933)
                            start_time = self.session_filters[sid]['start_time']
                            packet_timestamp = start_time.timestamp() + relative_timestamp
                        
                        if self.should_filter_data(sid, packet_timestamp):
                            continue
                        
                        packet_datetime = datetime.fromtimestamp(packet_timestamp)
                        formatted_timestamp = packet_datetime.strftime('%d/%m/%y - %H:%M:%S')
                        
                        if 'metrics' in entry:
                            for idx, metric in enumerate(entry['metrics']):
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                
                                # Formatta timestamp con progressivo per multiple metriche
                                if len(entry['metrics']) > 1:
                                    display_time = f"{formatted_timestamp}.{idx:02d}"
                                else:
                                    display_time = formatted_timestamp
                                
                                # Gestione metriche
                                if metric_type in expected_metrics:
                                    metrics_with_data.add(metric_type)
                                    
                                    metric_entry = {
                                        'metric_type': metric_type,
                                        'value': metric_val,
                                        'timestamp': display_time,
                                        'elapsed': str(elapsed).split('.')[0],
                                        'source': 'lastval'
                                    }
                                    event_history.append(('metric', metric_entry))
                                    self.socketio.emit('metric_found', metric_entry, room=sid)
                                
                                # 🔥 Gestione allarmi CON VALIDAZIONE
                                if 'EGM_OUT_SENS' in metric_type and metric_type in alarm_mapping:
                                    current_received_alarms[metric_type] = metric_val
                                    
                                    if metric_type not in all_received_alarms:
                                        all_received_alarms[metric_type] = metric_val                              
                                    
                                    if metric_type in expected_alarms:
                                        if metric_type not in found_alarms:
                                            found_alarms[metric_type] = packet_timestamp
                                            alarm_entry = {
                                                'alarm_type': metric_type,
                                                'value': metric_val,
                                                'timestamp': formatted_timestamp,
                                                'elapsed': str(elapsed).split('.')[0],
                                                'is_expected': True
                                            }
                                            event_history.append(('alarm', alarm_entry))
                                            self.socketio.emit('alarm_found', alarm_entry, room=sid)
                                    else:
                                        if metric_type not in other_alarms:
                                            other_alarms[metric_type] = metric_val
                                            other_alarm_entry = {
                                                'alarm_type': metric_type,
                                                'value': metric_val,
                                                'timestamp': formatted_timestamp,
                                                'elapsed': str(elapsed).split('.')[0],
                                                'is_expected': False
                                            }
                                            event_history.append(('other_alarm', other_alarm_entry))
                                            self.socketio.emit('other_alarm_found', other_alarm_entry, room=sid)
                    
                    # 🔥 Gestione allarmi flessibili
                    if is_flexible and isinstance(alarm_config, dict):
                        if num_sensors == 3:
                            primary_count = sum(1 for alarm in alarm_config['primary'] if alarm in all_received_alarms)
                            alt_count = sum(1 for alarm in alarm_config.get('alternative', []) if alarm in all_received_alarms)
                            
                            if alt_count > primary_count and alt_count > 0:
                                if expected_alarms != alarm_config['alternative']:
                                    expected_alarms = alarm_config['alternative']
                                    self.socketio.emit('config_detected', {
                                        'message': 'Rilevata configurazione 3 sensori lato B'
                                    }, room=sid)
                        
                        elif num_sensors == 6:
                            new_expected = list(alarm_config['primary'])
                            for alarm in all_received_alarms:
                                if alarm in alarm_config.get('acceptable', []) and alarm not in new_expected:
                                    new_expected.append(alarm)
                                    if len(new_expected) > len(expected_alarms):
                                        self.socketio.emit('config_detected', {
                                            'message': f'Aggiunto allarme {alarm} agli attesi'
                                        }, room=sid)
                            expected_alarms = new_expected

                # 🔥 STEP 5: FALLBACK API AGGREGATA per metriche/allarmi mancanti
                missing_metrics = [m for m in expected_metrics if m not in metrics_with_data]
                missing_alarms = [a for a in expected_alarms if a not in found_alarms]

                if (missing_metrics or missing_alarms) and agg_data and 'measures' in agg_data:
                    measures = agg_data['measures']
                    
                    # Processa metriche mancanti
                    for measure_key, measure_data in measures.items():
                        if measure_key in digil_test_service.reverse_metrics_mapping:
                            eit_metric = digil_test_service.reverse_metrics_mapping[measure_key]
                            
                            if eit_metric in missing_metrics and measure_data and isinstance(measure_data, dict) and len(measure_data) > 0:
                                measure_timestamp = measure_data.get('timestamp', 0) / 1000

                                if self.should_filter_data(sid, measure_timestamp):
                                    continue

                                # Formatta timestamp con data
                                measure_datetime = datetime.fromtimestamp(measure_timestamp)
                                display_time = measure_datetime.strftime('%d/%m/%y - %H:%M:%S')
                                
                                if 'avg' in measure_data:
                                    value = f"min:{measure_data.get('min', 'N/A')}, avg:{measure_data.get('avg', 'N/A')}, max:{measure_data.get('max', 'N/A')}"
                                elif 'value' in measure_data:
                                    value = str(measure_data.get('value', 'N/A'))
                                else:
                                    continue
                                
                                metrics_with_data.add(eit_metric)
                                
                                metric_entry = {
                                    'metric_type': eit_metric,
                                    'value': value,
                                    'timestamp': display_time,
                                    'elapsed': str(elapsed).split('.')[0],
                                    'source': 'aggregated'
                                }
                                event_history.append(('metric', metric_entry))
                                self.socketio.emit('metric_found', metric_entry, room=sid)
                    
                    # Gestione allarmi aggregati
                    measures_to_alarms = {
                        'SENS_Digil2_TC_F12A_L1_IN_ALARM': 'EGM_OUT_SENS_23_VAR_32',
                        'SENS_Digil2_TC_F12A_L2_IN_ALARM': 'EGM_OUT_SENS_23_VAR_33',
                        'SENS_Digil2_TC_F12B_L1_IN_ALARM': 'EGM_OUT_SENS_23_VAR_34',
                        'SENS_Digil2_TC_F12B_L2_IN_ALARM': 'EGM_OUT_SENS_23_VAR_35',
                        'SENS_Digil2_TC_F4A_L1_IN_ALARM': 'EGM_OUT_SENS_23_VAR_36',
                        'SENS_Digil2_TC_F4A_L2_IN_ALARM': 'EGM_OUT_SENS_23_VAR_37',
                        'SENS_Digil2_TC_F4B_L1_IN_ALARM': 'EGM_OUT_SENS_23_VAR_38',
                        'SENS_Digil2_TC_F4B_L2_IN_ALARM': 'EGM_OUT_SENS_23_VAR_39',
                        'SENS_Digil2_TC_F8A_L1_IN_ALARM': 'EGM_OUT_SENS_23_VAR_40',
                        'SENS_Digil2_TC_F8A_L2_IN_ALARM': 'EGM_OUT_SENS_23_VAR_41',
                        'SENS_Digil2_TC_F8B_L1_IN_ALARM': 'EGM_OUT_SENS_23_VAR_42',
                        'SENS_Digil2_TC_F8B_L2_IN_ALARM': 'EGM_OUT_SENS_23_VAR_43',
                        'SENS_Digil2_Inc_X_IN_ALARM': 'EGM_OUT_SENS_23_VAR_30',
                        'SENS_Digil2_Inc_Y_IN_ALARM': 'EGM_OUT_SENS_23_VAR_31'
                    }
                    
                    for measure_key, alarm_key in measures_to_alarms.items():
                        if alarm_key in missing_alarms and measure_key in measures:
                            measure_data = measures[measure_key]
                            if measure_data and 'value' in measure_data:
                                measure_timestamp = measure_data.get('timestamp', 0) / 1000

                                if self.should_filter_data(sid, measure_timestamp):
                                    continue

                                # Formatta timestamp con formato unificato
                                measure_datetime = datetime.fromtimestamp(measure_timestamp)
                                display_time = measure_datetime.strftime('%d/%m/%y - %H:%M:%S')
                                
                                found_alarms[alarm_key] = measure_timestamp

                                print(f"💾 ALARM FROM AGGREGATED API: {alarm_key} @ {measure_timestamp}")
                                
                                alarm_entry = {
                                    'alarm_type': alarm_key,
                                    'value': measure_data['value'],
                                    'timestamp': display_time,
                                    'elapsed': str(elapsed).split('.')[0],
                                    'is_expected': True,
                                    'source': 'aggregated'
                                }
                                event_history.append(('alarm', alarm_entry))
                                self.socketio.emit('alarm_found', alarm_entry, room=sid)

                # 🆕 STEP 5.5: VERIFICA MONGODB per allarmi mancanti O CON TIMESTAMP VECCHIO
                missing_alarms = [a for a in expected_alarms if a not in found_alarms]

                # 🆕 NUOVO: Anche allarmi già trovati potrebbero avere timestamp vecchi
                potentially_stale_alarms = list(found_alarms.keys())

                if (missing_alarms or potentially_stale_alarms) and self.mongo_checker is not None:
                    alarms_to_check = list(set(missing_alarms + potentially_stale_alarms))
                    print(f"🔍 Checking MongoDB for {len(alarms_to_check)} alarms (missing or potentially stale)...")
                    
                    for alarm_key in alarms_to_check:
                        # Verifica MongoDB per questo allarme
                        mongo_result = self.check_mongodb_alarm(device_id, alarm_key)
                        
                        if mongo_result['active'] and mongo_result.get('timestamp_unix'):
                            # MongoDB ha un TRUE con timestamp
                            
                            # 🆕 Applica filtro temporale se attivo
                            should_skip_due_to_filter = False
                            if self.should_filter_data(sid, mongo_result['timestamp_unix']):
                                print(f"   ⏩ MongoDB TRUE per {alarm_key} fuori dal range temporale ({mongo_result['timestamp']}), scartato")
                                should_skip_due_to_filter = True
                            
                            if not should_skip_due_to_filter:
                                # MongoDB timestamp è valido
                                
                                # 🆕 CONFRONTA con timestamp EGM se già trovato
                                should_use_mongodb = False
                                
                                if alarm_key in found_alarms:
                                    # Allarme già trovato via EGM - confronta timestamp
                                    egm_data = found_alarms[alarm_key]
                                    egm_timestamp = egm_data if isinstance(egm_data, (int, float)) else None
                                    mongo_timestamp = mongo_result['timestamp_unix']
                                    
                                    if egm_timestamp and mongo_timestamp:
                                        # 🆕 VERIFICA: Entrambi devono essere in secondi!
                                        # Se uno è > 10 miliardi, è in millisecondi
                                        if egm_timestamp > 10000000000:
                                            egm_timestamp = egm_timestamp / 1000
                                        
                                        if mongo_timestamp > 10000000000:
                                            mongo_timestamp = mongo_timestamp / 1000
                                        
                                        time_diff = mongo_timestamp - egm_timestamp
                                        print(f"      Differenza: {time_diff} secondi ({int(time_diff/60)} minuti)")
                                        
                                        # 🆕 NUOVO: Tolleranza 5 minuti (300 secondi)
                                        TOLERANCE_SECONDS = 300
                                        
                                        if time_diff > TOLERANCE_SECONDS:
                                            # MongoDB SIGNIFICATIVAMENTE più recente (>5 min)
                                            print(f"   🔄 MongoDB molto più recente di EGM per {alarm_key} (+{int(time_diff)}s > {TOLERANCE_SECONDS}s), sostituisco!")
                                            should_use_mongodb = True
                                        elif time_diff > 0:
                                            # MongoDB più recente MA dentro tolleranza (0-5 min)
                                            print(f"   ⏸️ MongoDB più recente di EGM per {alarm_key} (+{int(time_diff)}s), ma dentro tolleranza ({TOLERANCE_SECONDS}s), mantengo EGM (più affidabile)")
                                            should_use_mongodb = False
                                        else:
                                            # EGM più recente o uguale
                                            print(f"   ✓ EGM più recente di MongoDB per {alarm_key} ({int(abs(time_diff))}s), mantengo EGM")
                                            should_use_mongodb = False
                                    else:
                                        # Se non abbiamo timestamp EGM confrontabile, usiamo comunque EGM (priorità)
                                        print(f"   ⚠️ Timestamp EGM non confrontabile per {alarm_key}, mantengo EGM")
                                else:
                                    # Allarme NON trovato via EGM - usa MongoDB
                                    should_use_mongodb = True
                                    print(f"   ✓ Allarme {alarm_key} non trovato via EGM, uso MongoDB")
                                
                                if should_use_mongodb:
                                    # Aggiorna/sostituisci con dato MongoDB (salva timestamp per confronti futuri)
                                    found_alarms[alarm_key] = mongo_result['timestamp_unix']
                                    
                                    # Emetti evento
                                    alarm_entry = {
                                        'alarm_type': alarm_key,
                                        'value': 'TRUE (MongoDB)',
                                        'timestamp': mongo_result['timestamp'] or 'N/A',
                                        'elapsed': str(elapsed).split('.')[0],
                                        'is_expected': True,
                                        'source': 'mongodb',
                                        'mongodb_metric': mongo_result['metric_found']
                                    }
                                    event_history.append(('alarm', alarm_entry))
                                    self.socketio.emit('alarm_found', alarm_entry, room=sid)
                                    
                                    print(f"✅ Alarm {alarm_key} validated via MongoDB (timestamp: {mongo_result['timestamp']})")

                # 🔥 STEP 6: AGGIORNAMENTI DI STATO
                missing_metrics = [m for m in expected_metrics if m not in metrics_with_data]
                missing_alarms = [a for a in expected_alarms if a not in found_alarms]
                
                self.socketio.emit('metrics_update', {
                    'found_count': len(metrics_with_data),
                    'total_expected': len(expected_metrics),
                    'missing_list': missing_metrics,
                    'last_check': datetime.now().strftime('%H:%M:%S')
                }, room=sid)
                
                self.socketio.emit('alarms_update', {
                    'found_count': len(found_alarms),
                    'total_expected': len(expected_alarms),
                    'missing_list': missing_alarms,
                    'other_count': len(other_alarms),
                    'last_check': datetime.now().strftime('%H:%M:%S')
                }, room=sid)
                
                # 🔥 STEP 7: COMPLETAMENTO se tutto ricevuto
                if len(metrics_with_data) == len(expected_metrics) and len(found_alarms) == len(expected_alarms):
                    self.socketio.emit('monitoring_complete', {
                        'success': True,
                        'metrics': {
                            'total_found': len(metrics_with_data),
                            'total_expected': len(expected_metrics)
                        },
                        'alarms': {
                            'total_found': len(found_alarms),
                            'total_expected': len(expected_alarms),
                            'other_alarms': other_alarms
                        },
                        'duration': str(elapsed).split('.')[0],
                        'history': event_history
                    }, room=sid)
                    break
                    
            except Exception as e:
                import traceback
                print(f"❌ Errore nel loop di monitoraggio: {e}")
                print(traceback.format_exc())
                self.socketio.emit('monitoring_error', {
                    'error': str(e)
                }, room=sid)
            
            # Adatta intervallo di polling
            if elapsed.total_seconds() > 120:
                check_interval = 10
            elif elapsed.total_seconds() > 300:
                check_interval = 15
                
            stop_event.wait(check_interval)
    
    def _get_expected_metrics(self, num_sensors):
        """Restituisce le metriche attese organizzate per categoria"""
        
        # Centralina Meteo
        weather_metrics = [
            'EIT_WINDVEL', 'EIT_WINDDIR1', 'EIT_HUMIDITY',
            'EIT_TEMPERATURE', 'EIT_PIROMETER'
        ]
        
        # Smart Junction Box
        junction_box_metrics = [
            'EIT_ACCEL_X', 'EIT_ACCEL_Y', 'EIT_ACCEL_Z',
            'EIT_INCLIN_X', 'EIT_INCLIN_Y'
        ]
        
        # Sensori di Tiro
        if num_sensors == 3:
            load_metrics = [
                'EIT_LOAD_04_A_L1', 'EIT_LOAD_08_A_L1', 'EIT_LOAD_12_A_L1'
            ]
        elif num_sensors == 6:
            # CORRETTO: Metriche di carico per 6 sensori
            load_metrics = [
                'EIT_LOAD_04_A_L1', 'EIT_LOAD_04_B_L1',
                'EIT_LOAD_08_A_L1', 'EIT_LOAD_08_B_L1',
                'EIT_LOAD_12_A_L1', 'EIT_LOAD_12_B_L1'
            ]
        else:  # 12 sensori
            load_metrics = []
            for load in ['04', '08', '12']:
                for side in ['A', 'B']:
                    for line in ['L1', 'L2']:
                        load_metrics.append(f'EIT_LOAD_{load}_{side}_{line}')
        
        return weather_metrics + junction_box_metrics + load_metrics
    
    def _get_expected_alarms(self, num_sensors):
        """Restituisce gli allarmi attesi in base al numero di sensori"""
        if num_sensors == 3:
            # Per 3 sensori, prepara entrambe le possibilità
            return {
                'primary': [
                    'EGM_OUT_SENS_23_VAR_32',  # F12A_L1
                    'EGM_OUT_SENS_23_VAR_36',  # F4A_L1
                    'EGM_OUT_SENS_23_VAR_40',  # F8A_L1
                ],
                'alternative': [
                    'EGM_OUT_SENS_23_VAR_34',  # F12B_L1
                    'EGM_OUT_SENS_23_VAR_38',  # F4B_L1
                    'EGM_OUT_SENS_23_VAR_42',  # F8B_L1
                ],
                'flexible': True
            }
        elif num_sensors == 6:
            return {
                'primary': [
                    'EGM_OUT_SENS_23_VAR_32',  # F12A_L1
                    'EGM_OUT_SENS_23_VAR_34',  # F12B_L1
                    'EGM_OUT_SENS_23_VAR_36',  # F4A_L1
                    'EGM_OUT_SENS_23_VAR_38',  # F4B_L1
                    'EGM_OUT_SENS_23_VAR_40',  # F8A_L1
                    'EGM_OUT_SENS_23_VAR_42',  # F8B_L1
                ],
                'acceptable': [
                    'EGM_OUT_SENS_23_VAR_33',  # F12A_L2
                    'EGM_OUT_SENS_23_VAR_37',  # F4A_L2
                    'EGM_OUT_SENS_23_VAR_41',  # F8A_L2
                ],
                'flexible': True
            }
        else:  # 12 sensori
            return {
                'primary': [
                    'EGM_OUT_SENS_23_VAR_32', 'EGM_OUT_SENS_23_VAR_33',
                    'EGM_OUT_SENS_23_VAR_34', 'EGM_OUT_SENS_23_VAR_35',
                    'EGM_OUT_SENS_23_VAR_36', 'EGM_OUT_SENS_23_VAR_37',
                    'EGM_OUT_SENS_23_VAR_38', 'EGM_OUT_SENS_23_VAR_39',
                    'EGM_OUT_SENS_23_VAR_40', 'EGM_OUT_SENS_23_VAR_41',
                    'EGM_OUT_SENS_23_VAR_42', 'EGM_OUT_SENS_23_VAR_43'
                ],
                'flexible': False
            }