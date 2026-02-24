"""
MongoDB Alarm Checker via SSH Tunnel
Connects to MongoDB cluster through SSH bridge to verify alarm states (boolean _calc metrics)
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from sshtunnel import SSHTunnelForwarder
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError

# Load environment variables
load_dotenv()

class MongoDBAlarmChecker:
    """
    Handles MongoDB queries through SSH tunnel to check alarm boolean states (_calc metrics).
    """
    
    def __init__(self):
        """Initialize connection parameters from environment variables."""
        self.ssh_host = os.getenv('SSH_HOST')
        self.ssh_port = int(os.getenv('SSH_PORT', 22))
        self.ssh_user = os.getenv('SSH_USER')
        self.ssh_password = os.getenv('SSH_PASSWORD')
        
        self.mongo_uri = os.getenv('MONGO_URI')
        self.mongo_database = os.getenv('MONGO_DATABASE')
        self.mongo_collection = os.getenv('MONGO_COLLECTION')
        
        self.tunnel = None
        self.client = None
        self.db = None
        self.collection = None
        
        # 🆕 Flag per tracciare stato connessione
        self.is_connected = False
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate that all required environment variables are set."""
        required_vars = [
            'SSH_HOST', 'SSH_USER', 'SSH_PASSWORD',
            'MONGO_URI', 'MONGO_DATABASE', 'MONGO_COLLECTION'
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"⚠️  Missing required environment variables: {', '.join(missing)}")
    
    def connect(self) -> bool:
        """
        Establish SSH tunnel and MongoDB connection.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            print(f"🔌 Connecting to SSH bridge: {self.ssh_user}@{self.ssh_host}:{self.ssh_port}")
            
            # Parse MongoDB hosts from URI
            # Extract hosts between @ and /?
            uri_parts = self.mongo_uri.split('@')[1].split('/?')[0]
            mongo_hosts = uri_parts.split(',')
            primary_host = mongo_hosts[0].split(':')
            mongo_host = primary_host[0]
            mongo_port = int(primary_host[1]) if len(primary_host) > 1 else 27017
            
            print(f"   📡 Target MongoDB: {mongo_host}:{mongo_port}")
            
            # Create SSH tunnel
            self.tunnel = SSHTunnelForwarder(
                (self.ssh_host, self.ssh_port),
                ssh_username=self.ssh_user,
                ssh_password=self.ssh_password,
                remote_bind_address=(mongo_host, mongo_port),
                local_bind_address=('127.0.0.1', 0)  # Auto-assign local port
            )
            
            self.tunnel.start()
            print(f"✅ SSH tunnel established on local port: {self.tunnel.local_bind_port}")
            
            # Connect to MongoDB through tunnel
            local_uri = self.mongo_uri.replace(
                uri_parts,
                f"127.0.0.1:{self.tunnel.local_bind_port}"
            )
            
            # 🆕 Log URI mascherata (senza password)
            masked_uri = local_uri.split('@')[0].split(':')[0] + ':****@' + local_uri.split('@')[1] if '@' in local_uri else local_uri
            print(f"   🔗 Connecting to: {masked_uri[:80]}...")
            
            self.client = MongoClient(
                local_uri, 
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=20000,
                socketTimeoutMS=20000
            )
            
            # Test connection
            self.client.admin.command('ping')
            print(f"✅ MongoDB connection established to database: {self.mongo_database}")
            
            self.db = self.client[self.mongo_database]
            self.collection = self.db[self.mongo_collection]
            
            # 🆕 Verifica che la collection esista
            collections = self.db.list_collection_names()
            print(f"   📂 Collections disponibili: {collections[:5]}{'...' if len(collections) > 5 else ''}")
            
            if self.mongo_collection in collections:
                print(f"   ✅ Collection '{self.mongo_collection}' trovata")
            else:
                print(f"   ⚠️ Collection '{self.mongo_collection}' NON trovata!")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"❌ Connection error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            self.disconnect()
            return False
    
    def disconnect(self):
        """Close MongoDB connection and SSH tunnel."""
        try:
            if self.client:
                self.client.close()
                print("🔌 MongoDB connection closed")
            
            if self.tunnel:
                self.tunnel.stop()
                print("🔌 SSH tunnel closed")
            
            self.is_connected = False
                
        except Exception as e:
            print(f"⚠️  Error during disconnect: {e}")
    
    def check_connection_health(self) -> bool:
        """
        🆕 Verifica che la connessione sia ancora attiva.
        
        Returns:
            bool: True se connessione OK, False altrimenti
        """
        if not self.is_connected or self.client is None:
            print("   ⚠️ MongoDB: non connesso (is_connected=False o client=None)")
            return False
        
        try:
            # Ping per verificare connessione
            self.client.admin.command('ping')
            return True
        except Exception as e:
            print(f"   ⚠️ MongoDB connection health check failed: {type(e).__name__}: {e}")
            self.is_connected = False
            return False
    
    def check_alarm_boolean(
        self, 
        device_id: str, 
        alarm_metric: str,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """
        Check if an alarm boolean (_calc) is active (true) for a specific device and metric.
        
        Args:
            device_id: Device client ID (e.g., "1:1:2:15:21:DIGIL_IND_0015")
            alarm_metric: Alarm metric to check (e.g., "EAM_OUT_ALG_19_VAR_20")
            timeout: Query timeout in seconds
            
        Returns:
            Dict with keys:
                - 'found': bool - Whether the document was found in MongoDB
                - 'active': bool - Whether alarm boolean is true
                - 'timestamp': str - Timestamp of the alarm
                - 'metric_checked': str - The metric that was queried (_calc)
                - 'error': str - Error message if any
        """
        result = {
            'found': False,
            'active': False,
            'timestamp': None,
            'timestamp_unix': None,
            'metric_checked': f"{alarm_metric}_calc",
            'error': None
        }
        
        # 🆕 LOGGING DETTAGLIATO
        print(f"\n   🔍 MongoDB Query for {alarm_metric}_calc")
        print(f"      Device ID: {device_id}")
        
        if self.collection is None:
            result['error'] = "Not connected to MongoDB (collection is None)"
            print(f"      ❌ {result['error']}")
            return result
        
        # 🆕 Verifica health della connessione
        if not self.check_connection_health():
            result['error'] = "MongoDB connection lost"
            print(f"      ❌ {result['error']}")
            return result
        
        try:
            # Build query: looking for _calc metric with value = true
            metric_path = f"payload.metrics.{alarm_metric}_calc.value"
            query = {
                "clientId": device_id,
                metric_path: {"$eq": True}
            }
            
            # 🆕 LOG QUERY
            print(f"      📝 Query: {json.dumps(query, indent=None)}")
            print(f"      📂 Database: {self.mongo_database}")
            print(f"      📂 Collection: {self.mongo_collection}")
            
            # Execute query with timeout - SORT by receivedOn DESC to get most recent
            cursor = self.collection.find(
                query,
                max_time_ms=timeout * 1000
            ).sort("receivedOn", -1).limit(1)  # -1 = DESCENDING
            
            # 🆕 Conta documenti (per debug)
            # NOTA: count() è deprecato, usiamo una lista
            documents = list(cursor)
            doc_count = len(documents)
            
            print(f"      📊 Documenti trovati: {doc_count}")
            
            if doc_count == 0:
                # 🆕 Query di debug: cerca QUALSIASI documento per questo device
                debug_query = {"clientId": device_id}
                debug_count = self.collection.count_documents(debug_query, limit=10)
                print(f"      🔎 Debug: documenti totali per device '{device_id}': {debug_count}")
                
                if debug_count == 0:
                    print(f"      ⚠️ Nessun documento per questo device! Verifica clientId format.")
                    # 🆕 Cerca pattern simili
                    if ':' in device_id:
                        # Prova a cercare con pattern
                        device_suffix = device_id.split(':')[-1]  # es: DIGIL_IND_0751
                        pattern_query = {"clientId": {"$regex": device_suffix}}
                        pattern_count = self.collection.count_documents(pattern_query, limit=5)
                        print(f"      🔎 Documenti con pattern '{device_suffix}': {pattern_count}")
                        
                        if pattern_count > 0:
                            # Mostra un esempio di clientId trovato
                            sample = self.collection.find_one(pattern_query, {"clientId": 1})
                            if sample:
                                print(f"      💡 Esempio clientId trovato: {sample.get('clientId')}")
                else:
                    # 🆕 Cerca se ci sono metriche _calc per questo device
                    calc_query = {
                        "clientId": device_id,
                        f"payload.metrics.{alarm_metric}_calc": {"$exists": True}
                    }
                    calc_count = self.collection.count_documents(calc_query, limit=10)
                    print(f"      🔎 Documenti con metrica {alarm_metric}_calc esistente: {calc_count}")
                    
                    if calc_count > 0:
                        # La metrica esiste ma value != true
                        sample = self.collection.find_one(calc_query, {f"payload.metrics.{alarm_metric}_calc": 1})
                        if sample and 'payload' in sample:
                            calc_value = sample.get('payload', {}).get('metrics', {}).get(f"{alarm_metric}_calc", {})
                            print(f"      💡 Valore attuale della metrica: {calc_value}")
                    else:
                        # 🆕 Lista tutte le metriche disponibili per debug
                        any_doc = self.collection.find_one({"clientId": device_id}, {"payload.metrics": 1})
                        if any_doc and 'payload' in any_doc and 'metrics' in any_doc['payload']:
                            available_metrics = list(any_doc['payload']['metrics'].keys())
                            calc_metrics = [m for m in available_metrics if '_calc' in m]
                            print(f"      📋 Metriche _calc disponibili: {calc_metrics[:10]}{'...' if len(calc_metrics) > 10 else ''}")
                
                return result
            
            # Get the first (most recent) document
            document = documents[0]
            
            if document:
                result['found'] = True
                result['active'] = True
                
                # 🆕 Debug: Stampa struttura documento
                print(f"      📄 Document keys: {list(document.keys())}")
                print(f"      📄 receivedOn: {document.get('receivedOn', 'N/A')}")
                
                if 'payload' in document:
                    payload_keys = list(document['payload'].keys()) if isinstance(document['payload'], dict) else 'not a dict'
                    print(f"      📄 Payload keys: {payload_keys}")
                
                # Extract timestamp - priorità: receivedOn -> timestamp -> payload.metrics.TIMESTAMP
                timestamp_value = None
                
                # Prova 1: receivedOn (sempre disponibile, più semplice)
                timestamp_value = document.get('receivedOn')
                if timestamp_value:
                    print(f"      ✓ Timestamp da receivedOn: {timestamp_value}")
                
                # Prova 2: timestamp a root level (fallback)
                if not timestamp_value:
                    timestamp_value = document.get('timestamp')
                    if timestamp_value:
                        print(f"      ✓ Timestamp da root level: {timestamp_value}")
                
                # Prova 3: payload.metrics.TIMESTAMP.value (più preciso ma più complesso)
                if not timestamp_value and 'payload' in document and isinstance(document['payload'], dict):
                    if 'metrics' in document['payload'] and isinstance(document['payload']['metrics'], dict):
                        timestamp_metric = document['payload']['metrics'].get('TIMESTAMP')
                        if timestamp_metric and isinstance(timestamp_metric, dict):
                            timestamp_value = timestamp_metric.get('value')
                            print(f"      ✓ Timestamp da payload.metrics.TIMESTAMP: {timestamp_value}")
                
                if timestamp_value:
                    try:
                        # Handle milliseconds timestamp
                        if timestamp_value > 10000000000:
                            timestamp_value_seconds = timestamp_value / 1000
                        else:
                            timestamp_value_seconds = timestamp_value
                        
                        # Salva timestamp unix per filtro temporale
                        result['timestamp_unix'] = timestamp_value_seconds
                        
                        # Formatta per visualizzazione
                        dt = datetime.fromtimestamp(timestamp_value_seconds)
                        result['timestamp'] = dt.strftime('%d/%m/%y - %H:%M:%S')
                        
                        print(f"      ✅ Timestamp formattato: {result['timestamp']}")
                    except Exception as e:
                        print(f"      ⚠️ Errore formattazione timestamp: {e}")
                        result['timestamp'] = str(timestamp_value)
                        result['timestamp_unix'] = None
                else:
                    print(f"      ⚠️ Nessun timestamp trovato nel documento")
                    result['timestamp'] = 'N/A'
                    result['timestamp_unix'] = None
            
            return result
            
        except OperationFailure as e:
            result['error'] = f"Query failed: {e}"
            print(f"      ❌ OperationFailure: {e}")
            return result
        except ServerSelectionTimeoutError as e:
            result['error'] = f"MongoDB timeout: {e}"
            print(f"      ❌ ServerSelectionTimeoutError: {e}")
            return result
        except Exception as e:
            result['error'] = f"Unexpected error: {type(e).__name__}: {e}"
            print(f"      ❌ Exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return result
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# MAPPATURA: EGM sensor metrics -> EAM alarm metrics (for boolean check)
# Basata sul file tiro-dict.txt
SENSOR_TO_ALARM_MAP = {
    # Fase 4A L1
    'EGM_OUT_SENS_23_VAR_36': ['EAM_OUT_ALG_19_VAR_13', 'EAM_OUT_ALG_19_VAR_14'],  # TC_F4A_L1 (Min, Max)
    # Fase 4B L1
    'EGM_OUT_SENS_23_VAR_38': ['EAM_OUT_ALG_19_VAR_15', 'EAM_OUT_ALG_19_VAR_16'],  # TC_F4B_L1
    # Fase 8A L1
    'EGM_OUT_SENS_23_VAR_40': ['EAM_OUT_ALG_19_VAR_17', 'EAM_OUT_ALG_19_VAR_18'],  # TC_F8A_L1
    # Fase 8B L1
    'EGM_OUT_SENS_23_VAR_42': ['EAM_OUT_ALG_19_VAR_19', 'EAM_OUT_ALG_19_VAR_20'],  # TC_F8B_L1
    # Fase 12A L1
    'EGM_OUT_SENS_23_VAR_32': ['EAM_OUT_ALG_19_VAR_21', 'EAM_OUT_ALG_19_VAR_22'],  # TC_F12A_L1
    # Fase 12B L1
    'EGM_OUT_SENS_23_VAR_34': ['EAM_OUT_ALG_19_VAR_23', 'EAM_OUT_ALG_19_VAR_24'],  # TC_F12B_L1
    
    # Fase 4A L2
    'EGM_OUT_SENS_23_VAR_37': ['EAM_OUT_ALG_19_VAR_25', 'EAM_OUT_ALG_19_VAR_26'],  # TC_F4A_L2
    # Fase 4B L2
    'EGM_OUT_SENS_23_VAR_39': ['EAM_OUT_ALG_19_VAR_27', 'EAM_OUT_ALG_19_VAR_28'],  # TC_F4B_L2
    # Fase 8A L2
    'EGM_OUT_SENS_23_VAR_41': ['EAM_OUT_ALG_19_VAR_29', 'EAM_OUT_ALG_19_VAR_30'],  # TC_F8A_L2
    # Fase 8B L2
    'EGM_OUT_SENS_23_VAR_43': ['EAM_OUT_ALG_19_VAR_31', 'EAM_OUT_ALG_19_VAR_32'],  # TC_F8B_L2
    # Fase 12A L2
    'EGM_OUT_SENS_23_VAR_33': ['EAM_OUT_ALG_19_VAR_33', 'EAM_OUT_ALG_19_VAR_34'],  # TC_F12A_L2
    # Fase 12B L2
    'EGM_OUT_SENS_23_VAR_35': ['EAM_OUT_ALG_19_VAR_35', 'EAM_OUT_ALG_19_VAR_36'],  # TC_F12B_L2
}


def get_alarm_metrics_for_sensor(sensor_metric: str) -> list:
    """
    Get the alarm metrics (EAM) corresponding to a sensor metric (EGM).
    
    Args:
        sensor_metric: EGM sensor metric (e.g., "EGM_OUT_SENS_23_VAR_42")
        
    Returns:
        List of EAM alarm metrics [MIN, MAX] or empty list if not found
    """
    return SENSOR_TO_ALARM_MAP.get(sensor_metric, [])


# Example usage / testing
if __name__ == "__main__":
    import sys
    
    # Test the MongoDB connection and alarm check
    test_device_id = "1:1:2:16:21:DIGIL_IND_0751"  # Il device che stai testando
    test_alarm_metric = "EAM_OUT_ALG_19_VAR_14"  # Uno degli allarmi mancanti
    
    print("🧪 Testing MongoDB Alarm Checker - ENHANCED LOGGING\n")
    print("⚠️  Make sure .env file is configured with SSH and MongoDB credentials!\n")
    
    try:
        with MongoDBAlarmChecker() as checker:
            if checker.client:
                print(f"\n🔍 Checking alarm boolean state for:")
                print(f"   Device: {test_device_id}")
                print(f"   Metric: {test_alarm_metric}_calc\n")
                
                result = checker.check_alarm_boolean(test_device_id, test_alarm_metric)
                
                print("\n" + "="*60)
                print("📊 FINAL RESULT:")
                print(f"   Found: {result['found']}")
                print(f"   Active: {result['active']}")
                print(f"   Timestamp: {result['timestamp']}")
                print(f"   Timestamp Unix: {result['timestamp_unix']}")
                print(f"   Metric Checked: {result['metric_checked']}")
                if result['error']:
                    print(f"   Error: {result['error']}")
                print("="*60)
                    
                if result['active']:
                    print("\n✅ Alarm boolean is TRUE - test would be VALIDATED!")
                else:
                    print("\n❌ Alarm boolean is FALSE or not found")
            else:
                print("❌ Failed to connect to MongoDB")
                sys.exit(1)
                
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\n📝 Please create a .env file with:")
        print("   SSH_HOST=10.147.131.41")
        print("   SSH_PORT=22")
        print("   SSH_USER=reply")
        print("   SSH_PASSWORD=your_password")
        print("   MONGO_URI=mongodb://...")
        print("   MONGO_DATABASE=ibm_iot")
        print("   MONGO_COLLECTION=unsolicited")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)