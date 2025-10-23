# monitoring_service.py
from flask_socketio import SocketIO, emit
from threading import Thread, Event
import time
from datetime import datetime, timedelta
from digil_test_service import digil_test_service

class AlarmMonitor:
    def __init__(self, socketio):
        self.socketio = socketio
        self.monitoring_threads = {}
        self.stop_events = {}
        
        # MAPPATURA COMPLETA: EGM allarmi -> tutti i flag EAM (Fault, Min, Max)
        self.alarm_to_flag_mapping = {
            # F4A_L1
            'EGM_OUT_SENS_23_VAR_36': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F4A_L1', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F4A_L1', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F4A_L1', 'type': 'max'}
                ],
                'friendly': 'F4A_L1'
            },
            # F4B_L1
            'EGM_OUT_SENS_23_VAR_38': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F4B_L1', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F4B_L1', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F4B_L1', 'type': 'max'}
                ],
                'friendly': 'F4B_L1'
            },
            # F8A_L1
            'EGM_OUT_SENS_23_VAR_40': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F8A_L1', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F8A_L1', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F8A_L1', 'type': 'max'}
                ],
                'friendly': 'F8A_L1'
            },
            # F8B_L1
            'EGM_OUT_SENS_23_VAR_42': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F8B_L1', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F8B_L1', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F8B_L1', 'type': 'max'}
                ],
                'friendly': 'F8B_L1'
            },
            # F12A_L1
            'EGM_OUT_SENS_23_VAR_32': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F12A_L1', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F12A_L1', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F12A_L1', 'type': 'max'}
                ],
                'friendly': 'F12A_L1'
            },
            # F12B_L1
            'EGM_OUT_SENS_23_VAR_34': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F12B_L1', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F12B_L1', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F12B_L1', 'type': 'max'}
                ],
                'friendly': 'F12B_L1'
            },
            # F4A_L2
            'EGM_OUT_SENS_23_VAR_37': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F4A_L2', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F4A_L2', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F4A_L2', 'type': 'max'}
                ],
                'friendly': 'F4A_L2'
            },
            # F4B_L2
            'EGM_OUT_SENS_23_VAR_39': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F4B_L2', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F4B_L2', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F4B_L2', 'type': 'max'}
                ],
                'friendly': 'F4B_L2'
            },
            # F8A_L2
            'EGM_OUT_SENS_23_VAR_41': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F8A_L2', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F8A_L2', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F8A_L2', 'type': 'max'}
                ],
                'friendly': 'F8A_L2'
            },
            # F8B_L2
            'EGM_OUT_SENS_23_VAR_43': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F8B_L2', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F8B_L2', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F8B_L2', 'type': 'max'}
                ],
                'friendly': 'F8B_L2'
            },
            # F12A_L2
            'EGM_OUT_SENS_23_VAR_33': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F12A_L2', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F12A_L2', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F12A_L2', 'type': 'max'}
                ],
                'friendly': 'F12A_L2'
            },
            # F12B_L2
            'EGM_OUT_SENS_23_VAR_35': {
                'flags': [
                    {'vendorName': 'ALG_Digil2_Alm_Fault_TC_F12B_L2', 'type': 'fault'},
                    {'vendorName': 'ALG_Digil2_Alm_Min_TC_F12B_L2', 'type': 'min'},
                    {'vendorName': 'ALG_Digil2_Alm_Max_TC_F12B_L2', 'type': 'max'}
                ],
                'friendly': 'F12B_L2'
            }
        }
    
    def check_alarm_validation(self, egm_alarm_key, alarm_value, thing_alarms):
        """
        Verifica se un allarme EGM ha i corrispondenti flag EAM a true
        """
        print(f"🔍 DEBUG check_alarm_validation:")
        print(f"   Allarme: {egm_alarm_key}")
        print(f"   Valore: {alarm_value}")
        print(f"   Flag disponibili: {len(thing_alarms)}")
        
        if egm_alarm_key not in self.alarm_to_flag_mapping:
            print(f"   ⚠️ Allarme {egm_alarm_key} NON trovato in mapping")
            return {
                'valid': None,
                'message': f'Allarme {egm_alarm_key} non mappato per validazione'
            }
        
        mapping = self.alarm_to_flag_mapping[egm_alarm_key]
        friendly_name = mapping['friendly']
        flags_info = mapping['flags']
        
        print(f"   ✓ Mapping trovato per: {friendly_name}")
        print(f"   Flag da cercare: {[f['vendorName'] for f in flags_info]}")
        
        # Cerca tutti i flag (Fault, Min, Max)
        found_flags = {}
        active_flags = []
        
        for flag_info in flags_info:
            vendor_name = flag_info['vendorName']
            flag_type = flag_info['type']
            
            if vendor_name in thing_alarms:
                flag_data = thing_alarms[vendor_name]
                flag_value = flag_data.get('value', False)
                flag_timestamp = flag_data.get('timestamp')
                
                print(f"   ✓ Flag trovato: {vendor_name} = {flag_value}")
                
                found_flags[flag_type] = {
                    'value': flag_value,
                    'timestamp': flag_timestamp,
                    'vendor_name': vendor_name
                }
                
                if flag_value == True:
                    active_flags.append(flag_type)
            else:
                print(f"   ✗ Flag NON trovato: {vendor_name}")
        
        # Determina se l'allarme è valido (almeno un flag a true)
        is_valid = len(active_flags) > 0
        
        print(f"   Risultato: valid={is_valid}, active_flags={active_flags}")
        
        # Formatta timestamp del primo flag trovato
        if found_flags:
            first_flag = list(found_flags.values())[0]
            ts = first_flag['timestamp']
            if ts and ts > 10000000000:
                ts = ts / 1000
            time_str = datetime.fromtimestamp(ts).strftime('%d/%m/%y - %H:%M:%S') if ts else 'N/A'
        else:
            time_str = 'N/A'
        
        # Costruisci messaggio dettagliato
        if is_valid:
            flags_text = ', '.join([f.upper() for f in active_flags])
            message = f"Flag attivi: {flags_text}"
        elif found_flags:
            flags_text = ', '.join([f"{k.upper()}=false" for k in found_flags.keys()])
            message = f"Flag trovati ma inattivi: {flags_text}"
        else:
            expected_flags = ', '.join([f['vendorName'] for f in flags_info])
            message = f"Nessun flag trovato. Attesi: {expected_flags}"
        
        result = {
            'valid': is_valid,
            'friendly_name': friendly_name,
            'active_flags': active_flags,
            'all_flags': found_flags,
            'flag_timestamp': time_str,
            'message': message
        }
        
        print(f"   📤 Ritorno: {result}")
        
        return result
    
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
            'time_window_minutes': time_window
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
    
    def _unified_monitor_loop(self, sid, device_id, num_sensors, ui, timeout_minutes, stop_event):
        """Loop principale di monitoraggio unificato con tripla verifica metriche e validazione allarmi"""
        print(f"🔍 Monitoraggio avviato con sid: {sid}")
        start_time = datetime.now()
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
        
        # Variabili per gestione cache Twin Manager
        thing_alarms = {}
        thing_alarms_last_update = None
        
        while not stop_event.is_set():
            current_time = datetime.now()
            elapsed = current_time - start_time
            
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
                # 🔥 STEP 1: CARICA FLAG ALLARMI DA TWIN MANAGER
                # Aggiorna i flag allarme ogni 60 secondi o all'inizio
                should_update_alarms = (
                    thing_alarms_last_update is None or 
                    (current_time - thing_alarms_last_update).total_seconds() >= 60
                )
                
                if should_update_alarms:
                    print(f"🔄 Aggiornamento flag allarmi da Twin Manager (elapsed: {elapsed.total_seconds():.0f}s)")
                    success_thing, thing_data = digil_test_service.get_thing_metrics(device_id)
                    
                    if success_thing:
                        thing_alarms = thing_data
                        thing_alarms_last_update = current_time
                        print(f"   ✅ {len(thing_alarms)} flag allarme caricati")
                    else:
                        print(f"   ⚠️ Twin Manager non disponibile: {thing_data}")
                        # Mantieni cache precedente se disponibile
                else:
                    if thing_alarms:
                        elapsed_cache = (current_time - thing_alarms_last_update).total_seconds()
                        print(f"   📦 Uso cache flag allarmi ({len(thing_alarms)} flag, età: {elapsed_cache:.0f}s)")
                
                # 🔥 STEP 2: CARICA API AGGREGATA per metriche mancanti
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
                
                # 🔥 STEP 3: CHECK METRICHE DALLA TELEMETRIA
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
                        packet_timestamp = entry.get('timestamp', 0) / 1000
                        
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
                                    
                                    # 🔥 VALIDA L'ALLARME con i flag da Twin Manager
                                    validation = self.check_alarm_validation(
                                        metric_type, 
                                        metric_val, 
                                        thing_alarms
                                    )
                                    
                                    if metric_type in expected_alarms:
                                        if metric_type not in found_alarms:
                                            found_alarms[metric_type] = metric_val
                                            alarm_entry = {
                                                'alarm_type': metric_type,
                                                'value': metric_val,
                                                'timestamp': formatted_timestamp,
                                                'elapsed': str(elapsed).split('.')[0],
                                                'is_expected': True,
                                                'validation': validation  # 🔥 CAMPO VALIDAZIONE
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
                                                'is_expected': False,
                                                'validation': validation  # 🔥 CAMPO VALIDAZIONE
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
                                
                                found_alarms[alarm_key] = measure_data['value']
                                
                                # 🔥 VALIDA anche gli allarmi dall'API aggregata
                                validation = self.check_alarm_validation(
                                    alarm_key,
                                    measure_data['value'],
                                    thing_alarms
                                )
                                
                                alarm_entry = {
                                    'alarm_type': alarm_key,
                                    'value': measure_data['value'],
                                    'timestamp': display_time,
                                    'elapsed': str(elapsed).split('.')[0],
                                    'is_expected': True,
                                    'source': 'aggregated',
                                    'validation': validation
                                }
                                event_history.append(('alarm', alarm_entry))
                                self.socketio.emit('alarm_found', alarm_entry, room=sid)
                
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