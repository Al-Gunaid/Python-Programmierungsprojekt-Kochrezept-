# Kochrezept
# Telemedizinischer Terminplaner

## Installation

1) **Python installieren**
   - Laden Sie Python von [python.org](https://www.python.org/downloads/) herunter und installieren Sie es.

2) **Abhängigkeiten installieren**
   - Öffnen Sie ein Terminal oder eine Eingabeaufforderung im Verzeichnis des Projekts und führen Sie den folgenden Befehl aus:
   ```bash
   pip install -r requirements.txt
   ```

3) **Projekt starten**
   - Nach der Installation der Abhängigkeiten starten Sie die Anwendung mit:
   ```bash
   python Projekt_code.py
   ```

## Informationen

Dieses System wurde mit **Python** entwickelt. Folgende Bibliotheken und Tools wurden verwendet:

1) **Tkinter**: Für die grafische Benutzeroberfläche (GUI).
2) **sqlite3**: Für die Verwaltung der lokalen Datenbank.
3) **tkcalendar**: Für die Kalenderauswahl.
4) **smtplib**: Für den Versand von E-Mail-Benachrichtigungen.

### Hauptfunktionen

- **Benutzerregistrierung und -anmeldung**:
  - Benutzer können sich registrieren und mit einem Benutzernamen und Passwort anmelden.
  - Zwei Rollen: Patienten und Ärzte.

- **Terminverwaltung**:
  - Termine können über eine Kalenderansicht gebucht werden, jedoch (nur durch Arzt_User) verschoben und storniert werden.
  - Automatische Berechnung verfügbarer Zeitfenster für jeden Tag.

- **Benachrichtigungen**:
  - Erinnerungen an Termine werden per E-Mail verschickt.

- **Datenbankintegration**:
  - Alle Benutzerdaten und Termine werden in einer SQLite-Datenbank gespeichert.

###################################################### Hinweise##################################################

- Stellen Sie sicher, dass die E-Mail-Konfiguration korrekt eingerichtet ist, bevor Sie Benachrichtigungen senden.
- E-Mail-Konfiguration muss über Gmail (Absender) erfolgen. dafür muss eine Authentifizierung für den SMTP-Dienst aktiviert werden.


-----------------------------------------------------------------------------E-Mail-Konfiguration für Gmail----------------------------------------------------------

beachten Sie die folgenden Schritte, um die Authentifizierung für den SMTP-Dienst zu aktivieren:

1. Google-Konto einrichten :

Melden Sie sich bei Ihrem Google-Konto an und führen Sie zu Konto > Sicherheit durch .

2. Zwei-Faktor-Authentifizierung aktivieren :

Falls noch nicht geschehen, aktivieren Sie die Zwei-Faktor-Authentifizierung.

3. App-Passwort erstellen :

Gehen Sie zu Sicherheit > App-Passwörter .
Wählen Sie die Option „E-Mail“ und „Computer“ aus und generieren Sie ein App-Passwort.
<<<<Notieren Sie sich das generierte Passwort>>>>.

4. Konfiguration im Projekt :

Verwenden Sie das App-Passwort anstelle Ihres regulären Gmail-Passworts in der Anwendung.


Mit diesen Einstellungen können Sie E-Mails sicher und problemlos über Gmail versenden.
