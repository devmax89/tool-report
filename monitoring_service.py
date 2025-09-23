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
    
    def start_unified_monitoring(self, sid, device_id, num_sensors, ui, timeout_minutes=10):
        """Avvia il monitoraggio unificato per metriche e allarmi"""
        
        # Inizializza filtro PRIMA di avviare il thread
        if not hasattr(self, 'session_filters'):
            self.session_filters = {}
        
        # Se non esiste filtro per questa sessione, crea default
        if sid not in self.session_filters:
            self.session_filters[sid] = {
                'historical_mode': False,
                'time_window_minutes': 10
            }
            print(f"📝 Filtro inizializzato con default per sid {sid}")
        else:
            print(f"✅ Mantengo filtro esistente per sid {sid}: {self.session_filters[sid]}")
        
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
        """Loop principale di monitoraggio unificato con tripla verifica metriche"""
        print(f"🔍 Monitoraggio avviato con sid: {sid}")
        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        check_interval = 5
        last_aggregated_check = None
        
        # Aggiungi questa riga per avere accesso alla mappatura degli allarmi
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
        
        # Dati per metriche
        found_metrics = {}
        expected_metrics = self._get_expected_metrics(num_sensors)
        
        # Dati per allarmi
        found_alarms = {}
        other_alarms = {}
        alarm_config = self._get_expected_alarms(num_sensors)
        
        # Prepara lista iniziale di allarmi attesi
        if isinstance(alarm_config, dict):
            expected_alarms = alarm_config['primary']
            is_flexible = alarm_config.get('flexible', False)
        else:
            expected_alarms = alarm_config
            is_flexible = False
        
        # Storia eventi
        event_history = []
        all_received_alarms = {}
        
        while not stop_event.is_set():
            current_time = datetime.now()
            elapsed = current_time - start_time
            
            # Controlla timeout
            if elapsed > timeout:
                self.socketio.emit('monitoring_timeout', {
                    'message': f'Timeout raggiunto ({timeout_minutes} minuti)',
                    'metrics': {
                        'found': list(found_metrics.keys()),
                        'missing': [m for m in expected_metrics if m not in found_metrics]
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
                # Calcola range temporale
                end_timestamp = int(current_time.timestamp())
                start_timestamp = end_timestamp - 300  # Ultimi 5 minuti
                
                # Check 1: Metriche dalla telemetria (circa riga 150-170)
                success_tm, tm_data = digil_test_service.get_telemetry_data(
                    device_id, ui, start_timestamp, end_timestamp
                )

                if success_tm and 'tm' in tm_data and tm_data['tm']:
                    for tm_entry in tm_data['tm']:
                        # Converti timestamp del pacchetto
                        packet_timestamp = tm_entry.get('timestamp', 0) / 1000
                        
                        # IMPORTANTE: Controlla SUBITO se il dato è troppo vecchio
                        if self.should_filter_data(sid, packet_timestamp):
                            print(f"⏭️ Pacchetto telemetria filtrato (troppo vecchio)")
                            continue  # Salta TUTTO questo pacchetto
                        
                        packet_time = datetime.fromtimestamp(packet_timestamp).strftime('%H:%M:%S')
                        
                        if 'metrics' in tm_entry:
                            for metric in tm_entry['metrics']:
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                
                                if metric_type in expected_metrics and metric_type not in found_metrics:
                                    # Controlla PRIMA se è troppo vecchio
                                    if self.should_filter_data(sid, packet_timestamp):
                                        print(f"⏭️ Metrica {metric_type} filtrata (troppo vecchia)")
                                        continue  # SALTA completamente questa metrica
                                    
                                    # Aggiungi SOLO se NON è filtrata
                                    found_metrics[metric_type] = metric_val
                                    
                                    metric_entry = {
                                        'metric_type': metric_type,
                                        'value': metric_val,
                                        'timestamp': packet_time,
                                        'elapsed': str(elapsed).split('.')[0],
                                        'source': 'telemetry'
                                    }
                                    event_history.append(('metric', metric_entry))
                                    self.socketio.emit('metric_found', metric_entry, room=sid)

                # Check 2: Lastval per metriche mancanti E allarmi
                success_lv, lastval_data = digil_test_service.get_lastval_data(device_id, ui)

                if success_lv and 'lastVal' in lastval_data:
                    current_received_alarms = {}
                    
                    for entry in lastval_data.get('lastVal', []):
                        # Converti timestamp del pacchetto
                        packet_timestamp = entry.get('timestamp', 0) / 1000
                        
                        # IMPORTANTE: Controlla SUBITO se il dato è troppo vecchio
                        if self.should_filter_data(sid, packet_timestamp):
                            packet_time = datetime.fromtimestamp(packet_timestamp).strftime('%H:%M:%S')
                            print(f"⏭️ Entry lastval filtrato (troppo vecchio) - {packet_time}")
                            continue  # Salta TUTTO questo entry
                        
                        packet_time = datetime.fromtimestamp(packet_timestamp).strftime('%H:%M:%S')
                        
                        if 'metrics' in entry:
                            for metric in entry['metrics']:
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                
                                # Controlla se è una metrica mancante
                                if metric_type in expected_metrics and metric_type not in found_metrics:
                                    found_metrics[metric_type] = metric_val
                                    
                                    metric_entry = {
                                        'metric_type': metric_type,
                                        'value': metric_val,
                                        'timestamp': packet_time,
                                        'elapsed': str(elapsed).split('.')[0],
                                        'source': 'lastval'
                                    }
                                    event_history.append(('metric', metric_entry))
                                    self.socketio.emit('metric_found', metric_entry, room=sid)
                                
                                # Controlla se è un allarme
                                if 'EGM_OUT_SENS' in metric_type and metric_type in alarm_mapping:
                                    current_received_alarms[metric_type] = metric_val
                                    
                                    # Aggiungi ad all_received_alarms solo se non presente
                                    if metric_type not in all_received_alarms:
                                        all_received_alarms[metric_type] = metric_val
                                    
                                    # Processa allarme atteso
                                    if metric_type in expected_alarms:
                                        if metric_type not in found_alarms:
                                            # Controlla PRIMA se è troppo vecchio
                                            if self.should_filter_data(sid, packet_timestamp):
                                                print(f"⏭️ Allarme {metric_type} filtrato (troppo vecchio)")
                                                continue  # Non aggiungere a found_alarms
                                            
                                            # Aggiungi SOLO se non filtrato
                                            found_alarms[metric_type] = metric_val
                                            alarm_entry = {
                                                'alarm_type': metric_type,
                                                'value': metric_val,
                                                'timestamp': packet_time,
                                                'elapsed': str(elapsed).split('.')[0],
                                                'is_expected': True
                                            }
                                            event_history.append(('alarm', alarm_entry))
                                            self.socketio.emit('alarm_found', alarm_entry, room=sid)
                                    
                                    # Processa allarme non atteso (other)
                                    else:
                                        if metric_type not in other_alarms:
                                            other_alarms[metric_type] = metric_val
                                            other_alarm_entry = {
                                                'alarm_type': metric_type,
                                                'value': metric_val,
                                                'timestamp': packet_time,
                                                'elapsed': str(elapsed).split('.')[0],
                                                'is_expected': False
                                            }
                                            event_history.append(('other_alarm', other_alarm_entry))
                                            self.socketio.emit('other_alarm_found', other_alarm_entry, room=sid)
                    
                    # Adatta dinamicamente gli allarmi attesi SE configurazione flessibile
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

                # Check 3: API aggregata come fallback (solo ogni 30 secondi e dopo almeno 1 minuto)
                missing_metrics = [m for m in expected_metrics if m not in found_metrics]
                missing_alarms = [a for a in expected_alarms if a not in found_alarms]

                should_check_aggregated = (
                    (missing_metrics or missing_alarms) and
                    elapsed.total_seconds() > 60 and
                    (last_aggregated_check is None or 
                    (current_time - last_aggregated_check).total_seconds() > 30)
                )

                if should_check_aggregated:
                    last_aggregated_check = current_time
                    
                    success_agg, agg_data = digil_test_service.get_device_aggregated_data(device_id)
                    
                    if success_agg and 'measures' in agg_data:
                        measures = agg_data['measures']
                        
                        # Processa metriche mancanti
                        for measure_key, measure_data in measures.items():
                            if measure_key in digil_test_service.reverse_metrics_mapping:
                                eit_metric = digil_test_service.reverse_metrics_mapping[measure_key]
                                
                                if eit_metric in missing_metrics and measure_data and isinstance(measure_data, dict) and len(measure_data) > 0:
                                    # Estrai timestamp dalla misura
                                    measure_timestamp = measure_data.get('timestamp', 0) / 1000

                                    if self.should_filter_data(sid, measure_timestamp):
                                        print(f"⏭️ Metrica {eit_metric} da API aggregata filtrata (troppo vecchia)")
                                        continue

                                    measure_time = datetime.fromtimestamp(measure_timestamp).strftime('%H:%M:%S')
                                    
                                    if 'avg' in measure_data:
                                        value = f"min:{measure_data.get('min', 'N/A')}, avg:{measure_data.get('avg', 'N/A')}, max:{measure_data.get('max', 'N/A')}"
                                    elif 'value' in measure_data:
                                        value = str(measure_data.get('value', 'N/A'))
                                    else:
                                        continue
                                    
                                    found_metrics[eit_metric] = value
                                    
                                    metric_entry = {
                                        'metric_type': eit_metric,
                                        'value': value,
                                        'timestamp': measure_time,  # Usa il timestamp della misura
                                        'elapsed': str(elapsed).split('.')[0],
                                        'source': 'aggregated'
                                    }
                                    event_history.append(('metric', metric_entry))
                                    self.socketio.emit('metric_found', metric_entry, room=sid)
                        
                        # Processa allarmi mancanti
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
                                    # Estrai timestamp dalla misura
                                    measure_timestamp = measure_data.get('timestamp', 0) / 1000

                                    if self.should_filter_data(sid, measure_timestamp):
                                        print(f"⏭️ Allarme {alarm_key} da API aggregata filtrato (troppo vecchio)")
                                        continue

                                    measure_time = datetime.fromtimestamp(measure_timestamp).strftime('%H:%M:%S')
                                    
                                    found_alarms[alarm_key] = measure_data['value']
                                    
                                    alarm_entry = {
                                        'alarm_type': alarm_key,
                                        'value': measure_data['value'],
                                        'timestamp': measure_time,  # Usa il timestamp della misura
                                        'elapsed': str(elapsed).split('.')[0],
                                        'is_expected': True,
                                        'source': 'aggregated'
                                    }
                                    event_history.append(('alarm', alarm_entry))
                                    self.socketio.emit('alarm_found', alarm_entry, room=sid)

                                    # Debug: mostra stato dopo API aggregata
                                    print(f"📊 Stato dopo API aggregata:")
                                    print(f"   Metriche trovate (non filtrate): {len(found_metrics)}/{len(expected_metrics)}")
                                    print(f"   Allarmi trovati (non filtrati): {len(found_alarms)}/{len(expected_alarms)}")                                    
                
                # Invia aggiornamenti di stato
                missing_metrics = [m for m in expected_metrics if m not in found_metrics]
                missing_alarms = [a for a in expected_alarms if a not in found_alarms]
                
                # Aggiornamento metriche
                self.socketio.emit('metrics_update', {
                    'found_count': len(found_metrics),
                    'total_expected': len(expected_metrics),
                    'missing_list': missing_metrics,
                    'last_check': datetime.now().strftime('%H:%M:%S')
                }, room=sid)
                
                # Aggiornamento allarmi
                self.socketio.emit('alarms_update', {
                    'found_count': len(found_alarms),
                    'total_expected': len(expected_alarms),
                    'missing_list': missing_alarms,
                    'other_count': len(other_alarms),
                    'last_check': datetime.now().strftime('%H:%M:%S')
                }, room=sid)
                
                # Se tutto è stato ricevuto
                if len(found_metrics) == len(expected_metrics) and len(found_alarms) == len(expected_alarms):
                    self.socketio.emit('monitoring_complete', {
                        'success': True,
                        'metrics': {
                            'total_found': len(found_metrics),
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