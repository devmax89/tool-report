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
    
    def _unified_monitor_loop(self, sid, device_id, num_sensors, ui, timeout_minutes, stop_event):
        """Loop principale di monitoraggio unificato"""
        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        check_interval = 5
        
        # Dati per metriche
        found_metrics = {}
        expected_metrics = self._get_expected_metrics(num_sensors)
        
        # Dati per allarmi - ottieni configurazione iniziale
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
        
        # Storia eventi e allarmi ricevuti
        event_history = []
        all_received_alarms = {}  # Traccia tutti gli allarmi mai ricevuti
        
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
                
                # Check 1: Metriche (telemetria)
                success_tm, tm_data = digil_test_service.get_telemetry_data(
                    device_id, ui, start_timestamp, end_timestamp
                )
                
                if success_tm and 'tm' in tm_data and tm_data['tm']:
                    for tm_entry in tm_data['tm']:
                        if 'metrics' in tm_entry:
                            for metric in tm_entry['metrics']:
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                
                                # Se è una metrica attesa e non l'abbiamo già trovata
                                if metric_type in expected_metrics and metric_type not in found_metrics:
                                    timestamp = datetime.now().strftime('%H:%M:%S')
                                    found_metrics[metric_type] = metric_val
                                    
                                    metric_entry = {
                                        'metric_type': metric_type,
                                        'value': metric_val,
                                        'timestamp': timestamp,
                                        'elapsed': str(elapsed).split('.')[0]
                                    }
                                    event_history.append(('metric', metric_entry))
                                    self.socketio.emit('metric_found', metric_entry, room=sid)
                
                # Check 2: Allarmi (lastval)
                success_lv, lastval_data = digil_test_service.get_lastval_data(
                    device_id, ui, start_timestamp, end_timestamp
                )
                
                if success_lv and 'lastVal' in lastval_data:
                    # Prima raccogli TUTTI gli allarmi presenti
                    current_received_alarms = {}
                    for entry in lastval_data.get('lastVal', []):
                        if 'metrics' in entry:
                            for metric in entry['metrics']:
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                if 'EGM_OUT_SENS' in metric_type:
                                    current_received_alarms[metric_type] = metric_val
                                    all_received_alarms[metric_type] = metric_val
                    
                    # Adatta dinamicamente gli allarmi attesi SE configurazione flessibile
                    if is_flexible and isinstance(alarm_config, dict):
                        if num_sensors == 3:
                            # Conta quali allarmi sono presenti per decidere A o B
                            primary_count = sum(1 for alarm in alarm_config['primary'] if alarm in all_received_alarms)
                            alt_count = sum(1 for alarm in alarm_config.get('alternative', []) if alarm in all_received_alarms)
                            
                            if alt_count > primary_count and alt_count > 0:
                                if expected_alarms != alarm_config['alternative']:
                                    expected_alarms = alarm_config['alternative']
                                    self.socketio.emit('config_detected', {
                                        'message': 'Rilevata configurazione 3 sensori lato B'
                                    }, room=sid)
                            else:
                                expected_alarms = alarm_config['primary']
                        
                        elif num_sensors == 6:
                            # Parte con i primari e aggiunge quelli trovati che sono accettabili
                            new_expected = list(alarm_config['primary'])
                            for alarm in all_received_alarms:
                                if alarm in alarm_config.get('acceptable', []) and alarm not in new_expected:
                                    new_expected.append(alarm)
                                    if len(new_expected) > len(expected_alarms):
                                        self.socketio.emit('config_detected', {
                                            'message': f'Aggiunto allarme {alarm} agli attesi'
                                        }, room=sid)
                            expected_alarms = new_expected
                    
                    # ORA processa gli allarmi con la lista attesa aggiornata
                    for metric_type, metric_val in current_received_alarms.items():
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        
                        if metric_type in expected_alarms:
                            # Allarme atteso
                            if metric_type not in found_alarms:
                                found_alarms[metric_type] = metric_val
                                
                                alarm_entry = {
                                    'alarm_type': metric_type,
                                    'value': metric_val,
                                    'timestamp': timestamp,
                                    'elapsed': str(elapsed).split('.')[0],
                                    'is_expected': True
                                }
                                event_history.append(('alarm', alarm_entry))
                                self.socketio.emit('alarm_found', alarm_entry, room=sid)
                        else:
                            # Altro allarme non atteso
                            if metric_type not in other_alarms:
                                other_alarms[metric_type] = metric_val
                                
                                other_alarm_entry = {
                                    'alarm_type': metric_type,
                                    'value': metric_val,
                                    'timestamp': timestamp,
                                    'elapsed': str(elapsed).split('.')[0],
                                    'is_expected': False
                                }
                                event_history.append(('other_alarm', other_alarm_entry))
                                self.socketio.emit('other_alarm_found', other_alarm_entry, room=sid)
                
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