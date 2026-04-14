# TelChat – Requirements

| ID | Category | Title | Description | Covered By |
|----|----------|-------|-------------|------------|
| F-SYS-010 | System | Zentraler TCP-Hub | Der Router fungiert als dedizierter TCP-Server für JSON-basierte Kommunikation innerhalb des Wireguard-Netzes. | - |
| F-SYS-020 | System | Agent-Availability Watchdog | Der Router trennt Verbindungen bei Zeitüberschreitung und meldet den Ausfall des Agenten aktiv an @human. | - |
| F-COM-030 | Protocol | JSON-Schema Pflichtfelder | Jede Nachricht muss als valides JSON mit den Feldern `from`, `to`, `msg_type` (Enum: registration, data, error, ack), `data` sowie einem Unix-Zeitstempel vorliegen. | - |
| F-COM-040 | Protocol | Header-basiertes Routing | Die Zustellung erfolgt ausschließlich über die Auswertung des `to`-Feldes im JSON-Objekt. | - |
| F-COM-050 | Protocol | Byte-Count im Datenknoten | Jede Nachricht enthält die Anzahl der Bytes des `data`-Knotens als eigenes Feld. | - |
| F-COM-060 | Protocol | Lesebestätigung | Es existiert ein dediziertes JSON-Format (msg_type `ack`) zur Bestätigung des Nachrichtenempfangs. | - |
| F-REG-070 | Registry | JSON-basierte Anmeldung | Agenten registrieren ihren eindeutigen Alias über eine initiale JSON-Nachricht vom Typ `registration`. | - |
| F-UX-080 | UX | JSON-to-Table Formatter | Der Router transformiert JSON-Strukturen im `data`-Feld für den Empfänger `human` in eine lesbare Text-Tabelle. | - |
| F-UX-090 | UX | CLI-to-JSON Wrapper | Benutzereingaben (z.B. `@pta ...`) werden vom Router in das interne JSON-Standardformat gekapselt. | - |
| F-UX-095 | UX | Human Telnet Login & Feedback | Humans können sich statt mit JSON auch nur durch Eingabe ihres Alias registrieren. Bei Formatfehlern erhalten sie ein Text-Feedback plus Echo ihrer Eingabe. | - |
| F-UX-100 | UX | Human-Date Conversion | Unix-Zeitstempel werden für die Ausgabe an menschliche Schnittstellen in ein lesbares Format (ISO 8601/Lokalzeit) gewandelt. | - |
| F-ERR-110 | Error | Fehler-Feedback an Human | Systemfehler (Timeout, unbekanntes Ziel) werden als systemgenerierte Nachrichten an die menschlichen Nutzer gesendet. | - |
| F-SYS-120 | System | Multi-Human Broadcast | Nachrichten an den Empfänger `human` müssen an alle aktuell verbundenen menschlichen Schnittstellen gleichzeitig verteilt werden. | - |
| F-LOG-130 | Logging | Router-Logfile | Sämtliche Nachrichten, die den Router passieren, werden vollständig in eine Logdatei geschrieben. | - |
| F-CFG-140 | Config | Alias-Konfigurationsdatei | Gültige Agenten-Aliase werden in einer zentralen Konfigurationsdatei definiert. Nur dort eingetragene Aliase dürfen sich registrieren. | - |
| F-EXT-150 | Extension | Externer Web-Proxy (Zukunft) | Die Web-Anbindung erfolgt über einen separaten Proxy-Container, der Telnet-Streams in WebSockets für Browser übersetzt. | - |