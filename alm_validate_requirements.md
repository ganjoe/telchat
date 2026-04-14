# TelChat – Integration Test Specification

> Dieses Dokument definiert die Integrationstests zur Validierung der TelChat-Requirements.
> Jeder Test referenziert die zugehörigen Requirements aus `alm_requirements.md`.
> Tests sind so formuliert, dass sie automatisiert mit einem TCP-Client (z.B. `socket`) ausgeführt werden können.

---

## Testumgebung

```
┌─────────────────────────────────────────────────┐
│  Test-Harness (pytest)                          │
│                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐   │
│  │ Client A  │  │ Client B  │  │ Client C  │   │
│  │ (Agent)   │  │ (Agent)   │  │ (Human)   │   │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘   │
│        │              │              │          │
│        └──────────┬───┴──────────────┘          │
│                   │ TCP                         │
│            ┌──────┴──────┐                      │
│            │ TelChat     │                      │
│            │ Server      │                      │
│            └─────────────┘                      │
└─────────────────────────────────────────────────┘
```

### Voraussetzungen

- Der Server wird pro Testklasse einmal gestartet (Setup) und nach allen Tests gestoppt (Teardown).
- Die Test-Config `config/agents_test.json` enthält mindestens:
  - `"pta"` (is_human: false)
  - `"scanner"` (is_human: false)
  - `"human"` (is_human: true)
  - `"human2"` (is_human: true)
- Jeder Test-Client ist ein einfacher TCP-Socket, der JSON senden und empfangen kann.
- Timeout für Socket-Operationen: 5 Sekunden.
- Logfile-Pfad wird auf ein temporäres Verzeichnis gesetzt.

---

## Hilfsfunktionen (Test-Utilities)

Die folgenden Hilfsfunktionen werden von allen Tests verwendet:

```
connect_and_register(alias) → socket
    1. Öffne TCP-Socket zum Server
    2. Sende Registration-JSON: {"from": alias, "to": "router", "msg_type": "registration", "timestamp": ..., "byte_count": ..., "data": {"alias": alias}}
    3. Warte kurz (100ms) damit der Server die Registration verarbeiten kann
    4. Gib den Socket zurück

send_message(socket, from, to, data) → None
    1. Baue vollständiges JSON mit allen Pflichtfeldern
    2. Berechne byte_count aus data
    3. Sende als newline-terminierte Zeile

receive_message(socket, timeout=5) → str oder None
    1. Lese vom Socket bis Newline
    2. Bei Timeout: return None

read_logfile(path) → List[str]
    1. Lese alle Zeilen der Logdatei
    2. Gib als Liste zurück
```

---

## Testfälle

---

### IT-010 | Server-Start und Verbindungsaufbau

**Validiert:** F-SYS-010
**Priorität:** Kritisch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Server starten mit Test-Config | Server läuft, Port ist offen |
| 2 | TCP-Socket zu Server öffnen | Verbindung wird akzeptiert |
| 3 | Zweiten TCP-Socket öffnen | Auch diese Verbindung wird akzeptiert (Multi-Client) |

**Fail-Kriterium:** ConnectionRefusedError bei Schritt 2 oder 3.

---

### IT-020 | Agent-Registration (Happy Path)

**Validiert:** F-REG-070, F-CFG-140
**Priorität:** Kritisch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client verbindet und sendet Registration für Alias `"pta"` | Verbindung bleibt offen |
| 2 | Client sendet eine Data-Nachricht an `"human"` | Nachricht wird akzeptiert (kein Verbindungsabbruch) |

**Fail-Kriterium:** Verbindung wird nach Registration geschlossen.

---

### IT-030 | Registration mit ungültigem Alias

**Validiert:** F-CFG-140
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client verbindet und sendet Registration für Alias `"unknown_agent"` | Server schließt die Verbindung |
| 2 | Versuch, eine Data-Nachricht zu senden | Socket-Fehler (BrokenPipe / ConnectionReset) |

**Fail-Kriterium:** Server akzeptiert den unbekannten Alias.

---

### IT-040 | Registration ohne Registration-Message

**Validiert:** F-REG-070
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client verbindet und sendet direkt eine Data-Nachricht (kein Registration) | Server schließt die Verbindung |

**Fail-Kriterium:** Server akzeptiert Nachrichten ohne vorherige Registration.

---

### IT-050 | Agent-zu-Agent Routing

**Validiert:** F-COM-040
**Priorität:** Kritisch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client A registriert sich als `"pta"` | Verbindung steht |
| 2 | Client B registriert sich als `"scanner"` | Verbindung steht |
| 3 | Client A sendet Data-Nachricht mit `to="scanner"` | — |
| 4 | Client B liest vom Socket | Client B empfängt die JSON-Nachricht |
| 5 | Empfangene Nachricht parsen | Felder `from`, `to`, `msg_type`, `timestamp`, `byte_count`, `data` sind vollständig vorhanden |

**Fail-Kriterium:** Client B empfängt nichts (Timeout) oder JSON ist unvollständig.

---

### IT-060 | JSON-Schema Pflichtfelder

**Validiert:** F-COM-030
**Priorität:** Kritisch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client A registriert sich als `"pta"` | Verbindung steht |
| 2 | Client A sendet JSON ohne `msg_type`-Feld | Nachricht wird verworfen (kein Crash, kein Routing) |
| 3 | Client A sendet JSON ohne `timestamp`-Feld | Nachricht wird verworfen |
| 4 | Client A sendet JSON ohne `data`-Feld | Nachricht wird verworfen |
| 5 | Client A sendet invalides JSON (kein JSON-String) | Nachricht wird verworfen |
| 6 | Verbindung von Client A prüfen | Verbindung ist noch offen (kein Disconnect bei fehlerhaften Nachrichten) |

**Fail-Kriterium:** Server crasht oder routet unvollständige Nachrichten.

---

### IT-070 | Byte-Count Validierung

**Validiert:** F-COM-050
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client A registriert sich als `"pta"`, Client B als `"scanner"` | Verbindungen stehen |
| 2 | Client A sendet Nachricht mit korrektem `byte_count` an `"scanner"` | Client B empfängt die Nachricht |
| 3 | Client A sendet Nachricht mit falschem `byte_count` (z.B. 0) an `"scanner"` | Nachricht wird verworfen, Client B empfängt nichts |

**Fail-Kriterium:** Nachricht mit falschem byte_count wird zugestellt.

---

### IT-080 | Human Broadcast

**Validiert:** F-SYS-120
**Priorität:** Kritisch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client C1 registriert sich als `"human"` | Verbindung steht |
| 2 | Client C2 registriert sich als `"human2"` | Verbindung steht |
| 3 | Client A registriert sich als `"pta"` | Verbindung steht |
| 4 | Client A sendet Data-Nachricht mit `to="human"` | — |
| 5 | Client C1 liest vom Socket | Empfängt formatierte Nachricht |
| 6 | Client C2 liest vom Socket | Empfängt ebenfalls formatierte Nachricht |
| 7 | Inhalte von C1 und C2 vergleichen | Beide haben identischen Inhalt |

**Fail-Kriterium:** Nur ein Human empfängt die Nachricht, oder keiner.

---

### IT-090 | Human-Formatierung (JSON-to-Table)

**Validiert:** F-UX-080, F-UX-100
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client C registriert sich als `"human"` | Verbindung steht |
| 2 | Client A registriert sich als `"pta"` | Verbindung steht |
| 3 | Client A sendet `{"symbol": "AAPL", "price": 185.23}` an `"human"` | — |
| 4 | Client C liest vom Socket | Empfängt **keinen** rohen JSON-String |
| 5 | Empfangenen Text prüfen | Enthält Tabellen-Zeichen (`│`, `─`) ODER strukturierte Darstellung |
| 6 | Empfangenen Text prüfen | Enthält lesbaren Zeitstempel (Format `YYYY-MM-DD HH:MM:SS`), KEINEN Unix-Timestamp |
| 7 | Empfangenen Text prüfen | Enthält Absender-Alias `"pta"` |

**Fail-Kriterium:** Human empfängt rohen JSON oder Unix-Timestamp.

---

### IT-100 | CLI-to-JSON Wrapper

**Validiert:** F-UX-090
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client C registriert sich als `"human"` | Verbindung steht |
| 2 | Client B registriert sich als `"scanner"` | Verbindung steht |
| 3 | Client C sendet rohen Text: `@scanner scan AAPL\n` | — |
| 4 | Client B liest vom Socket | Empfängt valides JSON |
| 5 | JSON parsen | `from="human"`, `to="scanner"`, `msg_type="data"` |
| 6 | `data`-Feld prüfen | Enthält `{"text": "scan AAPL"}` |

**Fail-Kriterium:** Client B empfängt nichts, oder `data` enthält nicht den Text.

---

### IT-110 | Lesebestätigung (ACK)

**Validiert:** F-COM-060
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client A registriert sich als `"pta"` | Verbindung steht |
| 2 | Client B registriert sich als `"scanner"` | Verbindung steht |
| 3 | Client A sendet Data-Nachricht an `"scanner"` mit Timestamp `T1` | — |
| 4 | Client B empfängt die Nachricht | Nachricht liegt vor |
| 5 | Client B sendet ACK: `{"from": "scanner", "to": "pta", "msg_type": "ack", "timestamp": ..., "byte_count": ..., "data": {"ack_for": T1}}` | — |
| 6 | Client A liest vom Socket | Empfängt das ACK als JSON |
| 7 | ACK parsen | `msg_type="ack"`, `data.ack_for == T1` |

**Fail-Kriterium:** ACK kommt nicht bei Client A an, oder `ack_for` fehlt.

---

### IT-120 | ACK wird nicht als Tabelle formatiert

**Validiert:** F-COM-060, F-UX-080
**Priorität:** Mittel

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client C registriert sich als `"human"` | Verbindung steht |
| 2 | Client A registriert sich als `"pta"` | Verbindung steht |
| 3 | Client A sendet ACK-Nachricht an `"human"` | — |
| 4 | Client C liest vom Socket | Empfängt **rohen JSON**, KEINE Tabelle |

**Fail-Kriterium:** ACK wird als formatierte Tabelle zugestellt.

---

### IT-130 | Fehler bei unbekanntem Empfänger

**Validiert:** F-ERR-110
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client A registriert sich als `"pta"` | Verbindung steht |
| 2 | Client C registriert sich als `"human"` | Verbindung steht |
| 3 | Client A sendet Nachricht an `"scanner"` (NICHT verbunden) | — |
| 4 | Client C liest vom Socket | Empfängt Fehlermeldung vom System |
| 5 | Fehlermeldung prüfen | Enthält Hinweis auf `"scanner"` und dass Agent nicht erreichbar ist |
| 6 | Absender der Fehlermeldung prüfen | Absender ist `"system"` |

**Fail-Kriterium:** Kein Fehler-Feedback, oder Fehler geht an falschen Empfänger.

---

### IT-140 | Watchdog Timeout

**Validiert:** F-SYS-020
**Priorität:** Kritisch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Server mit kurzem Timeout starten (z.B. 3 Sekunden) | Server läuft |
| 2 | Client A registriert sich als `"pta"` | Verbindung steht |
| 3 | Client C registriert sich als `"human"` | Verbindung steht |
| 4 | Client A sendet KEINE weiteren Nachrichten | — |
| 5 | Warte Timeout + Check-Interval ab (z.B. 5 Sekunden) | — |
| 6 | Client C liest vom Socket | Empfängt Timeout-Fehlermeldung für `"pta"` |
| 7 | Fehlermeldung prüfen | `from="system"`, `msg_type` enthält Timeout-Hinweis |

**Sonderhinweis:** Dieser Test benötigt einen Server mit angepasster Watchdog-Konfiguration (kurzer Timeout). Entweder über Umgebungsvariablen oder Test-spezifische Server-Instanz.

**Fail-Kriterium:** Kein Timeout-Feedback, oder Agent bleibt registriert.

---

### IT-150 | Router-Logfile

**Validiert:** F-LOG-130
**Priorität:** Hoch

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Server mit temporärem Log-Verzeichnis starten | Server läuft |
| 2 | Client A registriert sich als `"pta"` | — |
| 3 | Client B registriert sich als `"scanner"` | — |
| 4 | Client A sendet eine Data-Nachricht an `"scanner"` | — |
| 5 | Client B empfängt die Nachricht | — |
| 6 | Logfile einlesen | Logfile existiert und ist nicht leer |
| 7 | Logfile-Inhalt prüfen | Enthält mindestens 3 Einträge: Registration A, Registration B, die Data-Nachricht |
| 8 | Einen Logeintrag prüfen | Enthält Zeitstempel, Richtung (RECV/ROUTE/SEND), Sender, Empfänger und JSON-Payload |

**Fail-Kriterium:** Logfile existiert nicht, ist leer, oder enthält unvollständige Einträge.

---

### IT-160 | Mehrere Nachrichten in Serie

**Validiert:** F-COM-040, F-SYS-010
**Priorität:** Mittel

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Client A (`"pta"`) und Client B (`"scanner"`) registrieren sich | Verbindungen stehen |
| 2 | Client A sendet 10 Nachrichten an `"scanner"` in schneller Folge | — |
| 3 | Client B liest alle Nachrichten | Genau 10 Nachrichten empfangen |
| 4 | Reihenfolge prüfen | Nachrichten kommen in der Sendereihenfolge an (FIFO) |

**Fail-Kriterium:** Nachrichten gehen verloren, werden dupliziert, oder kommen in falscher Reihenfolge.

---

### IT-170 | Gleichzeitige Agent-Verbindungen

**Validiert:** F-SYS-010
**Priorität:** Mittel

| Schritt | Aktion | Erwartetes Ergebnis |
|---------|--------|---------------------|
| 1 | Alle 4 Test-Agenten gleichzeitig registrieren (`"pta"`, `"scanner"`, `"human"`, `"human2"`) | Alle Verbindungen stehen |
| 2 | `"pta"` sendet an `"scanner"` | `"scanner"` empfängt |
| 3 | `"scanner"` sendet an `"human"` | Beide Humans empfangen |
| 4 | `"human"` sendet `@pta hello` | `"pta"` empfängt JSON |

**Fail-Kriterium:** Irgendeine Nachricht wird nicht zugestellt.

---

## Requirements-Traceability

| Requirement | Getestet durch |
|-------------|----------------|
| F-SYS-010 | IT-010, IT-160, IT-170 |
| F-SYS-020 | IT-140 |
| F-COM-030 | IT-060 |
| F-COM-040 | IT-050, IT-160 |
| F-COM-050 | IT-070 |
| F-COM-060 | IT-110, IT-120 |
| F-REG-070 | IT-020, IT-040 |
| F-UX-080 | IT-090, IT-120 |
| F-UX-090 | IT-100 |
| F-UX-100 | IT-090 |
| F-ERR-110 | IT-130 |
| F-SYS-120 | IT-080 |
| F-LOG-130 | IT-150 |
| F-CFG-140 | IT-030 |
| F-EXT-150 | — (Zukunft, nicht testbar) |
