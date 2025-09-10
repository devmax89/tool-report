# digil_test_service.py
import requests
import json
import time
from datetime import datetime, timedelta
import urllib3

# Disabilita warning SSL per ambiente di test
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class DigilTestService:
    def __init__(self):
        self.base_url = "https://digil-back-end-onesait.servizi.prv"
        self.auth_url = "https://rh-sso.apps.clusterzac.opencs.servizi.prv/auth/realms/DigilV2/protocol/openid-connect/token"
        self.influx_base_url = "apidigil-ese-onesait-ese.apps.clusteriot.opencs.servizi.prv"
        self.access_token = None
        self.token_expires_at = None
        
    def get_auth_token(self):
        """Ottiene token di autenticazione"""
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': 'application',
                'client_secret': 'q3pH03oAvt9io1K1rJ9GHVVRcmAEf55x'
            }
            
            response = requests.post(self.auth_url, data=data, verify=False)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            return True, "Token ottenuto con successo"
            
        except Exception as e:
            return False, f"Errore autenticazione: {str(e)}"
        
    def check_device_configuration(self, device_id):
        """Verifica configurazione e stato del dispositivo usando endpoint /configuration"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }

            # Usa endpoint /configuration che ha il campo application
            url = f"{self.base_url}/api/v1/digils/{device_id}/configuration"
            response = requests.get(url, headers=headers, verify=False)

            if response.status_code == 200:
                data = response.json()

                # Da /configuration abbiamo application con maintenanceMode
                application = data.get('application', {})
                if application is None:
                    application = {}
                maintenance = application.get('maintenanceMode', 'UNKNOWN')

                print(f"   Maintenance Mode: {maintenance}")

                return True, {
                    'maintenance': maintenance,
                    'configuration': data  # Restituisce anche tutta la config
                }
            else:
                return False, f"Errore recupero configurazione: {response.status_code}"

        except Exception as e:
            return False, f"Errore verifica configurazione: {str(e)}"
    
    def check_device_status(self, device_id):
        """Verifica solo lo stato di connessione del dispositivo"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }

            url = f"{self.base_url}/api/v1/digils/{device_id}"
            response = requests.get(url, headers=headers, verify=False)

            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'UNKNOWN')

                return True, {
                    'status': status,
                    'connected': status == 'CONNECTED'
                }
            else:
                return False, f"Dispositivo non trovato o errore: {response.status_code}"

        except Exception as e:
            return False, f"Errore verifica stato: {str(e)}"
    
    def send_maintenance_command(self, device_id, mode="ON"):
        """Invia comando maintenance ON/OFF"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            body = {
                "name": "maintenance",
                "params": {
                    "status": {"values": [mode]}
                }
            }
            
            url = f"{self.base_url}/api/v1/digils/{device_id}/command"
            response = requests.post(url, headers=headers, json=body, verify=False)
            
            if response.status_code in [200, 202, 204]:
                return True, f"Maintenance {mode} inviato"
            else:
                return False, f"Errore invio comando: {response.status_code}"
                
        except Exception as e:
            return False, f"Errore: {str(e)}"
    
    def configure_sensor(self, device_id, sensor_type, config_name, value):
        """Configura un sensore specifico"""
        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            body = {
                "name": config_name,
                "value": value
            }

            url = f"{self.base_url}/api/v1/digils/{device_id}/configuration/{sensor_type}"
            response = requests.post(url, headers=headers, json=body, verify=False)

            # 204 No Content è una risposta di successo!
            if response.status_code in [200, 204]:
                return True, f"Configurato {sensor_type}: {config_name}={value}"
            else:
                return False, f"Errore configurazione {sensor_type}: {response.status_code}"

        except Exception as e:
            return False, f"Errore: {str(e)}"
    
    def get_metric_definitions(self, num_sensors):
        """Definisce le metriche attese per numero di sensori"""
        base_metrics = [
            'EIT_WINDVEL',  # min, avg, max
            'EIT_WINDDIR1',  # val
            'EIT_HUMIDITY',  # val
            'EIT_TEMPERATURE',  # val
            'EIT_PIROMETER',  # val
        ]
        
        if num_sensors == 3:
            load_metrics = [
                'EIT_LOAD_04_A_L1',  # min, avg, max
                'EIT_LOAD_08_A_L1',  # min, avg, max
                'EIT_LOAD_12_A_L1',  # min, avg, max
            ]
        elif num_sensors == 6:
            load_metrics = [
                'EIT_LOAD_04_A_L1', 'EIT_LOAD_04_B_L1',
                'EIT_LOAD_08_A_L1', 'EIT_LOAD_08_B_L1', 
                'EIT_LOAD_12_A_L1', 'EIT_LOAD_12_B_L1',
            ]
        else:  # 12 sensori
            load_metrics = [
                'EIT_LOAD_04_A_L1', 'EIT_LOAD_04_A_L2', 'EIT_LOAD_04_B_L1', 'EIT_LOAD_04_B_L2',
                'EIT_LOAD_08_A_L1', 'EIT_LOAD_08_A_L2', 'EIT_LOAD_08_B_L1', 'EIT_LOAD_08_B_L2',
                'EIT_LOAD_12_A_L1', 'EIT_LOAD_12_A_L2', 'EIT_LOAD_12_B_L1', 'EIT_LOAD_12_B_L2',
            ]
        
        return base_metrics + load_metrics
 
    def get_telemetry_data(self, device_id, ui, start_timestamp, end_timestamp):
        """Recupera i dati di telemetria dal sistema"""
        try:
            # URL SENZA https:// - usa direttamente l'host
            base_url = "apidigil-ese-onesait-ese.apps.clusteriot.opencs.servizi.prv"
            
            # Codifica il device ID per l'URL (i : diventano %3A)
            import urllib.parse
            device_id_encoded = urllib.parse.quote(device_id)
            
            # Costruisci l'URL completo
            url = f"http://{base_url}/api/v1/tm"  # Usa http, non https
            
            params = {
                'startDate': str(start_timestamp),
                'endDate': str(end_timestamp),
                'ui': ui,
                'deviceID': device_id  # Non codificato qui, requests lo farà
            }
            
            headers = {
                'Accept': 'application/json'
            }
            
            print(f"📊 Chiamata API telemetria: {url}")
            print(f"   Parametri: {params}")
            
            response = requests.get(url, params=params, headers=headers, verify=False, timeout=30)
            
            print(f"   Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'tm' in data:
                    print(f"   Trovati {len(data.get('tm', []))} record telemetria")
                return True, data
            else:
                error_msg = f"Errore API: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text[:200]}"
                return False, error_msg
                
        except Exception as e:
            return False, f"Errore recupero telemetria: {str(e)}"
    
    def run_downlink_test(self, device_id, progress_callback=None):
        """Esegue il test completo Downlink"""
        results = {
            'success': False,
            'steps': [],
            'start_time': datetime.now(),
            'device_id': device_id
        }

        def log_step(step_name, success, message):
            results['steps'].append({
                'step': step_name,
                'success': success,
                'message': message,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
            if progress_callback:
                progress_callback(step_name, success, message)

        # Step 1: Autenticazione
        success, msg = self.get_auth_token()
        log_step("Autenticazione", success, msg)
        if not success:
            results['error'] = msg
            return results

        # Step 2: Verifica connessione
        success, status_data = self.check_device_status(device_id)
        if success:
            connected = status_data.get('connected', False)
            log_step("Verifica connessione", connected, 
                    f"Status: {status_data.get('status')}")
            if not connected:
                results['error'] = "Dispositivo non connesso"
                return results
        else:
            log_step("Verifica connessione", False, status_data)
            results['error'] = status_data
            return results

        # Step 3: Maintenance ON
        success, msg = self.send_maintenance_command(device_id, "ON")
        log_step("Maintenance ON", success, msg)
        if not success:
            results['error'] = msg
            return results

        time.sleep(3)

        # Step 4: Configurazioni sensori
        sensor_configs = [
            ("accelerometer", "samplingTime", 60),
            ("inclinometer", "thresholdAlarm", 45),
            ("weatherStationAnenometer", "thresholdWarning", 25),
            ("pullSensors", "samplingTime", 120)
        ]

        all_configs_success = True
        for sensor, param, value in sensor_configs:
            success, msg = self.configure_sensor(device_id, sensor, param, value)
            log_step(f"Config {sensor}", success, msg)
            if not success:
                all_configs_success = False
            time.sleep(1)

        # Step 5: Maintenance OFF
        success, msg = self.send_maintenance_command(device_id, "OFF")
        log_step("Maintenance OFF", success, msg)

        time.sleep(5)

        # Step 6: Verifica finale usando /configuration per avere maintenanceMode
        max_retries = 3
        maintenance_off = False

        for retry in range(max_retries):
            success, config_data = self.check_device_configuration(device_id)
            if success:
                maintenance_status = config_data.get('maintenance', 'UNKNOWN')
                if maintenance_status == 'OFF':
                    maintenance_off = True
                    log_step("Verifica finale", True, f"Maintenance: OFF")
                    break
                elif retry < max_retries - 1:
                    log_step(f"Verifica {retry+1}/{max_retries}", False, 
                            f"Maintenance ancora {maintenance_status}, riprovo...")
                    time.sleep(3)
                else:
                    log_step("Verifica finale", False, f"Maintenance: {maintenance_status}")
            else:
                log_step("Verifica finale", False, f"Errore verifica: {config_data}")
                break
            
        results['success'] = all_configs_success and maintenance_off

        if results['success']:
            log_step("Test completato", True, "✅ Tutte le configurazioni applicate e maintenance OFF")

        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()

        return results
    
    def run_metrics_test(self, device_id, num_sensors, ui="Lazio", time_range_minutes=5, progress_callback=None):
        """Esegue il test Metriche in Range"""
        results = {
            'success': False,
            'device_id': device_id,
            'num_sensors': num_sensors,
            'start_time': datetime.now(),
            'missing_metrics': [],
            'found_metrics': [],
            'details': []
        }
        
        def log_step(message, success=True):
            results['details'].append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'message': message,
                'success': success
            })
            if progress_callback:
                progress_callback(message, success)
            print(f"{'✓' if success else '✗'} {message}")
        
        try:
            # Calcola timestamp
            end_time = datetime.now()
            start_time = end_time - timedelta(minutes=time_range_minutes)
            
            # Converti in Unix timestamp in SECONDI (non millisecondi!)
            start_timestamp = int(start_time.timestamp())  # Rimuovi * 1000
            end_timestamp = int(end_time.timestamp())      # Rimuovi * 1000
            
            log_step(f"Recupero metriche ultimi {time_range_minutes} minuti...")
            log_step(f"Periodo: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
            
            # Recupera dati telemetria
            success, tm_data = self.get_telemetry_data(device_id, ui, start_timestamp, end_timestamp)
            
            if not success:
                log_step(f"Errore recupero dati: {tm_data}", False)
                results['error'] = tm_data
                return results
            
            # Analizza metriche ricevute
            received_metrics = set()
            metric_values = {}
            
            if 'tm' in tm_data and tm_data['tm']:
                log_step(f"Trovate {len(tm_data['tm'])} letture")
                
                for tm_entry in tm_data['tm']:
                    if 'metrics' in tm_entry:
                        for metric in tm_entry['metrics']:
                            metric_type = metric.get('metricType', '')
                            metric_name = metric.get('metricName', '')
                            metric_val = metric.get('val', '')
                            
                            received_metrics.add(metric_type)
                            
                            if metric_type not in metric_values:
                                metric_values[metric_type] = []
                            metric_values[metric_type].append({
                                'name': metric_name,
                                'value': metric_val,
                                'timestamp': tm_entry.get('timestamp', '')
                            })
            else:
                log_step("Nessuna lettura trovata nel periodo", False)
            
            # Verifica metriche attese
            expected_metrics = self.get_metric_definitions(num_sensors)
            missing_metrics = []
            found_metrics = []
            
            for expected in expected_metrics:
                if expected in received_metrics:
                    found_metrics.append(expected)
                    values = metric_values.get(expected, [])
                    if values:
                        latest = values[-1]
                        log_step(f"✓ {expected}: {latest['value']}")
                else:
                    missing_metrics.append(expected)
                    log_step(f"✗ {expected}: NON RICEVUTA", False)
            
            # Risultati
            results['found_metrics'] = found_metrics
            results['missing_metrics'] = missing_metrics
            results['total_expected'] = len(expected_metrics)
            results['total_found'] = len(found_metrics)
            results['success'] = len(missing_metrics) == 0
            
            if results['success']:
                log_step(f"✅ Test superato! Tutte le {len(expected_metrics)} metriche ricevute")
            else:
                log_step(f"❌ Test fallito! Mancano {len(missing_metrics)} metriche su {len(expected_metrics)}", False)
            
            # Statistiche aggiuntive
            if tm_data.get('tm'):
                results['total_readings'] = len(tm_data['tm'])
                if tm_data['tm']:
                    results['first_reading'] = datetime.fromtimestamp(tm_data['tm'][0]['timestamp']/1000).strftime('%H:%M:%S')
                    results['last_reading'] = datetime.fromtimestamp(tm_data['tm'][-1]['timestamp']/1000).strftime('%H:%M:%S')
            
        except Exception as e:
            log_step(f"Errore durante il test: {str(e)}", False)
            results['error'] = str(e)
        
        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
        
        return results

# Istanza singleton
digil_test_service = DigilTestService()