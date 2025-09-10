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

# Carica le variabili d'ambiente
load_dotenv()

class EmailService:
    def __init__(self):
        # Configurazione SMTP dalle variabili d'ambiente
        self.smtp_config = {
            'gmail': {
                'server': 'smtp.gmail.com',
                'port': 587,
                'use_tls': True,
                'username': os.getenv('GMAIL_USER', 'max.tvn89@gmail.com'),
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
        
        # Provider attivo (può essere cambiato tramite env o default)
        self.active_provider = os.getenv('EMAIL_PROVIDER', 'gmail')
        
        # Carica configurazione destinatari
        self.load_recipients_config()
        
        # Verifica configurazione all'avvio
        self.check_configuration()
    
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
        config_path = Path('config/email_recipients.json')
        
        # Se non esiste, crea il file con configurazione di default
        if not config_path.exists():
            config_path.parent.mkdir(exist_ok=True)
            default_config = {
                "MII": {
                    "to": ["m.tavernese@reply.it"],
                    "cc": []
                },
                "Indra/Olivetti": {
                    "to": ["m.tavernese@reply.it"],
                    "cc": []
                },
                "Sirtiv2": {
                    "to": ["m.tavernese@reply.it"],
                    "cc": []
                },
                "default": {
                    "to": ["m.tavernese@reply.it"],
                    "cc": []
                }
            }
            
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"📁 Creato file di configurazione destinatari: {config_path}")
        
        # Carica la configurazione
        try:
            with open(config_path, 'r') as f:
                self.recipients_config = json.load(f)
            print(f"📧 Caricata configurazione destinatari da {config_path}")
        except Exception as e:
            print(f"❌ Errore caricamento configurazione destinatari: {e}")
            self.recipients_config = {"default": {"to": ["m.tavernese@reply.it"], "cc": []}}
    
    def get_recipients(self, vendor):
        """Ottiene i destinatari per un vendor specifico"""
        # Pulisce il nome del vendor per la ricerca
        vendor_clean = vendor.replace('/', '-').replace('\\', '-')
        
        # Cerca prima il vendor specifico, poi il default
        for key in [vendor, vendor_clean, 'default']:
            if key in self.recipients_config:
                return self.recipients_config[key]
        
        return {'to': [], 'cc': []}
    
    def test_connection(self):
        """Testa la connessione SMTP"""
        try:
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
    


    def send_report_email(self, zip_path, vendor, device_id, date_formatted, send_to_custom=None):
        """Invia il report via email"""
        try:
            # Ottieni configurazione SMTP
            config = self.smtp_config[self.active_provider]
    
            # Verifica password
            if not config['password']:
                raise Exception(f"Password non configurata per {self.active_provider}. Configura il file .env")
    
            # Ottieni destinatari
            if send_to_custom:
                recipients = send_to_custom
            else:
                recipients = self.get_recipients(vendor)
    
            if not recipients.get('to'):
                raise Exception("Nessun destinatario configurato per questo vendor")
    
            # Crea messaggio
            msg = MIMEMultipart()
            msg['From'] = config['username']
            msg['To'] = ', '.join(recipients['to'])
            if recipients.get('cc'):
                msg['Cc'] = ', '.join(recipients['cc'])
    
            # Oggetto email
            msg['Subject'] = f"Report DIGIL - {vendor} - {date_formatted} - Device {device_id}"
    
            # Carica e renderizza il template HTML
            template_path = Path('templates/email_template.html')
    
            # Se l'app è compilata con PyInstaller
            if getattr(sys, 'frozen', False):
                # RIMOSSO: import sys (già importato all'inizio del file)
                template_path = Path(sys._MEIPASS) / 'templates' / 'email_template.html'
    
            with open(template_path, 'r', encoding='utf-8') as f:
                template = Template(f.read())
    
            # Renderizza il template con i dati
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
    
        except smtplib.SMTPAuthenticationError:
            return False, f"Errore autenticazione {self.active_provider}. Verifica username e password nel file .env"
        except smtplib.SMTPException as smtp_error:
            return False, f"Errore SMTP: {str(smtp_error)}"
        except Exception as e:
            return False, f"Errore invio email: {str(e)}"

# Istanza singleton del servizio email
email_service = EmailService()

# Test connessione all'avvio (opzionale)
if __name__ == "__main__":
    success, message = email_service.test_connection()
    print(f"Test connessione: {message}")