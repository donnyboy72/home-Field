import socket
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"
HOST = "192.168.0.218"
ADDRESS = (HOST, PORT)
DATABASE_PATH = Path(__file__).with_name("messages.db")


def create_database():
    """create the messages table"""
    with sqlite3.connect(DATABASE_PATH) as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_ip TEXT NOT NULL,
                client_port INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )


def save_message(address, message):
    """save one message to sqlite"""
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH, timeout=10) as database:
        database.execute(
            """
            INSERT INTO messages (client_ip, client_port, message, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (address[0], address[1], message, timestamp),
        )


def receive_exact(connection, byte_count):
    """receive exactly byte_count bytes or return None if disconnected"""
    chunks = []
    bytes_received = 0

    while bytes_received < byte_count:
        chunk = connection.recv(byte_count - bytes_received)
        if not chunk:
            return None
        chunks.append(chunk)
        bytes_received += len(chunk)

    return b"".join(chunks)


def handle_client(connection, address):
    print(f"[NEW CONNECTION] {address[0]}:{address[1]} connected")

    try:
        while True:
            header = receive_exact(connection, HEADER)
            if header is None:
                break

            header_text = header.decode(FORMAT).strip()
            if not header_text:
                continue

            try:
                message_length = int(header_text)
            except ValueError:
                connection.sendall("Invalid message header".encode(FORMAT))
                break

            message_data = receive_exact(connection, message_length)
            if message_data is None:
                break

            message = message_data.decode(FORMAT)

            if message == DISCONNECT_MESSAGE:
                connection.sendall("Disconnected".encode(FORMAT))
                break

            save_message(address, message)
            print(f"[{address[0]}:{address[1]}] {message}")
            connection.sendall("Message received and saved".encode(FORMAT))

    except (ConnectionError, UnicodeDecodeError) as error:
        print(f"[CONNECTION ERROR] {address}: {error}")
    finally:
        connection.close()
        print(f"[DISCONNECTED] {address[0]}:{address[1]}")


def start_server():
    create_database()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(ADDRESS)
        server.listen()

        print(f"[LISTENING] Server is running on {HOST}:{PORT}")
        print(f"[DATABASE] Messages are saved to {DATABASE_PATH}")
        print("Press Ctrl+C to stop the server.")

        try:
            while True:
                connection, address = server.accept()
                thread = threading.Thread(
                    target=handle_client,
                    args=(connection, address),
                    daemon=True,
                )
                thread.start()
                print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")
        except KeyboardInterrupt:
            print("\n[STOPPING] Server stopped.")


if __name__ == "__main__":
    start_server()
