# Import der benötigten Bibliotheken
import sqlite3
import logging
import smtplib
from tkinter import *
from tkinter import messagebox
from tkcalendar import DateEntry
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

# ------------------------- Logging-Konfiguration -------------------------
# Konfiguration des Logging-Moduls
logging.basicConfig(
    level=logging.INFO, # Standard-Log-Level
    format="%(asctime)s - %(levelname)s - %(message)s", # Format für die Log-Einträge: Zeitstempel, Level und Nachricht
    filename="telemedicine.log", # Datei, in die geloggt wird
    filemode="a", # Append-Modus
)

# ------------------------- Interfaces -------------------------
# Definition von abstrakten Basisklassen (Interfaces), die sicherstellen, dass jede Klasse, die diese erbt, bestimmte Methoden implementiert.
class NotificationService(ABC):
    @abstractmethod
    def send(self, recipient, subject, message):
        pass

class DatabaseReader(ABC):
    @abstractmethod
    def fetch_query(self, query, params=()):
        pass

class DatabaseWriter(ABC):
    @abstractmethod
    def execute_query(self, query, params=()):
        pass

# ------------------------- Implementierungen -------------------------
class DatabaseManager(DatabaseReader, DatabaseWriter):
    """
    Eine Klasse zur Verwaltung einer SQLite-Datenbank, die für ein Telemedizin-System verwendet wird.

    Attribute:
        conn: Die Verbindung zur SQLite-Datenbank.
        cursor: Ein Cursor-Objekt für die Ausführung von SQL-Befehlen.
    """
    def __init__(self, db_name="telemedicine.db"):
        """
        Konstruktor, der die Verbindung zur SQLite-Datenbank herstellt und die Tabellen initialisiert.
        Args:
            db_name (str): Der Pfad und Name der SQLite-Datenbankdatei.
        """
        self.conn = sqlite3.connect(db_name)    # Verbindung zur SQLite-Datenbank herstellen
        self.cursor = self.conn.cursor() # Cursor-Objekt erstellen
        self._initialize_tables() # Tabellen initialisieren, falls sie nicht existieren

    def _initialize_tables(self):
        """
        Interne Methode zum Erstellen der notwendigen Tabellen, falls sie nicht existieren.
        """
        # Tabelle für Benutzer erstellen
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """)
        # Tabelle für Termine erstellen
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            app_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            phone TEXT,
            email TEXT,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            doctor TEXT
        )
        """)

        self.conn.commit()  # Änderungen in der Datenbank speichern

    def execute_query(self, query, params=()):
        """
        Führt eine SQL-Anweisung aus, die keine Daten zurückgibt (z.B. INSERT, UPDATE, DELETE).

        Args:
            query (str): Die SQL-Abfrage, die ausgeführt werden soll.
            params (tuple): Optionale Parameter für die SQL-Abfrage.
        """
        self.cursor.execute(query, params)
        self.conn.commit()

    def fetch_query(self, query, params=()):
        """
        Führt eine SQL-Abfrage aus und gibt die Ergebnisse zurück.

        Args:
            query (str): Die SQL-Abfrage, die ausgeführt werden soll.
            params (tuple): Optionale Parameter für die SQL-Abfrage.

        Returns:
            list: Eine Liste mit den Ergebnissen der Abfrage.

        """
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def close(self):
        """
        Schließt die Verbindung zur Datenbank.
        """
        self.conn.close()

# --------------------------- Email Notification ---------------------------
# Diese Klasse implementiert die NotificationService-Schnittstelle und bietet Funktionen zum Senden von E-Mails über einen SMTP-Server.
class EmailNotification(NotificationService):
    """
    Implementierung des NotificationService für das Versenden von E-Mails.

    Attribute:
        smtp_server (str): Die Adresse des SMTP-Servers von Gmail.
        smtp_port (int): Der Port des SMTP-Servers von Gmail (Standard: 587 für TLS).
        email (str): Die E-Mail-Adresse des Absenders.
        password (str): Das Passwort der E-Mail-Adresse.
    """
    def __init__(self, smtp_server="smtp.gmail.com", smtp_port=587):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email = None
        self.password = None

    def set_credentials(self, email, password):
        self.email = email
        self.password = password

    def send(self, recipient, subject, message):
        """
        Sendet eine E-Mail an den angegebenen Empfänger.

        Args:
            recipient (str): Die E-Mail-Adresse des Empfängers.
            subject (str): Der Betreff der E-Mail.
            message (str): Der Inhalt der E-Mail.

        Raises:
            ValueError: Wenn die E-Mail-Anmeldedaten nicht gesetzt wurden.
            Exception: Bei Fehlern während des Versands wird die Ausnahme erneut ausgelöst.
        """
        if not self.email or not self.password:
            raise ValueError("Email credentials are not set.")
            
        try:
            msg = MIMEText(message)
            msg["Subject"] = subject
            msg["From"] = self.email
            msg["To"] = recipient

        
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email, self.password)
                server.send_message(msg)
                logging.info(f"Email sent to {recipient}")
        except Exception as e:
            logging.error(f"Failed to send email: {e}")
            raise

# ------------------------- Appointment Manager -------------------------
class AppointmentManager:
    """
    Diese Klasse zur Verwaltung von Terminen in einem Telemedizin-System.
    sie bietet Methoden zum Erstellen, Abrufen, Aktualisieren und Löschen von Terminen.
    Sie berechnet außerdem verfügbare Zeitfenster basierend auf bestehenden Terminen.
    Attribute:
        db_reader (DatabaseReader): Objekt, das für das Abrufen von Daten aus der Datenbank verwendet wird.
        db_writer (DatabaseWriter): Objekt, das für das Schreiben von Daten in die Datenbank verwendet wird.
    """
    def __init__(self, db_reader: DatabaseReader, db_writer: DatabaseWriter):
        """
        Initialisiert den AppointmentManager mit Datenbankzugriffsobjekten.

        Args:
            db_reader (DatabaseReader): Objekt zum Abrufen von Daten.
            db_writer (DatabaseWriter): Objekt zum Schreiben von Daten.
        """
        self.db_reader = db_reader
        self.db_writer = db_writer

    def create_appointment(self, patient_name, phone, email, date, start_time, end_time, doctor):
        """
        Erstellt einen neuen Termin und speichert ihn in der Datenbank.

        Args:
            patient_name (str): Der Name des Patienten.
            phone (str): Die Telefonnummer des Patienten.
            email (str): Die E-Mail-Adresse des Patienten.
            date (str): Das Datum des Termins (im Format YYYY-MM-DD).
            start_time (str): Die Startzeit des Termins (im Format HH:MM).
            end_time (str): Die Endzeit des Termins (im Format HH:MM).
            doctor (str): Der Name des zugewiesenen Arztes.
        """
        # Termin erstellen, die in der Datenbank eingefügt wird
        self.db_writer.execute_query(
            """
            INSERT INTO appointments (patient_name, phone, email, date, start_time, end_time, doctor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_name, phone, email, date, start_time, end_time, doctor),
        )

    def get_appointments(self):
        """
        Ruft alle Termine aus der Datenbank ab.

        Returns:
            list: Eine Liste mit allen Terminen.
        """
        return self.db_reader.fetch_query("SELECT * FROM appointments")

    def delete_appointment(self, app_id):
        """
        Löscht einen Termin anhand seiner ID.

        Args:
            app_id (int): Die ID des Termins, der gelöscht werden soll.
        """
        self.db_writer.execute_query("DELETE FROM appointments WHERE app_id = ?", (app_id,))

    def update_appointment(self, app_id, new_date, new_start_time, new_end_time):
        """
        Aktualisiert die Details eines bestehenden Termins.

        Args:
            app_id (int): Die ID des Termins, der aktualisiert werden soll.
            new_date (str): Das neue Datum des Termins (im Format YYYY-MM-DD).
            new_start_time (str): Die neue Startzeit des Termins (im Format HH:MM).
            new_end_time (str): Die neue Endzeit des Termins (im Format HH:MM).
        """
        self.db_writer.execute_query(
            """
            UPDATE appointments
            SET date = ?, start_time = ?, end_time = ?
            WHERE app_id = ?
            """,
            (new_date, new_start_time, new_end_time, app_id),
        )

    def get_available_slots(self, date):
        """
        Berechnet die verfügbaren Zeitfenster für ein bestimmtes Datum.
        Args:
            date (str): Das Datum, für das die verfügbaren Zeitfenster berechnet werden sollen (im Format YYYY-MM-DD).
        Returns:
            list: Eine Liste von verfügbaren Zeitfenstern als Tupel (Startzeit, Endzeit).
        """
        working_hours = [("08:00", "16:00")]    # Arbeitszeiten: 08:00 bis 16:00 Uhr
        appointments = self.db_reader.fetch_query(
            "SELECT start_time, end_time FROM appointments WHERE date = ?", (date,)
        )

        # Konvertiere bestehende Termine in Zeitfenster
        booked_slots = [
            (datetime.strptime(start, "%H:%M"), datetime.strptime(end, "%H:%M"))
            for start, end in appointments
        ]

        available_slots = []    # Liste der verfügbaren Zeitfenster
        current_time = datetime.strptime(working_hours[0][0], "%H:%M")
        end_of_day = datetime.strptime(working_hours[0][1], "%H:%M")
       
        # Berechne verfügbare Zeitfenster
        while current_time + timedelta(minutes=30) <= end_of_day:
            
            slot_end = current_time + timedelta(minutes=30)
           
            # Überprüfe, ob das Zeitfenster nicht mit bestehenden Terminen kollidiert
           
            if all(not (start < slot_end and current_time < end) for start, end in booked_slots):
               
                available_slots.append((current_time.strftime("%H:%M"), slot_end.strftime("%H:%M")))
          
            current_time = slot_end

        return available_slots

# ------------------------- GUI -------------------------
class TelemedicineApp:
    """
    GUI-Anwendung für die Telemedizin, die Benutzern die Verwaltung von Terminen ermöglicht.

    Funktionen:
        - Login und Registrierung von Benutzern.
        - Terminbuchung, -anzeige, -aktualisierung und -löschung.
        - Konfiguration von E-Mail-Benachrichtigungen.
        - Arzt- und Patientenfunktionen basierend auf Benutzerrollen.
    """

    def __init__(self, db_manager: DatabaseManager, notification_service: NotificationService ):
        """
        Initialisiert die Anwendung mit Datenbank- und Benachrichtigungsdiensten.

        Args:
            db_manager (DatabaseManager): Instanz zur Verwaltung der Datenbankoperationen.
            notification_service (NotificationService): Instanz für das Versenden von Benachrichtigungen.
        """
        self.db_manager = db_manager
        self.notification_service = notification_service
        self.appointment_manager = AppointmentManager(db_reader=db_manager, db_writer=db_manager)
        
        # GUI-Fenster einrichten
        self.root = Tk()
        self.root.title("Telemedizin Terminplaner")
        self.root.geometry("800x600")
        self.current_user = None    # Speichert die Informationen des angemeldeten Benutzers
        self.setup_login_screen()   # Zeigt den Login-Bildschirm beim Start an


    def setup_login_screen(self):
        """
        Zeigt den Login-Bildschirm an, auf dem Benutzer sich anmelden oder registrieren können.
        """
        # Alle vorherigen Widgets entfernen
        for widget in self.root.winfo_children():
            widget.destroy()

        Label(self.root, text="Login", font=("Arial", 24)).pack(pady=20)

        # Eingabefelder für Benutzername und Passwort
        Label(self.root, text="Benutzername:").pack(pady=5)
        username_entry = Entry(self.root)
        username_entry.pack()

        Label(self.root, text="Passwort:").pack(pady=5)
        password_entry = Entry(self.root, show="*")
        password_entry.pack()

        def login():
            """
            Überprüft die Benutzeranmeldeinformationen und leitet den Benutzer weiter, wenn die Anmeldung erfolgreich ist.
            """
            username = username_entry.get()
            password = password_entry.get()
            user = self.db_manager.fetch_query(
                "SELECT * FROM users WHERE username = ? AND password = ?", (username, password)
            )
            if user:
                self.current_user = user[0]
                self.current_role = self.current_user[4]
                logging.info(f"Benutzer {username} hat sich erfolgreich angemeldet.")
                self.setup_home_screen()    # Zur Startseite weiterleiten
            else:
                messagebox.showerror("Fehler", "Ungültiger Benutzername oder Passwort")
                logging.warning(f"Anmeldeversuch fehlgeschlagen für Benutzer: {username}")
        
        def register():
            """
            Öffnet die Registrierungsoberfläche für neue Benutzer.
            
            """
            self.setup_register_screen()

        # Buttons für Login und Registrierung
        Button(self.root, text="Anmelden", command=login).pack(pady=10)
        Button(self.root, text="Registrieren", command=register).pack(pady=5)

    def setup_register_screen(self):
        """
        Zeigt die Benutzeroberfläche für die Benutzerregistrierung an.
        
        """
        for widget in self.root.winfo_children():
            widget.destroy()

        Label(self.root, text="Registrieren", font=("Arial", 24)).pack(pady=20)

        Label(self.root, text="Name:").pack(pady=5)
        name_entry = Entry(self.root)
        name_entry.pack()

        Label(self.root, text="Benutzername:").pack(pady=5)
        username_entry = Entry(self.root)
        username_entry.pack()

        Label(self.root, text="Passwort:").pack(pady=5)
        password_entry = Entry(self.root, show="*")
        password_entry.pack()

        Label(self.root, text="Rolle (z.B. Arzt/Patient):").pack(pady=5)
        role_entry = Entry(self.root)
        role_entry.pack()

        def register_user():
            """
            Speichert die neuen Benutzerdaten in der Datenbank.
            
            """
            name = name_entry.get()
            username = username_entry.get()
            password = password_entry.get()
            role = role_entry.get()
            try:
                self.db_manager.execute_query(
                    "INSERT INTO users (name, username, password, role) VALUES (?, ?, ?, ?)",
                    (name, username, password, role),
                )
                messagebox.showinfo("Erfolg", "Benutzer erfolgreich registriert!")
                self.setup_login_screen()   # Nach erfolgreicher Registrierung zurück zum Login-Bildschirm
            except sqlite3.IntegrityError:
                messagebox.showerror("Fehler", "Benutzername existiert bereits!")
        
        # Buttons für Registrierung und Rückkehr zum Login-Bildschirm
        Button(self.root, text="Registrieren", command=register_user).pack(pady=10)
        Button(self.root, text="Zurück", command=self.setup_login_screen).pack(pady=5)

    def setup_home_screen(self):
        """
        Zeigt die Startseite an, nachdem sich ein Benutzer erfolgreich angemeldet hat.
        Der Inhalt variiert basierend auf der Benutzerrolle (z.B. Arzt oder Patient).
        
        """
        for widget in self.root.winfo_children():
            widget.destroy()

        # Startseite erstellen
        Label(self.root, text=f"Willkommen, {self.current_user[1]}", font=("Arial", 24)).pack(pady=20)

        # Gemeinsame Funktionen für Arzt-und Patient_Users
        Button(self.root, text="Termin buchen", command=self.setup_appointment_booking).pack(pady=10)

        if self.current_role == "Arzt":
            # Zusätzliche Funktionen für Arzt_User
            Button(self.root, text="Termine anzeigen", command=self.show_appointments).pack(pady=10)
            Button(self.root, text="E-Mail-Einstellungen", command=self.setup_email_settings).pack(pady=20)
       
        # Abmelden-Button
        Button(self.root, text="Abmelden", command=self.setup_login_screen).pack(pady=10)

    def setup_appointment_booking(self):
        """
        Erstellt die Benutzeroberfläche für die Terminbuchung.
        Benutzer können ihre Daten eingeben, einen Arzt auswählen und eine verfügbare Zeit buchen.
       
        """
        for widget in self.root.winfo_children():
            widget.destroy()

        Label(self.root, text="Termin buchen", font=("Arial", 24)).pack(pady=20)

        # Eingabefelder für die Patientendaten
        Label(self.root, text="Patientenname:").pack(pady=5)
        patient_name_entry = Entry(self.root)
        patient_name_entry.pack()

        Label(self.root, text="Telefon:").pack(pady=5)
        phone_entry = Entry(self.root)
        phone_entry.pack()

        Label(self.root, text="Email:").pack(pady=5)
        email_entry = Entry(self.root)
        email_entry.pack()

        # Eingabefeld für das Datum (Kalenderauswahl)
        Label(self.root, text="Datum:").pack(pady=5)
        date_entry = DateEntry(self.root)
        date_entry.pack()

        Label(self.root, text="Arzt:").pack(pady=5)
        doctor_entry = Entry(self.root)
        doctor_entry.pack()

        # Dropdown-Menü für verfügbare Zeiten
        available_slots_var = StringVar()
        available_slots_menu = OptionMenu(self.root, available_slots_var, "")
        available_slots_menu.pack(pady=5)

        def load_available_slots():
            """
            Lädt die verfügbaren Zeiten für das gewählte Datum und den Arzt.
            Aktualisiert das Dropdown-Menü mit diesen Zeiten.
            """
            date = date_entry.get() # Datum aus der Eingabe abrufen
            slots = self.appointment_manager.get_available_slots(date)  # Verfügbare Zeiten abrufen
            
            # Dropdown-Menü zurücksetzen und neu füllen
            available_slots_var.set("")
            available_slots_menu["menu"].delete(0, "end")
            for slot in slots:
                available_slots_menu["menu"].add_command(
                    label=f"{slot[0]} - {slot[1]}",
                    command=lambda s=slot: available_slots_var.set(f"{s[0]} - {s[1]}")
                )

        # Button, um verfügbare Zeiten zu laden
        Button(self.root, text="Verfügbare Zeiten laden", command=load_available_slots).pack(pady=10)

        def book():
            """
            Speichert die Buchung, nachdem ein Zeitfenster ausgewählt wurde.
            Zeigt bei Fehlern eine entsprechende Meldung an
            """
            if not available_slots_var.get():
                # Fehlermeldung, falls kein Zeitfenster ausgewählt wurde
                messagebox.showerror("Fehler", "Bitte wählen Sie eine verfügbare Zeit aus!")
                return
            
            # Start- und Endzeit aus dem Dropdown-Wert extrahieren
            start_time, end_time = available_slots_var.get().split(" - ")
            try:
                # Termin in der Datenbank speichern
                self.appointment_manager.create_appointment(
                    patient_name_entry.get(),
                    phone_entry.get(),
                    email_entry.get(),
                    date_entry.get(),
                    start_time,
                    end_time,
                    doctor_entry.get(),
                )
                messagebox.showinfo("Erfolg", "Termin erfolgreich gebucht!")
                logging.info(f"Termin gebucht: {patient_name_entry.get()}, {date_entry.get()}, {start_time}-{end_time}")
                self.setup_home_screen()
            
            except Exception as e:
                # Bei Kollisionen Fehlermeldung anzeigen
                messagebox.showerror("Fehler", str(e))
                logging.error(f"Fehler bei der Terminbuchung: {e}")

        # Button zur Bestätigung der Buchung und zurückzukehren der Startseite 
        Button(self.root, text="Bestätigen", command=book).pack(pady=10)
        Button(self.root, text="Zurück", command=self.setup_home_screen).pack(pady=5)
    def show_appointments(self):
        """
        Zeigt alle geplanten Termine an.
        Benutzer können Erinnerungen senden, Termine verschieben oder löschen.
        """
        for widget in self.root.winfo_children():
            widget.destroy()
        
        Label(self.root, text="Termine", font=("Arial", 24)).pack(pady=20)

        # Liste der Termine aus der Datenbank abrufen
        appointments = self.appointment_manager.get_appointments()
        for app in appointments:
            frame = Frame(self.root)
            frame.pack(pady=5)

            # Termin anzeigen
            Label(frame, text=f"{app[1]} | {app[4]} | {app[5]}-{app[6]} | Arzt: {app[7]}").pack(side=LEFT)
            # Button zum Senden von Erinnerungen
            Button(frame, text="Erinnerung senden", command=lambda a=app: self.send_reminder(a)).pack(side=LEFT, padx=5)
            # Button zum Verschieben eines Termins
            Button(frame, text="Verschieben", command=lambda a=app: self.setup_reschedule_appointment(a)).pack(side=LEFT, padx=5)
            # Button zum Löschen eines Termins
            Button(frame, text="löschen", command=lambda a=app[0]: self.delete_appointment(a)).pack(side=LEFT, padx=5)
        
        # Zurück zur Startseite
        Button(self.root, text="Zurück", command=self.setup_home_screen).pack(pady=10)

    def delete_appointment(self, app_id):
        """
        Löscht einen Termin basierend auf der Termin-ID.
        """
        self.appointment_manager.delete_appointment(app_id)
        messagebox.showinfo("Erfolg", "Termin wurde gelöscht!")
        self.show_appointments()
        
    def setup_email_settings(self):
        """
        Stellt die Benutzeroberfläche für die Konfiguration der E-Mail-Einstellungen bereit.
        """
        for widget in self.root.winfo_children():
            widget.destroy()

        Label(self.root, text="E-Mail-Einstellungen", font=("Arial", 24)).pack(pady=20)

        Label(self.root, text="E-Mail:").pack(pady=5)
        email_entry = Entry(self.root)
        email_entry.pack()

        Label(self.root, text="Password:").pack(pady=5)
        password_entry = Entry(self.root, show="*")
        password_entry.pack()

        def save_email_settings():
            """
            Speichert die eingegebenen E-Mail-Einstellungen.
            """
            email = email_entry.get()
            password = password_entry.get()

            self.notification_service.set_credentials(email, password)

            messagebox.showinfo("Erfolg", "E-Mail-Einstellungen gespeichert!")
            self.setup_home_screen()

        # Speichern und Zurück-Buttons
        Button(self.root, text="Speichern", command=save_email_settings).pack(pady=10)
        Button(self.root, text="Zurück", command=self.setup_home_screen).pack(pady=5)

    def send_reminder(self, appointment):
        """
        Sendet eine E-Mail-Erinnerung für einen geplanten Termin an den Patienten.

        Parameter:
        -----------
        appointment : tuple
            Ein Tupel, das die Details eines Termins enthält. Die relevanten Elemente sind:
            - appointment[1]: Name des Patienten
            - appointment[3]: E-Mail-Adresse des Patienten
            - appointment[4]: Datum des Termins
            - appointment[5]: Startzeit des Termins
        """
        # Details aus dem übergebenen Termin-Tupel extrahieren
        patient_name, email, date, start_time = appointment[1], appointment[3], appointment[4], appointment[5]
        
        try:
            self.notification_service.send(
                recipient=email,
                subject="Termin-Erinnerung",
                message=f"Hallo {patient_name},\n\nIhr Termin ist am {date} um {start_time}. Bitte seien Sie pünktlich.\n\nMit freundlichen Grüßen,\nIhr Telemedizin-Team",
                )
            messagebox.showinfo("Erfolg", "Erinnerung gesendet!")
            logging.info(f"Erinnerung gesendet an {email} für Termin am {date} um {start_time}.")
        except Exception as e:
            # Fehler bei der E-Mail-Zustellung behandeln
            logging.error(f"Fehler beim Senden der Erinnerung: {e}")
            messagebox.showerror("Fehler", f"Die Erinnerung konnte nicht gesendet werden: {str(e)}")
    
    def setup_reschedule_appointment(self, appointment):
        """
        Stellt die Benutzeroberfläche zum Verschieben eines Termins bereit.
        """
        for widget in self.root.winfo_children():
            widget.destroy()

        Label(self.root, text="Termin verschieben", font=("Arial", 24)).pack(pady=20)

        Label(self.root, text="Neues Datum:").pack(pady=5)
        new_date_entry = DateEntry(self.root)
        new_date_entry.pack()

        Label(self.root, text="Verfügbare Zeiten:").pack(pady=5)
        available_slots_var = StringVar()
        available_slots_menu = OptionMenu(self.root, available_slots_var, "")
        available_slots_menu.pack(pady=5)

        def load_available_slots_new():
            """
            Lädt die verfügbaren Zeiten basierend auf dem neuen Datum und Arzt.
            """
            new_date = new_date_entry.get()
            slots = self.appointment_manager.get_available_slots(new_date)

            # Füge die ursprüngliche Buchungszeit (die verschoben wird) temporär zu den Slots hinzu
            current_start = appointment[5]
            current_end = appointment[6]
            slots.append((current_start, current_end))

            # Sortiere die Slots nach der Startzeit
            slots = sorted(slots, key=lambda x: datetime.strptime(x[0], "%H:%M"))

            # Aktualisiere das Dropdown-Menü
            available_slots_var.set("")  # Zurücksetzen
            available_slots_menu["menu"].delete(0, "end")
            for slot in slots:
                available_slots_menu["menu"].add_command(
                    label=f"{slot[0]} - {slot[1]}",
                    command=lambda s=slot: available_slots_var.set(f"{s[0]} - {s[1]}")
                )

        Button(self.root, text="Verfügbare Zeiten laden", command=load_available_slots_new).pack(pady=10)

        def reschedule():
            """
            Aktualisiert den Termin basierend auf der Auswahl im Dropdown-Menü.
            """
            if not available_slots_var.get():
                messagebox.showerror("Fehler", "Bitte wählen Sie eine verfügbare Zeit aus!")
                return

            new_date = new_date_entry.get()
            start_time, end_time = available_slots_var.get().split(" - ")

            # Aktualisiere den Termin in der Datenbank
            self.appointment_manager.update_appointment(appointment[0], new_date, start_time, end_time)

            # Zeige Erfolgsmeldung und aktualisiere die Ansicht
            messagebox.showinfo("Erfolg", "Termin wurde erfolgreich verschoben!")
            self.show_appointments()

        Button(self.root, text="Speichern", command=reschedule).pack(pady=10)
        Button(self.root, text="Abbrechen", command=self.show_appointments).pack(pady=5)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    db_manager = DatabaseManager("telemedicine.db")
    notification_service = EmailNotification()
    
    app = TelemedicineApp(db_manager, notification_service)
    app.run()