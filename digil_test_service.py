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
        self.onesait_token = None
        self.onesait_token_expires_at = None
        
        # MAPPATURE COMPLETE DAL DIZIONARIO
        
        # 1. SENSORI DI TIRO - Metriche EIT
        self.load_metrics_mapping = {
            # Fase 4
            'EIT_LOAD_04_A_L1': 'SENS_Digil2_TC_F4A_L1',
            'EIT_LOAD_04_A_L2': 'SENS_Digil2_TC_F4A_L2',
            'EIT_LOAD_04_B_L1': 'SENS_Digil2_TC_F4B_L1',
            'EIT_LOAD_04_B_L2': 'SENS_Digil2_TC_F4B_L2',
            # Fase 8
            'EIT_LOAD_08_A_L1': 'SENS_Digil2_TC_F8A_L1',
            'EIT_LOAD_08_A_L2': 'SENS_Digil2_TC_F8A_L2',
            'EIT_LOAD_08_B_L1': 'SENS_Digil2_TC_F8B_L1',
            'EIT_LOAD_08_B_L2': 'SENS_Digil2_TC_F8B_L2',
            # Fase 12
            'EIT_LOAD_12_A_L1': 'SENS_Digil2_TC_F12A_L1',
            'EIT_LOAD_12_A_L2': 'SENS_Digil2_TC_F12A_L2',
            'EIT_LOAD_12_B_L1': 'SENS_Digil2_TC_F12B_L1',
            'EIT_LOAD_12_B_L2': 'SENS_Digil2_TC_F12B_L2'
        }
        
        # 2. SENSORI TIRO - Allarmi EGM
        self.alarm_mapping = {
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
            'EGM_OUT_SENS_23_VAR_30': 'Inc_X_ALARM',
            'EGM_OUT_SENS_23_VAR_31': 'Inc_Y_ALARM'
        }
        
        # 3. JUNCTION BOX - Accelerometri e Inclinometri
        self.junction_box_mapping = {
            # Accelerometri
            'EIT_ACCEL_X': 'SENS_Digil2_Acc_X',
            'EIT_ACCEL_Y': 'SENS_Digil2_Acc_Y',
            'EIT_ACCEL_Z': 'SENS_Digil2_Acc_Z',
            # Inclinometri
            'EIT_INCLIN_X': 'SENS_Digil2_Inc_X',
            'EIT_INCLIN_Y': 'SENS_Digil2_Inc_Y'
        }
        
        # 4. STAZIONE METEO
        self.weather_mapping = {
            'EIT_WINDVEL': 'SENS_Digil2_Wind_Speed',
            'EIT_WINDDIR1': 'SENS_Digil2_Wind_Dir',
            'EIT_HUMIDITY': 'SENS_Digil2_Humidity',
            'EIT_TEMPERATURE': 'SENS_Digil2_Temperature',
            'EIT_PIROMETER': 'SENS_Digil2_Pirometer'
        }
        
        # 5. SISTEMA BATTERIA E ALIMENTAZIONE
        self.battery_mapping = {
            'EIT_BATTERY_LEVEL': 'SENS_Digil2_BatteryLevel_Percent',
            'EIT_BATTERY_STATE': 'SENS_Digil2_BatteryState_Percent',
            'EIT_BATTERY_VOLT': 'SENS_Digil2_Battery_VOLT',
            'EIT_BATTERY_AMPERE': 'SENS_Digil2_BatteryOut_AMPERE',
            'EIT_BATTERY_TEMP': 'SENS_Digil2_Batt_Temp_1',
            'EIT_SOLAR_VOLTAGE': 'SENS_Digil2_SolarPanelVoltage',
            'EIT_SOLAR_CURRENT': 'SENS_Digil2_SolarPanelCurrent',
            'EIT_MPPT_STATUS': 'SENS_Digil2_MPPTStatus',
            'EIT_ENERGY_CONS': 'SENS_Digil2_ConsumptionEnergy',
            'EIT_ENERGY_TOTAL': 'SENS_Digil2_TotalConsumptionEnergy'
        }
        
        # 6. COMUNICAZIONE
        self.communication_mapping = {
            'EGM_OUT_SENS_23_VAR_7': 'SENS_Digil2_Channel',
            'EIT_LTE_SIGNAL': 'SENS_Digil2_LtePowerSignal',
            'EIT_NBIOT_SIGNAL': 'SENS_Digil2_NBIoTPowerSignal'
        }
        
        # 7. TEMPERATURE CABINET
        self.temperature_mapping = {
            'EIT_TEMP_CABIN': 'SENS_Digil2_TmpInCabin',
            'EIT_TEMP_DEVICE': 'SENS_Digil2_TmpDevice'
        }
        
        # MAPPATURA UNIFICATA PER TUTTE LE METRICHE
        self.all_metrics_mapping = {
            **self.load_metrics_mapping,
            **self.junction_box_mapping,
            **self.weather_mapping,
            **self.battery_mapping,
            **self.communication_mapping,
            **self.temperature_mapping
        }
        
        # MAPPATURA INVERSA (SENS_Digil2 -> EIT)
        self.reverse_metrics_mapping = {v: k for k, v in self.all_metrics_mapping.items()}
        
        # Descrizioni user-friendly per categorie
        self.metric_categories = {
            'weather': {
                'name': '🌤️ Stazione Meteo',
                'metrics': list(self.weather_mapping.keys())
            },
            'junction_box': {
                'name': '📦 Smart Junction Box',
                'metrics': list(self.junction_box_mapping.keys())
            },
            'load': {
                'name': '⚡ Sensori di Tiro',
                'metrics': list(self.load_metrics_mapping.keys())
            },
            'battery': {
                'name': '🔋 Sistema Batteria',
                'metrics': list(self.battery_mapping.keys())
            },
            'communication': {
                'name': '📡 Comunicazione',
                'metrics': list(self.communication_mapping.keys())
            },
            'temperature': {
                'name': '🌡️ Temperature',
                'metrics': list(self.temperature_mapping.keys())
            }
        }
        
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
        """Definisce le metriche attese per numero di sensori, organizzate per categoria"""

        # Centralina Meteo (Weather Station)
        weather_metrics = [
            'EIT_WINDVEL',      # min, avg, max
            'EIT_WINDDIR1',     # value
            'EIT_HUMIDITY',     # value
            'EIT_TEMPERATURE',  # value
            'EIT_PIROMETER',    # value
        ]

        # Smart Junction Box (Accelerometri e Inclinometri)
        junction_box_metrics = [
            'EIT_ACCEL_X',      # min, avg, max
            'EIT_ACCEL_Y',      # min, avg, max
            'EIT_ACCEL_Z',      # min, avg, max
            'EIT_INCLIN_X',     # min, avg, max
            'EIT_INCLIN_Y',     # min, avg, max
        ]

        # Sensori di Tiro (basati sul numero di sensori)
        if num_sensors == 3:
            # Per 3 sensori, prepara entrambe le possibilità
            load_metrics_A = [
                'EIT_LOAD_04_A_L1',  # min, avg, max
                'EIT_LOAD_08_A_L1',  # min, avg, max
                'EIT_LOAD_12_A_L1',  # min, avg, max
            ]
            load_metrics_B = [
                'EIT_LOAD_04_B_L1',  # min, avg, max
                'EIT_LOAD_08_B_L1',  # min, avg, max
                'EIT_LOAD_12_B_L1',  # min, avg, max
            ]
            # Usa lato A come default, ma restituisci anche le alternative
            load_metrics = load_metrics_A

        elif num_sensors == 6:
            load_metrics = [
                'EIT_LOAD_04_A_L1', 'EIT_LOAD_04_B_L1',
                'EIT_LOAD_08_A_L1', 'EIT_LOAD_08_B_L1',
                'EIT_LOAD_12_A_L1', 'EIT_LOAD_12_B_L1'
            ]
        else:  # 12 sensori
            load_metrics = [
                'EIT_LOAD_04_A_L1', 'EIT_LOAD_04_A_L2', 'EIT_LOAD_04_B_L1', 'EIT_LOAD_04_B_L2',
                'EIT_LOAD_08_A_L1', 'EIT_LOAD_08_A_L2', 'EIT_LOAD_08_B_L1', 'EIT_LOAD_08_B_L2',
                'EIT_LOAD_12_A_L1', 'EIT_LOAD_12_A_L2', 'EIT_LOAD_12_B_L1', 'EIT_LOAD_12_B_L2',
            ]

        # Combina tutte le metriche
        all_metrics = weather_metrics + junction_box_metrics + load_metrics

        # Restituisci con informazioni aggiuntive per 3 sensori
        result = {
            'all': all_metrics,
            'weather': weather_metrics,
            'junction_box': junction_box_metrics,
            'load': load_metrics
        }

        # Per 3 sensori, aggiungi le alternative
        if num_sensors == 3:
            result['load_alternative'] = load_metrics_B
            result['flexible'] = True

        return result
 
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
    

    def get_device_aggregated_data(self, device_id):
        """Ottiene dati aggregati del dispositivo dall'API /digils/:deviceId"""
        try:
            # Ottieni prima il token di autenticazione
            success, msg = self.get_auth_token()
            if not success:
                print(f"   ✗ Errore ottenimento token: {msg}")
                return False, f"Errore ottenimento token: {msg}"

            print(f"   ✓ Token ottenuto")

            # Trasforma il device ID
            transformed_id = self.transform_device_id_fallback(device_id)

            # Prepara la chiamata
            url = f"{self.base_url}/api/v1/digils/{transformed_id}"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Accept': 'application/json'
            }

            print(f"📊 Chiamata API aggregata:")
            print(f"   URL: {url}")
            print(f"   Device ID: {device_id} → {transformed_id}")

            # Fai la chiamata
            response = requests.get(url, headers=headers, verify=False, timeout=30)

            print(f"   Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"   ✓ Risposta OK, dati ricevuti")
                if 'measures' in data:
                    print(f"   ✓ Trovate {len(data['measures'])} measures")
                return True, data
            elif response.status_code == 401:
                print(f"   ✗ Errore 401: Token non valido")
                return False, "Token non valido"
            elif response.status_code == 404:
                print(f"   ✗ Errore 404: Device {transformed_id} non trovato")
                return False, "Device non trovato"
            else:
                print(f"   ✗ Errore HTTP {response.status_code}")
                if response.text:
                    print(f"   Response body: {response.text[:500]}")
                return False, f"HTTP {response.status_code}"

        except requests.exceptions.RequestException as e:
            print(f"   ✗ Errore di rete: {e}")
            return False, f"Errore di rete: {e}"
        except Exception as e:
            print(f"   ✗ Errore generico: {e}")
            import traceback
            print(traceback.format_exc())
            return False, str(e)

    def transform_device_id_fallback(self, device_id):
        # Dividi per ":"
        parts = device_id.split(":")
        
        if len(parts) >= 5:
            # Prendi i primi 5 numeri
            first_five = ''.join(parts[:5])
            
            # Estrai le ultime 4 cifre dal nome del device
            device_name = parts[-1] if len(parts) > 5 else ""
            last_four = ''.join(filter(str.isdigit, device_name))[-4:]
            
            transformed = f"{first_five}_{last_four}"
            return transformed
        else:
            # Fallback al metodo vecchio
            no_colons = device_id.replace(":", "")
            numbers = ''.join(filter(str.isdigit, no_colons))
            if len(numbers) >= 4:
                main_part = numbers[:-4]
                last_four = numbers[-4:]
                return f"{main_part}_{last_four}"
            return numbers
    
    def run_downlink_test(self, device_id, progress_callback=None):
        """Esegue il test completo Downlink - versione ottimizzata"""
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
    
        time.sleep(2)  # Ridotto da 3 a 2 secondi
    
        # Step 4: Configurazioni sensori IN PARALLELO (più veloce)
        import concurrent.futures
        sensor_configs = [
            ("accelerometer", "samplingTime", 60),
            ("inclinometer", "thresholdAlarm", 45),
            ("weatherStationAnenometer", "thresholdWarning", 25),
            ("pullSensors", "samplingTime", 120)
        ]
    
        all_configs_success = True
        
        # Esegui le configurazioni in parallelo per velocizzare
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            for sensor, param, value in sensor_configs:
                future = executor.submit(self.configure_sensor, device_id, sensor, param, value)
                futures[future] = (sensor, param, value)
            
            # Raccogli i risultati
            for future in concurrent.futures.as_completed(futures):
                sensor, param, value = futures[future]
                try:
                    success, msg = future.result(timeout=5)
                    log_step(f"Config {sensor}", success, msg)
                    if not success:
                        all_configs_success = False
                except Exception as e:
                    log_step(f"Config {sensor}", False, f"Errore: {str(e)}")
                    all_configs_success = False
        
        time.sleep(1)  # Breve pausa dopo tutte le config
    
        # Step 5: Maintenance OFF
        success, msg = self.send_maintenance_command(device_id, "OFF")
        log_step("Maintenance OFF", success, msg)
    
        time.sleep(3)  # Ridotto da 5 a 3 secondi
    
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
                    time.sleep(2)  # Ridotto da 3 a 2 secondi
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
        """Esegue il test Metriche in Range con tripla verifica (tm + lastval + aggregata)"""
        results = {
            'success': False,
            'device_id': device_id,
            'num_sensors': num_sensors,
            'start_time': datetime.now(),
            'missing_metrics': [],
            'found_metrics': [],
            'metrics_by_category': {
                'weather': {'found': [], 'missing': []},
                'junction_box': {'found': [], 'missing': []},
                'load': {'found': [], 'missing': []}
            },
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
            
            start_timestamp = int(start_time.timestamp())
            end_timestamp = int(end_time.timestamp())
            
            log_step(f"Recupero metriche ultimi {time_range_minutes} minuti...")
            log_step(f"Periodo: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
            
            # Prima chiamata: telemetria
            success_tm, tm_data = self.get_telemetry_data(device_id, ui, start_timestamp, end_timestamp)
            
            # Analizza metriche ricevute dalla telemetria
            received_metrics = set()
            metric_values = {}

            # Aggiungi controllo tipo per tm_data
            if success_tm and isinstance(tm_data, dict) and 'tm' in tm_data and tm_data['tm']:
                log_step(f"Trovate {len(tm_data['tm'])} letture dalla telemetria")
                
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
                                'timestamp': tm_entry.get('timestamp', ''),
                                'source': 'telemetry'
                            })
            elif not success_tm:
                # Log dell'errore se la telemetria fallisce
                log_step(f"Errore telemetria: {tm_data}", False)

            # Ottieni definizioni metriche
            metrics_def = self.get_metric_definitions(num_sensors)
            expected_metrics = metrics_def['all'] if isinstance(metrics_def, dict) else metrics_def

            # Verifica quali metriche mancano dopo la prima chiamata
            missing_after_tm = [m for m in expected_metrics if m not in received_metrics]

            if missing_after_tm:
                log_step(f"Mancano {len(missing_after_tm)} metriche dalla telemetria, controllo lastval...")
                
                # Seconda chiamata: lastval per le metriche mancanti
                success_lv, lastval_data = self.get_lastval_data(device_id, ui)
                
                # Aggiungi controllo tipo anche per lastval_data
                if success_lv and isinstance(lastval_data, dict) and 'lastVal' in lastval_data:
                    log_step(f"Trovati {len(lastval_data.get('lastVal', []))} record da lastval")
                    
                    for entry in lastval_data.get('lastVal', []):
                        if 'metrics' in entry:
                            for metric in entry['metrics']:
                                metric_type = metric.get('metricType', '')
                                metric_val = metric.get('val', '')
                                
                                # Aggiungi solo metriche che erano mancanti e sono attese
                                if metric_type in missing_after_tm:
                                    received_metrics.add(metric_type)
                                    
                                    if metric_type not in metric_values:
                                        metric_values[metric_type] = []
                                    metric_values[metric_type].append({
                                        'name': metric_type,
                                        'value': metric_val,
                                        'timestamp': entry.get('timestamp', ''),
                                        'source': 'lastval'
                                    })
                                    log_step(f"✓ Trovata {metric_type} da lastval: {metric_val}")
                elif not success_lv:
                    log_step(f"Errore lastval: {lastval_data}", False)
            else:
                log_step("Tutte le metriche trovate dalla telemetria!")
            
            # TERZA CHIAMATA: API aggregata per metriche ancora mancanti
            final_missing = [m for m in expected_metrics if m not in received_metrics]

            # Inizializza variabili per evitare errori
            success_agg = False
            agg_data = {}

            if final_missing:
                log_step(f"⚠️ Ancora {len(final_missing)} metriche mancanti dopo tm+lastval")
                log_step(f"📊 Tentativo con API aggregata di fallback...")
                
                success_agg, agg_data = self.get_device_aggregated_data(device_id)
                
                if success_agg and 'measures' in agg_data:
                    measures = agg_data['measures']
                    log_step(f"   Trovate {len(measures)} measures nell'API aggregata")
                    
                    # Debug: mostra alcune measures
                    measure_samples = list(measures.keys())[:5]
                    log_step(f"   Esempi di measures: {measure_samples}")
                    
                    # Conta quante measures sono vuote
                    empty_measures = [k for k, v in measures.items() if not v or v == {}]
                    if empty_measures:
                        log_step(f"   ⚠️ {len(empty_measures)} measures sono vuote")
                    
                    # Analisi dati aggregati per metriche mancanti
                    metrics_found_from_aggregated = 0
                    
                    # Usa il reverse mapping per convertire da SENS_Digil2 a EIT
                    for measure_key, measure_data in measures.items():
                        # Controlla se questa misura corrisponde a una metrica mancante
                        if measure_key in self.reverse_metrics_mapping:
                            eit_metric = self.reverse_metrics_mapping[measure_key]
                            
                            if eit_metric in final_missing:
                                # Debug per vedere cosa c'è in measure_data
                                if not measure_data or measure_data == {}:
                                    log_step(f"   ⚠️ {measure_key} → {eit_metric}: vuoto, skip")
                                    continue
                                
                                # Verifica che ci siano dati validi
                                if isinstance(measure_data, dict) and len(measure_data) > 0:
                                    received_metrics.add(eit_metric)
                                    metrics_found_from_aggregated += 1
                                    
                                    # Gestisci diversi formati di dati
                                    if 'avg' in measure_data:
                                        # Dati con min/avg/max (sensori di tiro, accelerometri, etc.)
                                        value_str = f"min:{measure_data.get('min', 'N/A')}, avg:{measure_data.get('avg', 'N/A')}, max:{measure_data.get('max', 'N/A')}"
                                    elif 'value' in measure_data:
                                        # Dati con valore singolo (temperatura, batteria, etc.)
                                        value_str = str(measure_data.get('value', 'N/A'))
                                    else:
                                        log_step(f"   ⚠️ {measure_key}: formato dati non riconosciuto")
                                        continue  # Skip se non ci sono dati validi
                                    
                                    if eit_metric not in metric_values:
                                        metric_values[eit_metric] = []
                                    
                                    metric_values[eit_metric].append({
                                        'name': eit_metric,
                                        'value': value_str,
                                        'timestamp': measure_data.get('timestamp', 'N/A'),
                                        'source': 'aggregated-fallback'
                                    })
                                    
                                    log_step(f"   ✓ Recuperata {eit_metric} ({measure_key}): {value_str} [da API aggregata]")
                    
                    if metrics_found_from_aggregated == 0:
                        log_step(f"   ⚠️ Nessuna metrica mancante recuperata dall'API aggregata")
                    else:
                        log_step(f"   ✓ Recuperate {metrics_found_from_aggregated} metriche dall'API aggregata")
                else:
                    if not success_agg:
                        log_step(f"   ✗ API aggregata fallita: {agg_data}", False)
                    else:
                        log_step(f"   ✗ API aggregata senza measures", False)
            else:
                log_step("✅ Tutte le metriche trovate dalla telemetria!")
            
            # Mostra risultati per categoria
            if isinstance(metrics_def, dict):
                # Stazione Meteo
                log_step("=== 🌤️ Stazione Meteo ===")
                for metric in metrics_def['weather']:
                    sens_name = self.weather_mapping.get(metric, metric)
                    if metric in received_metrics:
                        results['metrics_by_category']['weather']['found'].append(metric)
                        if metric in metric_values and metric_values[metric]:
                            latest = metric_values[metric][-1]
                            source_tag = f" [{latest.get('source', '')}]" if latest.get('source') else ""
                            log_step(f"✓ {metric} ({sens_name}): {latest['value']}{source_tag}")
                    else:
                        results['metrics_by_category']['weather']['missing'].append(metric)
                        log_step(f"✗ {metric} ({sens_name}): NON RICEVUTA", False)

                # Smart Junction Box
                log_step("=== 📦 Smart Junction Box ===")
                for metric in metrics_def['junction_box']:
                    sens_name = self.junction_box_mapping.get(metric, metric)
                    if metric in received_metrics:
                        results['metrics_by_category']['junction_box']['found'].append(metric)
                        if metric in metric_values and metric_values[metric]:
                            latest = metric_values[metric][-1]
                            source_tag = f" [{latest.get('source', '')}]" if latest.get('source') else ""
                            log_step(f"✓ {metric} ({sens_name}): {latest['value']}{source_tag}")
                    else:
                        results['metrics_by_category']['junction_box']['missing'].append(metric)
                        log_step(f"✗ {metric} ({sens_name}): NON RICEVUTA", False)

                # Sensori di Tiro
                log_step("=== ⚡ Sensori di Tiro ===")
                for metric in metrics_def['load']:
                    sens_name = self.load_metrics_mapping.get(metric, metric)
                    if metric in received_metrics:
                        results['metrics_by_category']['load']['found'].append(metric)
                        if metric in metric_values and metric_values[metric]:
                            latest = metric_values[metric][-1]
                            source_tag = f" [{latest.get('source', '')}]" if latest.get('source') else ""
                            log_step(f"✓ {metric} ({sens_name}): {latest['value']}{source_tag}")
                    else:
                        results['metrics_by_category']['load']['missing'].append(metric)
                        log_step(f"✗ {metric} ({sens_name}): NON RICEVUTA", False)
            
            # Calcola totali finali
            missing_metrics = []
            found_metrics = []
            
            for expected in expected_metrics:
                if expected in received_metrics:
                    found_metrics.append(expected)
                else:
                    missing_metrics.append(expected)
            
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
    
    def get_alarm_definitions(self, num_sensors):
        """Definisce gli allarmi attesi per numero di sensori con flessibilità"""

        # Mappa completa degli allarmi possibili
        alarm_mapping = {
            # Fase 12
            'EGM_OUT_SENS_23_VAR_32': 'F12A_L1',
            'EGM_OUT_SENS_23_VAR_33': 'F12A_L2',
            'EGM_OUT_SENS_23_VAR_34': 'F12B_L1',
            'EGM_OUT_SENS_23_VAR_35': 'F12B_L2',
            # Fase 4
            'EGM_OUT_SENS_23_VAR_36': 'F4A_L1',
            'EGM_OUT_SENS_23_VAR_37': 'F4A_L2',
            'EGM_OUT_SENS_23_VAR_38': 'F4B_L1',
            'EGM_OUT_SENS_23_VAR_39': 'F4B_L2',
            # Fase 8
            'EGM_OUT_SENS_23_VAR_40': 'F8A_L1',
            'EGM_OUT_SENS_23_VAR_41': 'F8A_L2',
            'EGM_OUT_SENS_23_VAR_42': 'F8B_L1',
            'EGM_OUT_SENS_23_VAR_43': 'F8B_L2',
            # Inclinometri
            'EGM_OUT_SENS_23_VAR_30': 'Inc_X',
            'EGM_OUT_SENS_23_VAR_31': 'Inc_Y'
        }

        # Definizione teorica per configurazione
        if num_sensors == 3:
            # Solo lato A o B, linea 1
            expected_base = [
                'EGM_OUT_SENS_23_VAR_32',  # F12A_L1
                'EGM_OUT_SENS_23_VAR_36',  # F4A_L1
                'EGM_OUT_SENS_23_VAR_40',  # F8A_L1
            ]
            # Potrebbe anche essere lato B
            alternative = [
                'EGM_OUT_SENS_23_VAR_34',  # F12B_L1
                'EGM_OUT_SENS_23_VAR_38',  # F4B_L1
                'EGM_OUT_SENS_23_VAR_42',  # F8B_L1
            ]
            
        elif num_sensors == 6:
            # Per 6 sensori: 6 allarmi base (3 lato A + 3 lato B)
            expected_base = [
                'EGM_OUT_SENS_23_VAR_32',  # F12A_L1
                'EGM_OUT_SENS_23_VAR_34',  # F12B_L1
                'EGM_OUT_SENS_23_VAR_36',  # F4A_L1
                'EGM_OUT_SENS_23_VAR_38',  # F4B_L1
                'EGM_OUT_SENS_23_VAR_40',  # F8A_L1
                'EGM_OUT_SENS_23_VAR_42',  # F8B_L1
            ]
            # Possibili aggiunte L2
            possible_additions = [
                'EGM_OUT_SENS_23_VAR_33',  # F12A_L2
                'EGM_OUT_SENS_23_VAR_37',  # F4A_L2
                'EGM_OUT_SENS_23_VAR_41',  # F8A_L2
                'EGM_OUT_SENS_23_VAR_35',  # F12B_L2
                'EGM_OUT_SENS_23_VAR_39',  # F4B_L2
                'EGM_OUT_SENS_23_VAR_43',  # F8B_L2
            ]
            
        else:  # 12 sensori
            # Tutti gli allarmi possibili (esclusi inclinometri)
            expected_base = list(alarm_mapping.keys())[:12]
        
        result = {
            'expected': expected_base,
            'mapping': alarm_mapping,
            'flexible': num_sensors in [3, 6]
        }
        
        if num_sensors == 3:
            result['alternative'] = alternative
        elif num_sensors == 6:
            result['possible_additions'] = possible_additions
        
        return result


    def get_lastval_data(self, device_id, ui):
        """Recupera gli ultimi valori e allarmi dal sistema (sempre chiamata secca)"""
        try:
            base_url = "apidigil-ese-onesait-ese.apps.clusteriot.opencs.servizi.prv"
            url = f"http://{base_url}/api/v1/lastval"

            params = {
                'ui': ui,
                'deviceID': device_id
            }

            headers = {
                'Accept': 'application/json'
            }

            print(f"📊 Chiamata API lastval (secca): {url}")
            print(f"   Parametri: {params}")

            response = requests.get(url, params=params, headers=headers, verify=False, timeout=30)

            print(f"   Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                if 'lastVal' in data:
                    print(f"   Trovati {len(data.get('lastVal', []))} record lastval")
                return True, data
            else:
                error_msg = f"Errore API: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text[:200]}"
                return False, error_msg

        except Exception as e:
            return False, f"Errore recupero lastval: {str(e)}"

    def run_alarm_test(self, device_id, num_sensors, ui="Lazio", progress_callback=None):
        """Esegue il test Allarme Metriche con logica flessibile e fallback API aggregata"""
        results = {
            'success': False,
            'device_id': device_id,
            'num_sensors': num_sensors,
            'start_time': datetime.now(),
            'found_alarms': [],
            'expected_alarms': [],
            'missing_alarms': [],
            'other_alarms': {},
            'alarm_values': {},
            'details': [],
            'total_found': 0,
            'total_expected': 0
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
            log_step(f"Recupero ultimi allarmi disponibili...")
            log_step(f"UI: {ui}, Sensori: {num_sensors}")

            # Recupera dati lastval (sempre chiamata secca)
            success, lastval_data = self.get_lastval_data(device_id, ui)

            if not success:
                log_step(f"Errore recupero dati: {lastval_data}", False)
                results['error'] = lastval_data
                results['total_expected'] = 0
                results['total_found'] = 0
                return results

            if 'lastVal' in lastval_data:
                log_step(f"Ricevuti {len(lastval_data.get('lastVal', []))} record lastval")

            # Usa l'alarm_mapping dalla classe
            alarm_mapping = self.alarm_mapping

            # Raccogli tutti gli allarmi ricevuti da lastval
            received_alarms = {}

            if 'lastVal' in lastval_data and lastval_data['lastVal']:
                for entry in lastval_data['lastVal']:
                    if 'metrics' in entry:
                        for metric in entry['metrics']:
                            metric_type = metric.get('metricType', '')
                            metric_val = metric.get('val', '')

                            if 'EGM_OUT_SENS' in metric_type and metric_type in alarm_mapping:
                                received_alarms[metric_type] = metric_val

            # Definisci allarmi attesi base
            required_alarms = []

            if num_sensors == 3:
                required_alarms_A = [
                    'EGM_OUT_SENS_23_VAR_32',  # F12A_L1
                    'EGM_OUT_SENS_23_VAR_36',  # F4A_L1
                    'EGM_OUT_SENS_23_VAR_40',  # F8A_L1
                ]
                required_alarms_B = [
                    'EGM_OUT_SENS_23_VAR_34',  # F12B_L1
                    'EGM_OUT_SENS_23_VAR_38',  # F4B_L1
                    'EGM_OUT_SENS_23_VAR_42',  # F8B_L1
                ]

                count_A = sum(1 for alarm in required_alarms_A if alarm in received_alarms)
                count_B = sum(1 for alarm in required_alarms_B if alarm in received_alarms)

                if count_B > count_A:
                    log_step("ℹ️ Rilevata configurazione 3 sensori lato B")
                    required_alarms = required_alarms_B
                else:
                    log_step("ℹ️ Configurazione 3 sensori lato A (default)")
                    required_alarms = required_alarms_A

            elif num_sensors == 6:
                required_alarms = [
                    'EGM_OUT_SENS_23_VAR_32',  # F12A_L1
                    'EGM_OUT_SENS_23_VAR_34',  # F12B_L1
                    'EGM_OUT_SENS_23_VAR_36',  # F4A_L1
                    'EGM_OUT_SENS_23_VAR_38',  # F4B_L1
                    'EGM_OUT_SENS_23_VAR_40',  # F8A_L1
                    'EGM_OUT_SENS_23_VAR_42',  # F8B_L1
                ]
                acceptable_additions = [
                    'EGM_OUT_SENS_23_VAR_33',  # F12A_L2
                    'EGM_OUT_SENS_23_VAR_37',  # F4A_L2
                    'EGM_OUT_SENS_23_VAR_41',  # F8A_L2
                ]

                log_step("=== Configurazione flessibile 6 sensori ===")
                for alarm in received_alarms.keys():
                    if alarm in acceptable_additions and alarm not in required_alarms:
                        desc = alarm_mapping.get(alarm, alarm)
                        log_step(f"ℹ️ Aggiunto allarme {alarm} ({desc}) agli attesi")
                        required_alarms.append(alarm)

            else:  # 12 sensori
                required_alarms = [
                    'EGM_OUT_SENS_23_VAR_32', 'EGM_OUT_SENS_23_VAR_33',
                    'EGM_OUT_SENS_23_VAR_34', 'EGM_OUT_SENS_23_VAR_35',
                    'EGM_OUT_SENS_23_VAR_36', 'EGM_OUT_SENS_23_VAR_37',
                    'EGM_OUT_SENS_23_VAR_38', 'EGM_OUT_SENS_23_VAR_39',
                    'EGM_OUT_SENS_23_VAR_40', 'EGM_OUT_SENS_23_VAR_41',
                    'EGM_OUT_SENS_23_VAR_42', 'EGM_OUT_SENS_23_VAR_43',
                ]

            # FALLBACK API AGGREGATA
            missing_after_lastval = [a for a in required_alarms if a not in received_alarms]
            
            if missing_after_lastval:
                log_step(f"⚠️ Mancano {len(missing_after_lastval)} allarmi dopo lastval")
                log_step(f"📊 Tentativo con API aggregata di fallback...")
                
                success_agg, agg_data = self.get_device_aggregated_data(device_id)
                
                if success_agg and 'measures' in agg_data:
                    measures = agg_data['measures']
                    
                    # Mappa per convertire da measures a EGM_OUT_SENS
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
                        if alarm_key in missing_after_lastval and measure_key in measures:
                            measure_data = measures[measure_key]
                            if measure_data and 'value' in measure_data:
                                received_alarms[alarm_key] = measure_data['value']
                                desc = alarm_mapping.get(alarm_key, alarm_key)
                                log_step(f"   ✓ Recuperato {alarm_key} ({desc}): {measure_data['value']} [da API aggregata]")
                else:
                    log_step(f"   ✗ API aggregata non disponibile o senza dati", False)

            # Verifica allarmi finali
            missing_alarms = []
            found_alarms = []
            other_alarms = {}

            log_step("=== Verifica Allarmi Sensori di Tiro ===")

            # Controlla allarmi richiesti
            for expected in required_alarms:
                desc = alarm_mapping.get(expected, expected)
                if expected in received_alarms:
                    found_alarms.append(expected)
                    value = received_alarms[expected]
                    log_step(f"✓ {expected} ({desc}): {value}")
                    results['alarm_values'][expected] = value
                else:
                    missing_alarms.append(expected)
                    log_step(f"✗ {expected} ({desc}): NON TROVATO", False)

            # Raccogli altri allarmi non attesi
            for alarm_key, alarm_value in received_alarms.items():
                if alarm_key not in required_alarms:
                    desc = alarm_mapping.get(alarm_key, "Sconosciuto")
                    other_alarms[alarm_key] = alarm_value

            # Mostra altri allarmi trovati
            if other_alarms:
                log_step("=== Altri Allarmi Trovati ===")
                for alarm_key, alarm_value in other_alarms.items():
                    desc = alarm_mapping.get(alarm_key, "Sconosciuto")
                    log_step(f"ℹ️ {alarm_key} ({desc}): {alarm_value}")

            # Imposta i risultati
            results['found_alarms'] = found_alarms
            results['missing_alarms'] = missing_alarms
            results['expected_alarms'] = required_alarms
            results['other_alarms'] = other_alarms
            results['total_expected'] = len(required_alarms)
            results['total_found'] = len(found_alarms)
            results['success'] = len(missing_alarms) == 0
            
            # Aggiungi versioni friendly per il frontend
            results['missing_alarms_friendly'] = [
                f"{alarm} ({alarm_mapping.get(alarm, alarm)})" 
                for alarm in missing_alarms
            ]
            results['other_alarms_friendly'] = {
                f"{key} ({alarm_mapping.get(key, 'Sconosciuto')})": value 
                for key, value in other_alarms.items()
            }

            if results['success']:
                log_step(f"✅ Test superato! Tutti gli allarmi ricevuti ({results['total_found']}/{results['total_expected']})")
            else:
                log_step(f"❌ Test fallito! Mancano {len(missing_alarms)} allarmi su {results['total_expected']}", False)

        except Exception as e:
            log_step(f"Errore durante il test: {str(e)}", False)
            results['error'] = str(e)
            results['total_expected'] = len(results.get('expected_alarms', []))
            results['total_found'] = len(results.get('found_alarms', []))

        results['end_time'] = datetime.now()
        results['duration'] = (results['end_time'] - results['start_time']).total_seconds()

        return results
    
    def get_onesait_token(self):
        """Ottiene token per chiamate Onesait Engine (diverso dal token DigilV2)"""
        try:
            url = "https://rh-sso.apps.clusterzac.opencs.servizi.prv/auth/realms/Onesait-terna/protocol/openid-connect/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': 'application',
                'client_secret': 'LW1Rz1K4YWWgShW0vslArw8To4pTQeje'
            }
            
            response = requests.post(url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            
            token_data = response.json()
            return True, token_data['access_token']
            
        except Exception as e:
            return False, f"Errore token Onesait: {str(e)}"
        
    def get_onesait_token(self):
        """Ottiene token per chiamate Onesait Engine (diverso dal token DigilV2)"""
        try:
            # Controlla se il token è ancora valido
            if self.onesait_token and self.onesait_token_expires_at:
                if datetime.now() < (self.onesait_token_expires_at - timedelta(seconds=10)):
                    return True, self.onesait_token
            
            url = "https://rh-sso.apps.clusterzac.opencs.servizi.prv/auth/realms/Onesait-terna/protocol/openid-connect/token"
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': 'application',
                'client_secret': 'LW1Rz1K4YWWgShW0vslArw8To4pTQeje'
            }
            
            print("🔑 Richiesta token Onesait...")
            response = requests.post(url, headers=headers, data=data, verify=False, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.onesait_token = token_data['access_token']
            # Token scade dopo 300 secondi
            self.onesait_token_expires_at = datetime.now() + timedelta(seconds=290)
            
            print(f"✅ Token Onesait ottenuto, scade alle: {self.onesait_token_expires_at.strftime('%H:%M:%S')}")
            return True, self.onesait_token
            
        except Exception as e:
            print(f"❌ Errore token Onesait: {e}")
            return False, f"Errore token Onesait: {str(e)}"
        
    def get_thing_metrics(self, device_name):
        """
        Recupera tutte le metriche del device da Onesait Twin Manager
        Include gli allarmi con i loro valori true/false
        """
        try:
            print(f"📊 Recupero metriche Twin Manager per: {device_name}")
            
            # Step 1: Ottieni tenantId dalla chiamata al backend DigilV2
            success, backend_response = self._get_device_info_from_backend(device_name)
            if not success:
                return False, "Impossibile recuperare tenant ID dal backend"
            
            content = backend_response.get('content', [])
            if not content or len(content) == 0:
                return False, f"Device {device_name} non trovato nel backend"
            
            tenant_id = content[0].get('tenantId')
            if not tenant_id:
                return False, "Tenant ID non presente nella response"
            
            print(f"   ✓ Tenant ID: {tenant_id}")
            
            # Step 2: Ottieni token Onesait
            success, onesait_token = self.get_onesait_token()
            if not success:
                return False, onesait_token
            
            # Step 3: Chiama Twin Manager
            url = f"https://onesait-engine-ese.apps.clusteriot.opencs.servizi.prv/twin-manager/v1/tenants/{tenant_id}/things?searchText="
            
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {onesait_token}'
            }
            
            print(f"   📡 Chiamata Twin Manager...")
            response = requests.get(url, headers=headers, verify=False, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # Estrai le metriche dal primo thing
                if 'things' in data and len(data['things']) > 0:
                    metrics = data['things'][0].get('metrics', [])
                    print(f"   ✓ Trovate {len(metrics)} metriche totali")
                    
                    # 🔍 DEBUG: Mostra TUTTE le info di un flag per capire la struttura
                    print(f"\n🔍 DEBUG: Struttura completa delle prime 3 metriche con ALG_:")
                    for metric in metrics[:50]:  # Mostra le prime 50
                        metric_name = metric.get('metric', '')
                        if 'ALG_Digil2_Alm_' in metric_name:
                            print(f"\n   📋 Metrica completa:")
                            print(f"      {metric}")
                            break  # Mostra solo il primo per non intasare i log
                    
                    # Filtra solo gli allarmi (ALG_Digil2_Alm_*)
                    alarms = {}
                    alarm_count = 0
                    for metric in metrics:
                        metric_name = metric.get('metric', '')
                        
                        # Cerca pattern ALG_Digil2_Alm_*
                        if 'ALG_Digil2_Alm_' in metric_name and '.calc' in metric_name:
                            # Rimuovi .calc dal nome
                            clean_name = metric_name.replace('.calc', '')
                            
                            # 🔍 DEBUG: Mostra i primi 3 allarmi trovati
                            if alarm_count < 3:
                                print(f"\n   🔍 Allarme #{alarm_count + 1}:")
                                print(f"      Nome: {clean_name}")
                                print(f"      Value: {metric.get('value')} (type: {type(metric.get('value'))})")
                                print(f"      Timestamp: {metric.get('timestamp')}")
                                print(f"      Metrica completa: {metric}")
                                alarm_count += 1
                            
                            alarms[clean_name] = {
                                'value': metric.get('value'),
                                'timestamp': metric.get('timestamp'),
                                'type': self._parse_alarm_type(clean_name)
                            }
                    
                    print(f"   ✓ Trovati {len(alarms)} flag allarme")
                    
                    # Debug: mostra alcuni esempi
                    if alarms:
                        sample_alarms = list(alarms.keys())[:3]
                        print(f"   Esempi: {sample_alarms}")
                    
                    return True, alarms
                else:
                    return False, "Nessun thing trovato nella response"
            else:
                error_msg = f"HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text[:200]}"
                return False, error_msg
                
        except Exception as e:
            print(f"❌ Errore recupero Twin Manager: {e}")
            import traceback
            print(traceback.format_exc())
            return False, f"Errore recupero metriche: {str(e)}"

    def _parse_alarm_type(self, alarm_name):
        """Estrae il tipo di allarme dal nome"""
        if 'Fault' in alarm_name:
            return 'fault'
        elif 'Min' in alarm_name:
            return 'min'
        elif 'Max' in alarm_name:
            return 'max'
        return 'unknown'

    def _get_device_info_from_backend(self, device_name):
        """Recupera info device dal backend DigilV2 (metodo helper)"""
        try:
            # Assicurati di avere un token valido per il backend DigilV2
            if not self.access_token:
                success, msg = self.get_auth_token()
                if not success:
                    return False, msg
            
            import urllib.parse
            encoded_name = urllib.parse.quote(device_name)
            url = f"https://digil-back-end-onesait.servizi.prv/api/v1/digils?name={encoded_name}"
            
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(url, headers=headers, verify=False, timeout=10)
            response.raise_for_status()
            
            return True, response.json()
            
        except Exception as e:
            return False, str(e)

# Istanza singleton
digil_test_service = DigilTestService()