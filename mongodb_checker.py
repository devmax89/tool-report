"""
MongoDB Alarm Checker via SSH Tunnel
Connects to MongoDB cluster through SSH bridge to verify alarm states (boolean _calc metrics)
"""

import os
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
            
            self.client = MongoClient(
                local_uri, 
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            
            # Test connection
            self.client.admin.command('ping')
            print(f"✅ MongoDB connection established to database: {self.mongo_database}")
            
            self.db = self.client[self.mongo_database]
            self.collection = self.db[self.mongo_collection]
            
            return True
            
        except Exception as e:
            print(f"❌ Connection error: {e}")
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
                
        except Exception as e:
            print(f"⚠️  Error during disconnect: {e}")
    
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
            'timestamp_unix': None,  # 🆕 NUOVO: timestamp numerico per filtro temporale
            'metric_checked': f"{alarm_metric}_calc",
            'error': None
        }
        
        if self.collection is None:
            result['error'] = "Not connected to MongoDB"
            return result
        
        try:
            # Build query: looking for _calc metric with value = true
            metric_path = f"payload.metrics.{alarm_metric}_calc.value"
            query = {
                "clientId": device_id,
                metric_path: {"$eq": True}
            }
            
            # Execute query with timeout - SORT by receivedOn DESC to get most recent
            cursor = self.collection.find(
                query,
                max_time_ms=timeout * 1000
            ).sort("receivedOn", -1).limit(1)  # -1 = DESCENDING
            
            # Get the first (most recent) document
            document = None
            try:
                document = next(cursor, None)
            except StopIteration:
                document = None
            
            if document:
                result['found'] = True
                result['active'] = True
                
                # DEBUG: Stampa struttura documento per capire dove sta il timestamp
                print(f"   📄 MongoDB document keys: {list(document.keys())}")
                if 'payload' in document:
                    print(f"   📄 Payload keys: {list(document['payload'].keys()) if isinstance(document['payload'], dict) else 'not a dict'}")
                
                # Extract timestamp - priorità: receivedOn -> timestamp -> payload.metrics.TIMESTAMP
                timestamp_value = None
                
                # Prova 1: receivedOn (sempre disponibile, più semplice)
                timestamp_value = document.get('receivedOn')
                if timestamp_value:
                    print(f"   ✓ Timestamp da receivedOn: {timestamp_value}")
                
                # Prova 2: timestamp a root level (fallback)
                if not timestamp_value:
                    timestamp_value = document.get('timestamp')
                    if timestamp_value:
                        print(f"   ✓ Timestamp da root level: {timestamp_value}")
                
                # Prova 3: payload.metrics.TIMESTAMP.value (più preciso ma più complesso)
                if not timestamp_value and 'payload' in document and isinstance(document['payload'], dict):
                    if 'metrics' in document['payload'] and isinstance(document['payload']['metrics'], dict):
                        timestamp_metric = document['payload']['metrics'].get('TIMESTAMP')
                        if timestamp_metric and isinstance(timestamp_metric, dict):
                            timestamp_value = timestamp_metric.get('value')
                            print(f"   ✓ Timestamp da payload.metrics.TIMESTAMP: {timestamp_value}")
                
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
                    except Exception as e:
                        result['timestamp'] = str(timestamp_value)
                        result['timestamp_unix'] = None
                else:
                    result['timestamp'] = 'N/A'
                    result['timestamp_unix'] = None
            
            return result
            
        except OperationFailure as e:
            result['error'] = f"Query failed: {e}"
            return result
        except ServerSelectionTimeoutError as e:
            result['error'] = f"MongoDB timeout: {e}"
            return result
        except Exception as e:
            result['error'] = f"Unexpected error: {e}"
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
    test_device_id = "1:1:2:15:21:DIGIL_IND_0015"
    test_alarm_metric = "EAM_OUT_ALG_19_VAR_20"  # TC_F8B_L1 Max alarm
    
    print("🧪 Testing MongoDB Alarm Checker\n")
    print("⚠️  Make sure .env file is configured with SSH and MongoDB credentials!\n")
    
    try:
        with MongoDBAlarmChecker() as checker:
            if checker.client:
                print(f"\n🔍 Checking alarm boolean state for:")
                print(f"   Device: {test_device_id}")
                print(f"   Metric: {test_alarm_metric}_calc\n")
                
                result = checker.check_alarm_boolean(test_device_id, test_alarm_metric)
                
                print("📊 Result:")
                print(f"   Found: {result['found']}")
                print(f"   Active: {result['active']}")
                print(f"   Timestamp: {result['timestamp']}")
                print(f"   Metric Checked: {result['metric_checked']}")
                if result['error']:
                    print(f"   Error: {result['error']}")
                    
                if result['active']:
                    print("\n✅ Alarm boolean is TRUE - test would be VALIDATED!")
                else:
                    print("\n❌ Alarm boolean is FALSE or not found - waiting for alarm...")
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