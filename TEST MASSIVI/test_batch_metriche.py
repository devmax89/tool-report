import requests
import json
import time
from datetime import datetime
import pandas as pd

# Lista dei dispositivi da testare
DEVICES = [
    "1:1:2:15:21:DIGIL_IND_0108", "1:1:2:16:21:DIGIL_IND_0529", "1:1:2:16:21:DIGIL_IND_0470",
    "1:1:2:16:21:DIGIL_IND_0471", "1:1:2:16:21:DIGIL_IND_0474", "1:1:2:15:21:DIGIL_IND_0260",
    "1:1:2:16:21:DIGIL_IND_0500", "1:1:2:16:21:DIGIL_IND_0670", "1:1:2:15:21:DIGIL_IND_0323",
    "1:1:2:16:21:DIGIL_IND_0756", "1:1:2:16:21:DIGIL_IND_0757", "1:1:2:15:21:DIGIL_IND_0099",
    "1:1:2:15:21:DIGIL_IND_0102", "1:1:2:15:21:DIGIL_IND_0103", "1:1:2:15:21:DIGIL_IND_0105",
    "1:1:2:16:21:DIGIL_IND_0517", "1:1:2:16:21:DIGIL_IND_0521", "1:1:2:16:21:DIGIL_IND_0524",
    "1:1:2:16:21:DIGIL_IND_0525", "1:1:2:16:21:DIGIL_IND_0634", "1:1:2:16:21:DIGIL_IND_0651",
    "1:1:2:16:21:DIGIL_IND_0652", "1:1:2:15:21:DIGIL_IND_0271", "1:1:2:16:21:DIGIL_IND_0690",
    "1:1:2:16:21:DIGIL_IND_0691", "1:1:2:15:21:DIGIL_IND_0176", "1:1:2:15:21:DIGIL_IND_0177"
]

# Configurazione
BASE_URL = "http://localhost:5000"  # URL del tuo DIGIL Report Generator
TIME_RANGE = 5  # Minuti di metriche da controllare

# Carica anagrafica dal file CSV locale (opzionale - se vuoi usarla direttamente dallo script)
def load_anagrafica_from_csv(csv_path="digil_anagrafica_data_result.csv"):
    """Carica l'anagrafica dal CSV per recuperare UI e num_sensori"""
    try:
        import csv
        anagrafica = {}
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                device_id = row.get('DeviceID', row.get('deviceid', ''))
                if device_id:
                    anagrafica[device_id] = {
                        'ui': row.get('UI', row.get('ui', 'Lazio')),
                        'n_sensori': row.get('n_sensori', row.get('N_SENSORI', '6'))
                    }
        
        print(f"✅ Anagrafica caricata: {len(anagrafica)} dispositivi")
        return anagrafica
    except Exception as e:
        print(f"⚠️ Impossibile caricare anagrafica: {e}")
        print("   Uso valori di default: 6 sensori, UI Lazio")
        return None

# Anagrafica globale
ANAGRAFICA = load_anagrafica_from_csv()

def get_device_config(device_id):
    """Ottiene configurazione del dispositivo dall'anagrafica"""
    
    if ANAGRAFICA and device_id in ANAGRAFICA:
        config = ANAGRAFICA[device_id]
        num_sensors = config.get('n_sensori', '6')
        ui_location = config.get('ui', 'Lazio')
        
        # Normalizza num_sensors
        try:
            num_sensors = str(int(float(num_sensors)))  # Converte "6.0" in "6"
        except:
            num_sensors = '6'
        
        return num_sensors, ui_location
    else:
        # Valori di default se non trovato
        print(f"   ⚠️ {device_id} non trovato in anagrafica, uso default")
        return '6', 'Lazio'

def test_single_device(device_id, time_range=TIME_RANGE):
    """Esegue test metriche per un singolo dispositivo usando l'anagrafica"""
    
    # Recupera configurazione dall'anagrafica
    num_sensors, ui_location = get_device_config(device_id)
    
    print(f"\n🔍 Testing: {device_id}")
    print(f"   Config: {num_sensors} sensori, UI: {ui_location}")
    
    try:
        # Prepara i dati per la richiesta
        form_data = {
            'device_id': device_id,
            'num_sensors': num_sensors,
            'time_range': time_range,
            'ui_location': ui_location
        }
        
        # Chiama l'API
        response = requests.post(f"{BASE_URL}/test_metrics", data=form_data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Estrai le informazioni principali
            success = result.get('success', False)
            total_found = result.get('total_found', 0)
            total_expected = result.get('total_expected', 0)
            
            # Dettagli per categoria
            metrics_by_category = result.get('metrics_by_category', {})
            
            return {
                'device_id': device_id,
                'num_sensors': num_sensors,
                'ui_location': ui_location,
                'success': success,
                'total_found': total_found,
                'total_expected': total_expected,
                'percentage': (total_found / total_expected * 100) if total_expected > 0 else 0,
                'weather_found': len(metrics_by_category.get('weather', {}).get('found', [])),
                'junction_box_found': len(metrics_by_category.get('junction_box', {}).get('found', [])),
                'load_found': len(metrics_by_category.get('load', {}).get('found', [])),
                'weather_missing': metrics_by_category.get('weather', {}).get('missing', []),
                'junction_missing': metrics_by_category.get('junction_box', {}).get('missing', []),
                'load_missing': metrics_by_category.get('load', {}).get('missing', []),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            return {
                'device_id': device_id,
                'num_sensors': num_sensors,
                'ui_location': ui_location,
                'success': False,
                'error': f"HTTP {response.status_code}",
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
    except Exception as e:
        return {
            'device_id': device_id,
            'num_sensors': num_sensors,
            'ui_location': ui_location,
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def run_batch_test():
    """Esegue test su tutti i dispositivi"""
    
    print(f"🚀 Avvio test batch per {len(DEVICES)} dispositivi")
    print(f"   Range temporale: {TIME_RANGE} minuti")
    print(f"   Configurazioni prese dall'anagrafica")
    print("="*70)
    
    results = []
    
    # Raggruppa per UI per info
    ui_counts = {}
    
    for i, device_id in enumerate(DEVICES, 1):
        print(f"\n[{i}/{len(DEVICES)}] ", end="")
        
        # Esegui test
        result = test_single_device(device_id)
        results.append(result)
        
        # Conta per UI
        ui = result.get('ui_location', 'Unknown')
        ui_counts[ui] = ui_counts.get(ui, 0) + 1
        
        # Stampa risultato immediato
        if result.get('success'):
            print(f"✅ PASS - {result['total_found']}/{result['total_expected']} metriche ({result['percentage']:.1f}%)")
        else:
            if 'error' in result:
                print(f"❌ ERRORE - {result.get('error', 'Errore sconosciuto')}")
            else:
                print(f"⚠️ FAIL - {result.get('total_found', 0)}/{result.get('total_expected', 0)} metriche ({result.get('percentage', 0):.1f}%)")
                # Mostra dettagli mancanti per categoria
                if result.get('weather_missing'):
                    print(f"   🌤️ Meteo mancanti: {', '.join(result['weather_missing'])}")
                if result.get('junction_missing'):
                    print(f"   📦 Junction mancanti: {', '.join(result['junction_missing'])}")
                if result.get('load_missing'):
                    print(f"   ⚡ Tiro mancanti: {', '.join(result['load_missing'][:3])}")
        
        # Piccola pausa per non sovraccaricare il server
        time.sleep(2)
    
    # Mostra distribuzione UI
    print(f"\n📍 Distribuzione per UI:")
    for ui, count in ui_counts.items():
        print(f"   - {ui}: {count} dispositivi")
    
    return results

def generate_report(results):
    """Genera report Excel con i risultati dettagliati"""
    
    # Crea DataFrame principale
    df = pd.DataFrame(results)
    
    # Calcola statistiche
    total_devices = len(results)
    successful = df['success'].sum() if 'success' in df else 0
    failed = total_devices - successful
    avg_percentage = df['percentage'].mean() if 'percentage' in df else 0
    
    # Salva Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"test_metriche_batch_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Sheet principale con risultati
        df.to_excel(writer, sheet_name='Risultati', index=False)
        
        # Sheet con statistiche
        stats_data = {
            'Metrica': ['Totale Dispositivi', 'Test Riusciti', 'Test Falliti', 'Percentuale Successo', 'Media Metriche (%)'],
            'Valore': [total_devices, successful, failed, f"{(successful/total_devices*100):.1f}%", f"{avg_percentage:.1f}%"]
        }
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistiche', index=False)
        
        # Sheet per UI
        if 'ui_location' in df.columns:
            ui_summary = df.groupby('ui_location').agg({
                'success': 'sum',
                'device_id': 'count',
                'percentage': 'mean'
            }).round(2)
            ui_summary.columns = ['Successi', 'Totale', 'Media %']
            ui_summary.to_excel(writer, sheet_name='Per UI')
        
        # Sheet con dispositivi problematici
        if 'success' in df.columns:
            failed_df = df[df['success'] == False]
            if not failed_df.empty:
                failed_df.to_excel(writer, sheet_name='Dispositivi Falliti', index=False)
    
    print(f"\n📊 Report salvato in: {filename}")
    return filename

def print_summary(results):
    """Stampa riepilogo dei risultati"""
    
    print("\n" + "="*70)
    print("📈 RIEPILOGO TEST BATCH")
    print("="*70)
    
    total = len(results)
    successful = sum(1 for r in results if r.get('success'))
    failed = total - successful
    
    print(f"Totale dispositivi testati: {total}")
    print(f"✅ Successo: {successful} ({successful/total*100:.1f}%)")
    print(f"❌ Falliti: {failed} ({failed/total*100:.1f}%)")
    
    # Analisi per categoria di metriche
    weather_issues = sum(1 for r in results if r.get('weather_missing'))
    junction_issues = sum(1 for r in results if r.get('junction_missing'))
    load_issues = sum(1 for r in results if r.get('load_missing'))
    
    if any([weather_issues, junction_issues, load_issues]):
        print(f"\n📊 Problemi per categoria:")
        if weather_issues:
            print(f"  🌤️ Meteo: {weather_issues} dispositivi con problemi")
        if junction_issues:
            print(f"  📦 Junction Box: {junction_issues} dispositivi con problemi")
        if load_issues:
            print(f"  ⚡ Sensori Tiro: {load_issues} dispositivi con problemi")
    
    # Dispositivi con problemi
    failed_devices = [r for r in results if not r.get('success')]
    if failed_devices:
        print(f"\n⚠️ Dettaglio dispositivi con problemi:")
        for result in failed_devices[:10]:  # Mostra max 10
            device = result['device_id']
            if 'error' in result:
                print(f"  - {device}: {result['error']}")
            else:
                print(f"  - {device}: {result.get('total_found', 0)}/{result.get('total_expected', 0)} metriche")
                print(f"    UI: {result.get('ui_location')}, Sensori: {result.get('num_sensors')}")

if __name__ == "__main__":
    print("🔧 DIGIL Batch Test - Metriche\n")
    
    # Verifica che il server sia raggiungibile
    try:
        test_response = requests.get(BASE_URL)
        print(f"✅ Server raggiungibile su {BASE_URL}\n")
    except:
        print(f"❌ ERRORE: Server non raggiungibile su {BASE_URL}")
        print("   Assicurati che DIGIL Report Generator sia in esecuzione!")
        exit(1)
    
    # Esegui test
    results = run_batch_test()
    
    # Genera report Excel
    report_file = generate_report(results)
    
    # Stampa riepilogo
    print_summary(results)
    
    print(f"\n✨ Test completato! Controlla il file {report_file} per i dettagli.")