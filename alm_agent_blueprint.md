# TelChat Agent – Implementation Guide (v1.0)

> Dieses Dokument beschreibt, wie ein Client-Programm (Agent) implementiert werden muss, um erfolgreich mit dem TelChat-Router zu kommunizieren.

---

## 1. Netzwerk-Layer

- **Protokoll:** TCP (Standard-Socket)
- **Standard-Port:** `9999`
- **Format:** Zeilenbasierte Kommunikation. Jede Nachricht MUSS mit einem Newline-Zeichen (`\n`) abgeschlossen werden.
- **Encoding:** UTF-8

---

## 2. Der Lebenszyklus eines Agenten

### Phase 1: Verbindung & Registrierung
Direkt nach dem Öffnen des TCP-Sockets MUSS der Agent eine Registrierungs-Nachricht senden. Der Router verwirft alle anderen Nachrichten oder schließt die Verbindung, wenn kein gültiger Alias registriert wird.

**Schema (Registration):**
```json
{
  "from": "DEIN_ALIAS",
  "to": "router",
  "msg_type": "registration",
  "timestamp": 1713100000.0,
  "byte_count": 27,
  "data": { "alias": "DEIN_ALIAS" }
}
```
*Wichtig: Der `DEIN_ALIAS` muss in der `config/agents.json` des Routers hinterlegt sein.*

### Phase 2: Die Message-Loop
Nach erfolgreicher Registrierung tritt der Agent in die Loop ein:
1. **Senden:** Nachrichten an andere Agenten oder `human`.
2. **Empfangen:** Eingehende Nachrichten (JSON) oder ACKs verarbeiten.
3. **Heartbeat:** Mindestens alle 50 Sekunden eine Nachricht senden (oder ein ACK), um den Router-Watchdog (60s Timeout) zurückzusetzen.

---

## 3. Nachrichten-Schema (Pflichtfelder)

Jedes JSON-Objekt auf der Leitung muss folgende 6 Felder enthalten:

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `from` | string | Dein registrierter Alias. |
| `to` | string | Ziel-Alias (z.B. `pta`, `human`). |
| `msg_type` | string | `data`, `registration`, `error` oder `ack`. |
| `timestamp` | float | Unix-Zeitstempel (Sekunden seit 1970). |
| `byte_count` | int | Die Länge des JSON-Strings im `data`-Feld. |
| `data` | object | Das tatsächliche Payload-Objekt. |

---

## 4. Spezielle Nachrichten-Typen

### Lesebestätigungen (msg_type: "ack")
Agenten sollten den Empfang wichtiger Nachrichten quittieren (Optional, aber empfohlen).

```json
{
  "from": "scanner",
  "to": "pta",
  "msg_type": "ack",
  "timestamp": 1713100005.0,
  "byte_count": 45,
  "data": { "ack_for": 1713100001.0 }
}
```
*Das Feld `ack_for` muss den exakten `timestamp` der Originalnachricht enthalten.*

### Fehlerbehandlung (msg_type: "error")
Der Router sendet Fehlermeldungen unter dem Alias `system`.

```json
{
  "from": "system",
  "to": "pta",
  "msg_type": "error",
  "data": { "error": "Recipient agent 'scanner' is not connected" }
}
```

---

## 5. Besonderheiten für "Human"-Agenten

Wenn ein Agent in der Konfiguration als `is_human: true` markiert ist:
- Er erhält Nachrichten vom Router in **formatiertem Text** (CLI-Tabellen), nicht als JSON (außer bei ACKs).
- Er kann Text-Befehle im Format `@empfänger Nachricht` senden. Der Router parst diese automatisch in JSON um.

---

## 6. Checkliste für die Implementierung

- [ ] Socket-Verbindung zu Host/Port aufbauen.
- [ ] Sofort Registration-JSON senden (mit Newline!).
- [ ] Background-Thread zum Lesen einrichten (Warten auf `\n`).
- [ ] `byte_count` vor dem Senden immer frisch berechnen.
- [ ] `timestamp` bei jeder Nachricht setzen.
- [ ] Fehlerfall: Bei Connection-Loss (Broken Pipe) den Reconnect-Prozess einleiten.

---

## Beispiel: Minimaler Python-Client (Pseudo-Code)

```python
import socket, json, time

def send(sock, sender, to, type, data):
    payload = json.dumps(data)
    msg = {
        "from": sender, "to": to, "msg_type": type,
        "timestamp": time.time(), "byte_count": len(payload.encode("utf-8")),
        "data": data
    }
    sock.sendall((json.dumps(msg) + "\n").encode("utf-8"))

# 1. Connect
s = socket.socket()
s.connect(("127.0.0.1", 9999))

# 2. Register
send(s, "pta", "router", "registration", {"alias": "pta"})

# 3. Loop
while True:
    send(s, "pta", "human", "data", {"signal": "BUY", "ticker": "AAPL"})
    time.sleep(30) # Reset Watchdog
```
