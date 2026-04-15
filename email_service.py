import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import os
import sys
import json
import platform
import subprocess
import tempfile
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
        self.is_mac = platform.system() == 'Darwin'
        self.is_windows = platform.system() == 'Windows'

        if self.is_windows:
            # Windows: usa Outlook COM
            if self.check_outlook_com():
                self.active_provider = 'outlook_com'
                print("✅ Outlook COM disponibile - sarà usato per l'invio email")
            else:
                self.active_provider = None
                print("⚠️ ATTENZIONE: Outlook COM non disponibile - invio email disabilitato")
                print("   Per abilitare l'invio email, installare e configurare Outlook")
        elif self.is_mac:
            # Mac: usa Outlook via AppleScript
            if self.check_outlook_mac():
                self.active_provider = 'outlook_mac'
                print("✅ Outlook for Mac disponibile - sarà usato per l'invio email")
            else:
                self.active_provider = None
                print("⚠️ ATTENZIONE: Outlook for Mac non trovato - invio email disabilitato")
        else:
            self.active_provider = None
            print("⚠️ ATTENZIONE: Sistema operativo non supportato per l'invio email")

        # Carica configurazione destinatari
        self.load_recipients_config()

    def check_outlook_com(self):
        """Verifica se Outlook COM API è disponibile (Windows)"""
        try:
            import win32com.client
            outlook = win32com.client.Dispatch('outlook.application')
            return True
        except:
            return False

    def check_outlook_mac(self):
        """Verifica se Outlook for Mac è installato (Mac)"""
        try:
            result = subprocess.run(
                ['mdfind', 'kMDItemCFBundleIdentifier == "com.microsoft.Outlook"'],
                capture_output=True, text=True, timeout=5
            )
            return bool(result.stdout.strip())
        except:
            return False

    def load_recipients_config(self):
        """Carica la configurazione dei destinatari dal file JSON"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
            config_path = base_path / '_internal' / 'config' / 'email_recipients.json'
            if not config_path.exists():
                config_path = base_path / 'config' / 'email_recipients.json'
        else:
            config_path = Path('config/email_recipients.json')

        # Configurazione di default se il file non esiste
        if not config_path.exists():
            config_path.parent.mkdir(exist_ok=True, parents=True)
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

        try:
            with open(config_path, 'r') as f:
                self.recipients_config = json.load(f)
            print(f"📧 Caricata configurazione destinatari da {config_path}")
        except Exception as e:
            print(f"❌ Errore caricamento configurazione destinatari: {e}")
            self.recipients_config = {"default": {"to": ["m.tavernese@reply.it"], "cc": []}}

    def get_recipients(self, vendor):
        """Ottiene i destinatari per un vendor specifico"""
        vendor_clean = vendor.replace('/', '-').replace('\\', '-')

        for key in [vendor, vendor_clean, 'default']:
            if key in self.recipients_config:
                return self.recipients_config[key]

        return {'to': ['m.tavernese@reply.it'], 'cc': []}

    def _render_html_body(self, vendor, device_id, date_formatted, zip_path, collaudo_scorte):
        """Carica e renderizza il template HTML email"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
            template_path = base_path / '_internal' / 'templates' / 'email_template.html'
            if not template_path.exists():
                template_path = Path(sys._MEIPASS) / 'templates' / 'email_template.html'
        else:
            template_path = Path('templates/email_template.html')

        with open(template_path, 'r', encoding='utf-8') as f:
            template = Template(f.read())

        scorte_label = "Scorte " if collaudo_scorte else ""
        return template.render(
            vendor=vendor,
            device_id=device_id,
            date_formatted=date_formatted,
            send_datetime=datetime.now().strftime('%d/%m/%Y %H:%M'),
            filename=os.path.basename(zip_path),
            scorte_label=scorte_label
        )

    def send_via_outlook_com(self, zip_path, vendor, device_id, date_formatted, send_to_custom=None, collaudo_scorte=False):
        """Invia email usando Outlook COM API (Windows only)"""
        try:
            import win32com.client
            import pythoncom

            print("📧 Invio tramite Outlook COM...")

            # Inizializza COM per questo thread
            pythoncom.CoInitialize()

            try:
                # Connetti a Outlook
                outlook = win32com.client.Dispatch('outlook.application')
                mail = outlook.CreateItem(0)  # 0 = olMailItem

                # GESTIONE EMAIL PERSONALIZZATA
                if send_to_custom and send_to_custom.strip():
                    recipients = {'to': [send_to_custom.strip()], 'cc': []}
                    print(f"📧 Uso email personalizzata: {send_to_custom}")
                else:
                    recipients = self.get_recipients(vendor)
                    print(f"📧 Uso destinatari standard per vendor: {vendor}")

                # Configura email
                mail.To = '; '.join(recipients['to'])
                if recipients.get('cc'):
                    mail.CC = '; '.join(recipients['cc'])

                scorte_label = "Scorte " if collaudo_scorte else ""
                mail.Subject = f"Report {scorte_label}DIGIL - {vendor} - {date_formatted} - Device {device_id}"
                mail.HTMLBody = self._render_html_body(vendor, device_id, date_formatted, zip_path, collaudo_scorte)

                # Converti il percorso in assoluto
                absolute_path = os.path.abspath(zip_path)
                print(f"📎 Allegato: {absolute_path}")

                if not os.path.exists(absolute_path):
                    raise FileNotFoundError(f"File non trovato: {absolute_path}")

                mail.Attachments.Add(absolute_path)
                mail.Send()

                if send_to_custom:
                    return True, f"Email inviata con successo tramite Outlook a: {send_to_custom}"
                else:
                    all_recipients = recipients['to'] + recipients.get('cc', [])
                    return True, f"Email inviata con successo tramite Outlook a: {', '.join(all_recipients)}"

            finally:
                pythoncom.CoUninitialize()

        except ImportError:
            return False, "Libreria pywin32 non installata. Esegui: pip install pywin32"
        except FileNotFoundError as e:
            return False, f"File allegato non trovato: {str(e)}"
        except Exception as e:
            return False, f"Errore invio tramite Outlook COM: {str(e)}"

    def send_via_outlook_mac(self, zip_path, vendor, device_id, date_formatted, send_to_custom=None, collaudo_scorte=False):
        """Invia email usando Outlook for Mac via AppleScript"""
        html_temp_path = None
        script_temp_path = None
        try:
            print("📧 Invio tramite Outlook for Mac (AppleScript)...")

            # Gestione destinatari
            if send_to_custom and send_to_custom.strip():
                recipients = {'to': [send_to_custom.strip()], 'cc': []}
                print(f"📧 Uso email personalizzata: {send_to_custom}")
            else:
                recipients = self.get_recipients(vendor)
                print(f"📧 Uso destinatari standard per vendor: {vendor}")

            scorte_label = "Scorte " if collaudo_scorte else ""
            subject = f"Report {scorte_label}DIGIL - {vendor} - {date_formatted} - Device {device_id}"
            subject_escaped = subject.replace('\\', '\\\\').replace('"', '\\"')

            # Scrivi HTML su file temporaneo (evita problemi di escape in AppleScript)
            html_body = self._render_html_body(vendor, device_id, date_formatted, zip_path, collaudo_scorte)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                html_temp_path = f.name
                f.write(html_body)

            absolute_zip_path = os.path.abspath(zip_path)
            print(f"📎 Allegato: {absolute_zip_path}")

            if not os.path.exists(absolute_zip_path):
                raise FileNotFoundError(f"File non trovato: {absolute_zip_path}")

            # Costruisci i blocchi destinatari To e CC
            # Usiamo i raw Apple Event codes per evitare problemi con proprietà multi-parola:
            #   «class emad» = email address (record-type)
            #   «class radd» = address (campo del record)
            to_lines = []
            for i, addr in enumerate(recipients['to']):
                to_lines.append(f'    set toRec{i} to make new to recipient at newMessage with properties {{«class emad»:{{«class radd»:"{addr}"}}}}')

            cc_lines = []
            for i, addr in enumerate(recipients.get('cc', [])):
                cc_lines.append(f'    set ccRec{i} to make new cc recipient at newMessage with properties {{«class emad»:{{«class radd»:"{addr}"}}}}')

            recipient_block = '\n'.join(to_lines + cc_lines)

            # Script AppleScript
            # NOTA: la proprietà HTML in Outlook Mac si chiama "content" (codice ctnt), NON "html content"
            applescript = f'''tell application "Microsoft Outlook"
    set htmlContent to do shell script "cat " & quoted form of "{html_temp_path}"
    set newMessage to make new outgoing message with properties {{subject:"{subject_escaped}", content:htmlContent}}
{recipient_block}
    make new attachment at newMessage with properties {{file:(POSIX file "{absolute_zip_path}")}}
    send newMessage
end tell
'''

            # DEBUG: stampa lo script generato per diagnostica
            print("--- DEBUG AppleScript generato ---")
            for i, line in enumerate(applescript.split('\n'), 1):
                print(f"  {i}: {line}")
            print(f"--- Lunghezza totale: {len(applescript)} chars ---")

            # Scrivi lo script su file temporaneo ed eseguilo
            with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', delete=False) as f:
                script_temp_path = f.name
                f.write(applescript)

            result = subprocess.run(
                ['osascript', script_temp_path],
                capture_output=True, text=True, timeout=60
            )

            if result.returncode == 0:
                all_recipients = recipients['to'] + recipients.get('cc', [])
                return True, f"Email inviata con successo tramite Outlook a: {', '.join(all_recipients)}"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"Errore AppleScript Outlook: {error_msg}"

        except FileNotFoundError as e:
            return False, f"File allegato non trovato: {str(e)}"
        except subprocess.TimeoutExpired:
            return False, "Timeout: Outlook non ha risposto entro 60 secondi"
        except Exception as e:
            return False, f"Errore invio tramite Outlook Mac: {str(e)}"
        finally:
            # Pulizia file temporanei
            for p in [html_temp_path, script_temp_path]:
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except:
                        pass

    def send_report_email(self, zip_path, vendor, device_id, date_formatted, send_to_custom=None, collaudo_scorte=False):
        """Metodo principale per l'invio email"""
        try:
            if self.active_provider == 'outlook_com':
                return self.send_via_outlook_com(zip_path, vendor, device_id, date_formatted, send_to_custom, collaudo_scorte)
            elif self.active_provider == 'outlook_mac':
                return self.send_via_outlook_mac(zip_path, vendor, device_id, date_formatted, send_to_custom, collaudo_scorte)
            else:
                return False, "Invio email disabilitato: Outlook non disponibile."
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
            elif self.active_provider == 'outlook_mac':
                if self.check_outlook_mac():
                    return True, "Outlook for Mac disponibile e funzionante"
                else:
                    return False, "Outlook for Mac non trovato"
            else:
                return False, "Nessun provider email configurato - Outlook richiesto per l'invio email"
        except Exception as e:
            return False, f"Errore connessione: {str(e)}"


# Istanza singleton del servizio email
email_service = EmailService()

# Test connessione all'avvio (opzionale)
if __name__ == "__main__":
    success, message = email_service.test_connection()
    print(f"Test connessione: {message}")
