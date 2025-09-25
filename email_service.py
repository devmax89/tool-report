import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from jinja2 import Template

# Carica le variabili d'ambiente dal percorso corretto
if getattr(sys, 'frozen', False):
    base_path = Path(sys.executable).parent
    env_path = base_path / '_internal' / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        env_path = base_path / '.env'
        if env_path.exists():
            load_dotenv(env_path)
else:
    load_dotenv()

class EmailService:
    def __init__(self):
        # Configurazione SMTP dalle variabili d'ambiente
        self.smtp_config = {
            'gmail': {
                'server': 'smtp.gmail.com',
                'port': 587,
                'use_tls': True,
                'username': os.getenv('GMAIL_USER', 'digil.report.info@gmail.com'),
                'password': os.getenv('GMAIL_APP_PASSWORD', '')
            },
            'outlook': {
                'server': 'smtp-mail.outlook.com',
                'port': 587,
                'use_tls': True,
                'username': os.getenv('OUTLOOK_USER', 'm.tavernese@reply.it'),
                'password': os.getenv('OUTLOOK_PASSWORD', '')
            }
        }
        
        # Verifica se Outlook COM è disponibile
        self.outlook_com_available = self.check_outlook_com()
        
        # Provider attivo (può essere cambiato tramite env o default)
        if self.outlook_com_available:
            self.active_provider = 'outlook_com'  # Priorità a Outlook COM se disponibile
            print("✅ Outlook COM disponibile - sarà usato per l'invio email")
        else:
            self.active_provider = os.getenv('EMAIL_PROVIDER', 'gmail')
            print(f"ℹ️ Outlook COM non disponibile - uso {self.active_provider}")
        
        # Carica configurazione destinatari
        self.load_recipients_config()
        
        # Verifica configurazione all'avvio
        if self.active_provider != 'outlook_com':
            self.check_configuration()
    
    def check_outlook_com(self):
        """Verifica se Outlook COM API è disponibile"""
        try:
            import win32com.client
            outlook = win32com.client.Dispatch('outlook.application')
            return True
        except:
            return False
    
    def check_configuration(self):
        """Verifica che la configurazione email sia completa"""
        config = self.smtp_config[self.active_provider]
        if not config['password']:
            print(f"⚠️ ATTENZIONE: Password non configurata per {self.active_provider}")
            print(f"   Configura {self.active_provider.upper()}_APP_PASSWORD nel file .env")
        else:
            print(f"✅ Email service configurato correttamente con {self.active_provider}")
    
    def load_recipients_config(self):
        """Carica la configurazione dei destinatari dal file JSON"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
            config_path = base_path / '_internal' / 'config' / 'email_recipients.json'
            if not config_path.exists():
                config_path = base_path / 'config' / 'email_recipients.json'
        else:
            config_path = Path('config/email_recipients.json')
        
        # PER ORA: Tutti i destinatari puntano a digil.report.info@gmail.com
        # Questo è temporaneo finché non definisci le email finali
        if not config_path.exists():
            config_path.parent.mkdir(exist_ok=True, parents=True)
            default_config = {
                "MII": {
                    "to": ["digil.report.info@gmail.com"],
                    "cc": []
                },
                "Indra/Olivetti": {
                    "to": ["digil.report.info@gmail.com"],
                    "cc": []
                },
                "Sirtiv2": {
                    "to": ["digil.report.info@gmail.com"],
                    "cc": []
                },
                "default": {
                    "to": ["digil.report.info@gmail.com"],
                    "cc": []
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"📁 Creato file di configurazione destinatari: {config_path}")
        
        try:
            with open(config_path, 'r') as f:
                self.recipients_config = json.load(f)
            print(f"📧 Caricata configurazione destinatari da {config_path}")
        except Exception as e:
            print(f"❌ Errore caricamento configurazione destinatari: {e}")
            self.recipients_config = {"default": {"to": ["digil.report.info@gmail.com"], "cc": []}}
    
    def get_recipients(self, vendor):
        """Ottiene i destinatari per un vendor specifico"""
        vendor_clean = vendor.replace('/', '-').replace('\\', '-')
        
        for key in [vendor, vendor_clean, 'default']:
            if key in self.recipients_config:
                return self.recipients_config[key]
        
        return {'to': ['digil.report.info@gmail.com'], 'cc': []}
    
    def send_via_outlook_com(self, zip_path, vendor, device_id, date_formatted):
        """Invia email usando Outlook COM API (Windows only)"""
        try:
            import win32com.client
            import pythoncom
            from pathlib import Path
            
            print("📧 Invio tramite Outlook COM...")
            
            # IMPORTANTE: Inizializza COM per questo thread
            pythoncom.CoInitialize()
            
            try:
                # Connetti a Outlook
                outlook = win32com.client.Dispatch('outlook.application')
                mail = outlook.CreateItem(0)  # 0 = olMailItem
                
                # Ottieni destinatari
                recipients = self.get_recipients(vendor)
                
                # Configura email
                mail.To = '; '.join(recipients['to'])
                if recipients.get('cc'):
                    mail.CC = '; '.join(recipients['cc'])
                
                mail.Subject = f"Report DIGIL - {vendor} - {date_formatted} - Device {device_id}"
                
                # Carica template HTML
                if getattr(sys, 'frozen', False):
                    base_path = Path(sys.executable).parent
                    template_path = base_path / '_internal' / 'templates' / 'email_template.html'
                    if not template_path.exists():
                        template_path = Path(sys._MEIPASS) / 'templates' / 'email_template.html'
                else:
                    template_path = Path('templates/email_template.html')
                
                with open(template_path, 'r', encoding='utf-8') as f:
                    template = Template(f.read())
                
                # Renderizza il template
                html_body = template.render(
                    vendor=vendor,
                    device_id=device_id,
                    date_formatted=date_formatted,
                    send_datetime=datetime.now().strftime('%d/%m/%Y %H:%M'),
                    filename=os.path.basename(zip_path)
                )
                
                # Imposta il corpo HTML
                mail.HTMLBody = html_body
                
                # IMPORTANTE: Converti il percorso in assoluto
                absolute_path = os.path.abspath(zip_path)
                print(f"📎 Allegato: {absolute_path}")
                
                # Verifica che il file esista
                if not os.path.exists(absolute_path):
                    raise FileNotFoundError(f"File non trovato: {absolute_path}")
                
                # Aggiungi allegato con percorso assoluto
                mail.Attachments.Add(absolute_path)
                
                # Invia
                mail.Send()
                
                all_recipients = recipients['to'] + recipients.get('cc', [])
                return True, f"Email inviata con successo tramite Outlook a: {', '.join(all_recipients)}"
                
            finally:
                # IMPORTANTE: Deinizializza COM
                pythoncom.CoUninitialize()
                
        except ImportError:
            return False, "Libreria pywin32 non installata. Esegui: pip install pywin32"
        except FileNotFoundError as e:
            return False, f"File allegato non trovato: {str(e)}"
        except Exception as e:
            return False, f"Errore invio tramite Outlook COM: {str(e)}"
    
    def send_via_smtp(self, zip_path, vendor, device_id, date_formatted, config):
        """Metodo esistente per invio via SMTP (Gmail/Outlook)"""
        try:
            # Crea messaggio
            msg = MIMEMultipart()
            msg['From'] = f"DIGIL Report System <{config['username']}>"
            
            recipients = self.get_recipients(vendor)
            msg['To'] = ', '.join(recipients['to'])
            if recipients.get('cc'):
                msg['Cc'] = ', '.join(recipients['cc'])
            
            msg['Subject'] = f"Report DIGIL - {vendor} - {date_formatted} - Device {device_id}"
            
            # Carica template HTML
            if getattr(sys, 'frozen', False):
                base_path = Path(sys.executable).parent
                template_path = base_path / '_internal' / 'templates' / 'email_template.html'
                if not template_path.exists():
                    template_path = Path(sys._MEIPASS) / 'templates' / 'email_template.html'
            else:
                template_path = Path('templates/email_template.html')
            
            with open(template_path, 'r', encoding='utf-8') as f:
                template = Template(f.read())
            
            html_body = template.render(
                vendor=vendor,
                device_id=device_id,
                date_formatted=date_formatted,
                send_datetime=datetime.now().strftime('%d/%m/%Y %H:%M'),
                filename=os.path.basename(zip_path)
            )
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Allega il file ZIP
            with open(zip_path, 'rb') as attachment:
                part = MIMEBase('application', 'zip')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={os.path.basename(zip_path)}'
                )
                msg.attach(part)
            
            # Invia email
            all_recipients = recipients['to'] + recipients.get('cc', [])
            
            print(f"📧 Connessione a {config['server']}...")
            server = smtplib.SMTP(config['server'], config['port'])
            if config['use_tls']:
                server.starttls()
            
            print(f"📧 Autenticazione come {config['username']}...")
            server.login(config['username'], config['password'])
            
            print(f"📧 Invio a: {', '.join(all_recipients)}")
            server.send_message(msg)
            server.quit()
            
            return True, f"Email inviata con successo a: {', '.join(all_recipients)}"
            
        except Exception as e:
            return False, f"Errore invio email: {str(e)}"
    
    def send_report_email(self, zip_path, vendor, device_id, date_formatted, send_to_custom=None):
        """Metodo principale che sceglie il metodo di invio migliore"""
        try:
            # Se c'è Outlook COM disponibile, usalo
            if self.active_provider == 'outlook_com':
                return self.send_via_outlook_com(zip_path, vendor, device_id, date_formatted)
            else:
                # Altrimenti usa SMTP (Gmail o Outlook web)
                config = self.smtp_config[self.active_provider]
                
                if not config['password']:
                    raise Exception(f"Password non configurata per {self.active_provider}. Configura il file .env")
                
                return self.send_via_smtp(zip_path, vendor, device_id, date_formatted, config)
                
        except Exception as e:
            return False, f"Errore invio email: {str(e)}"
    
    def test_connection(self):
        """Testa la connessione email"""
        try:
            if self.active_provider == 'outlook_com':
                if self.check_outlook_com():
                    return True, "Outlook COM disponibile e funzionante"
                else:
                    return False, "Outlook COM non disponibile"
            else:
                config = self.smtp_config[self.active_provider]
                
                if not config['password']:
                    return False, "Password non configurata"
                
                server = smtplib.SMTP(config['server'], config['port'])
                if config['use_tls']:
                    server.starttls()
                server.login(config['username'], config['password'])
                server.quit()
                
                return True, f"Connessione a {self.active_provider} riuscita"
        except Exception as e:
            return False, f"Errore connessione: {str(e)}"

# Istanza singleton del servizio email
email_service = EmailService()

# Test connessione all'avvio (opzionale)
if __name__ == "__main__":
    success, message = email_service.test_connection()
    print(f"Test connessione: {message}")