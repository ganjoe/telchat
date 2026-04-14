import pytest
import socket
import json
import time
import threading
import os
from net.tcp_server import TelChatServer
from core.message import MessageType


# --- Test Setup ---

TEST_CONFIG = "config/agents_test.json"
TEST_HOST = "127.0.0.1"
TEST_PORT = 10000

@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    # Create test config
    config_data = {
        "agents": [
            {"alias": "pta", "description": "Agent A", "is_human": False},
            {"alias": "scanner", "description": "Agent B", "is_human": False},
            {"alias": "human", "description": "Human 1", "is_human": True},
            {"alias": "human2", "description": "Human 2", "is_human": True}
        ]
    }
    os.makedirs("config", exist_ok=True)
    with open(TEST_CONFIG, "w") as f:
        json.dump(config_data, f)
    
    # Start server in background thread
    server = TelChatServer(host=TEST_HOST, port=TEST_PORT, config_path=TEST_CONFIG)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(1) # Give server time to bind
    yield
    # Server dies with thread on process exit


# --- Utilities ---

def connect_and_register(alias):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TEST_HOST, TEST_PORT))
    sock.settimeout(2.0)
    
    data = {"alias": alias}
    bc = len(json.dumps(data).encode("utf-8"))
    reg_msg = {
        "from": alias,
        "to": "router",
        "msg_type": "registration",
        "timestamp": time.time(),
        "byte_count": bc,
        "data": data
    }
    sock.sendall((json.dumps(reg_msg) + "\n").encode("utf-8"))
    time.sleep(0.1)
    return sock

def receive_line(sock):
    buffer = b""
    while True:
        try:
            chunk = sock.recv(1)
            if not chunk: return None
            if chunk == b"\n": break
            buffer += chunk
        except socket.timeout:
            return None
    return buffer.decode("utf-8")

def receive_all(sock, timeout=1.0):
    """Wait for all data from socket until timeout."""
    sock.setblocking(0)
    total_data = []
    begin = time.time()
    while True:
        # If we got some data, then stay in the loop for a short while to see if more is coming
        if total_data and time.time() - begin > 0.1:
            break
        # If we waited too long, break
        if time.time() - begin > timeout:
            break
        try:
            data = sock.recv(8192)
            if data:
                total_data.append(data.decode("utf-8"))
                begin = time.time()
            else:
                time.sleep(0.01)
        except socket.error:
            time.sleep(0.01)
    return "".join(total_data)


# --- Test Cases ---

def test_it_010_connection_accepted():
    """Validates F-SYS-010: Server accepts connections."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TEST_HOST, TEST_PORT))
    sock.close()

def test_it_020_030_registration_enforcement():
    """Validates F-REG-070, F-CFG-140: Valid vs Invalid Alias."""
    # Valid alias
    sock1 = connect_and_register("pta")
    # Valid message format for next test
    msg_data = {"ping": "pong"}
    bc = len(json.dumps(msg_data).encode("utf-8"))
    msg = {
        "from": "pta", "to": "router", "msg_type": "data",
        "timestamp": time.time(), "byte_count": bc, "data": msg_data
    }
    sock1.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    time.sleep(0.1)
    sock1.close()

    # Invalid alias
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock2.connect((TEST_HOST, TEST_PORT))
    reg_msg = {
        "from": "unknown", "to": "router", "msg_type": "registration", 
        "timestamp": time.time(), "byte_count": 0, "data": {}
    }
    sock2.sendall((json.dumps(reg_msg) + "\n").encode("utf-8"))
    time.sleep(0.2)
    response = sock2.recv(1024).decode()
    assert "Fehler:" in response
    assert sock2.recv(1024) == b"" # Server should close connection afterwards

def test_it_050_agent_to_agent_routing():
    """Validates F-COM-040: Routing between agents."""
    sock_a = connect_and_register("pta")
    sock_b = connect_and_register("scanner")
    
    msg_data = {"symbol": "AAPL", "cmd": "scan"}
    bc = len(json.dumps(msg_data).encode("utf-8"))
    msg = {
        "from": "pta", "to": "scanner", "msg_type": "data",
        "timestamp": time.time(), 
        "byte_count": bc,
        "data": msg_data
    }
    sock_a.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    
    raw_recv = receive_line(sock_b)
    assert raw_recv is not None
    data_recv = json.loads(raw_recv)
    assert data_recv["from"] == "pta"
    assert data_recv["data"]["symbol"] == "AAPL"
    
    sock_a.close()
    sock_b.close()

def test_it_080_human_broadcast():
    """Validates F-SYS-120: Multi-human broadcast."""
    h1 = connect_and_register("human")
    h2 = connect_and_register("human2")
    agent = connect_and_register("pta")
    
    msg_data = {"alert": "Crash!"}
    bc = len(json.dumps(msg_data).encode("utf-8"))
    msg = {
        "from": "pta", "to": "human", "msg_type": "data",
        "timestamp": time.time(), 
        "byte_count": bc,
        "data": msg_data
    }
    agent.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    
    # Use receive_all for humans because they receive multi-line tables
    r1 = receive_all(h1)
    r2 = receive_all(h2)
    
    assert r1 != ""
    assert r2 != ""
    assert "Crash!" in r1
    assert "pta" in r1
    # Check if a table character is present
    assert "┌" in r1 or "│" in r1
    
    h1.close()
    h2.close()
    agent.close()

def test_it_100_cli_parsing():
    """Validates F-UX-090: CLI input from human."""
    h = connect_and_register("human")
    a = connect_and_register("scanner")
    
    # Human types raw text
    h.sendall(b"@scanner scan MSFT\n")
    
    raw = receive_line(a)
    assert raw is not None
    data = json.loads(raw)
    assert data["from"] == "human"
    assert data["to"] == "scanner"
    assert data["data"]["text"] == "scan MSFT"
    
    h.close()
    a.close()

def test_it_110_ack_logic():
    """Validates F-COM-060: ACKs are routed as raw JSON."""
    h = connect_and_register("human")
    a = connect_and_register("pta")
    
    t_ref = 1234567.89
    ack_data = {"ack_for": t_ref}
    bc = len(json.dumps(ack_data).encode("utf-8"))
    ack = {
        "from": "pta", "to": "human", "msg_type": "ack",
        "timestamp": time.time(), "byte_count": bc,
        "data": ack_data
    }
    a.sendall((json.dumps(ack) + "\n").encode("utf-8"))
    
    # ACKs to humans come as raw JSON (one line)
    raw = receive_line(h)
    assert raw is not None
    data = json.loads(raw)
    assert data["msg_type"] == "ack"
    assert data["data"]["ack_for"] == t_ref
    
    h.close()
    a.close()

def test_it_130_error_on_missing_recipient():
    """Validates F-ERR-110: Feedback on unknown recipient."""
    h = connect_and_register("human")
    a = connect_and_register("pta")
    
    # Send to "scanner" (not connected)
    msg_data = {"x": 1}
    bc = len(json.dumps(msg_data).encode("utf-8"))
    msg = {
        "from": "pta", "to": "scanner", "msg_type": "data",
        "timestamp": time.time(), "byte_count": bc, "data": msg_data
    }
    a.sendall((json.dumps(msg) + "\n").encode("utf-8"))
    
    # Error comes back as JSON
    raw = receive_line(a)
    assert raw is not None
    err = json.loads(raw)
    assert err["from"] == "system"
    assert "not connected" in err["data"]["error"]
    
    h.close()
    a.close()

def test_it_150_logfile_created():
    """Validates F-LOG-130: Logfile creation."""
    # Ensure logs directory exists
    log_dir = "logs"
    assert os.path.exists(log_dir)
    files = os.listdir(log_dir)
    assert len(files) > 0
    # Current log file should be in there
    found = any(f.startswith("telchat_") and f.endswith(".log") for f in files)
    assert found
