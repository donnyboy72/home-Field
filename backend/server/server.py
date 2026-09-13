import socket
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
import json


HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"
HOST = "0.0.0.0"
ADDRESS = (HOST, PORT)
DATABASE_PATH = Path(__file__).resolve().parent.parent / "database" 


def create_messages_database():
    """create the messages table"""
    with sqlite3.connect(DATABASE_PATH / "messages.db") as database:
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

def create_tasks_database():
    """create the tasks table"""
    with sqlite3.connect(DATABASE_PATH / "tasks.db") as database:
        database.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL,
                is_delete INTEGER NOT NULL DEFAULT 0 CHECK (is_delete IN (0, 1)),
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row[1] for row in database.execute("PRAGMA table_info(tasks)")
        }
        if "is_delete" not in columns:
            database.execute(
                "ALTER TABLE tasks ADD COLUMN is_delete INTEGER NOT NULL DEFAULT 0"
            )


def save_message(address, message):
    """save one message to sqlite"""
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH / "messages.db", timeout=10) as database:
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


def send_response(connection, response):
    """send one length-prefixed response"""
    encoded_response = response.encode(FORMAT)
    response_length = str(len(encoded_response)).encode(FORMAT)
    padded_header = response_length + b" " * (HEADER - len(response_length))

    connection.sendall(padded_header)
    connection.sendall(encoded_response)


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
                send_response(connection, "Invalid message header")
                break

            message_data = receive_exact(connection, message_length)
            if message_data is None:
                break

            message = message_data.decode(FORMAT)

            if message == DISCONNECT_MESSAGE:
                send_response(connection, "Disconnected")
                break

            try:
                request = json.loads(message)
            except (json.JSONDecodeError, AttributeError):
                save_message(address, message)
                print(f"[{address[0]}:{address[1]}] {message}")
                send_response(connection, "Message received and saved")
                continue

            if not isinstance(request, dict):
                send_response(connection, "Invalid task data")
                continue

            if request.get("action") == "task.create":
                task_data = request.get("data")
                if (
                    isinstance(task_data, dict)
                    and isinstance(task_data.get("is_delete", False), bool)
                ):
                    with sqlite3.connect(DATABASE_PATH / "tasks.db") as database:
                        database.execute(
                            """
                            INSERT INTO tasks (
                                title, description, status, is_delete, created_at
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                task_data.get("title"),
                                task_data.get("description", ""),
                                task_data.get("status", "todo"),
                                int(task_data.get("is_delete", False)),
                                datetime.now(timezone.utc).isoformat(),
                            ),
                        )
                    send_response(connection, "Task created successfully")
                else:
                    send_response(connection, "Invalid task data")
            elif request.get("action") == "task.view":
                with sqlite3.connect(DATABASE_PATH / "tasks.db") as database:
                    database.row_factory = sqlite3.Row
                    rows = database.execute(
                        """
                        SELECT id, title, description, status, is_delete, created_at
                        FROM tasks
                        WHERE is_delete = 0
                        ORDER BY id
                        """
                    ).fetchall()

                tasks = []
                for row in rows:
                    task = dict(row)
                    task["is_delete"] = bool(task["is_delete"])
                    tasks.append(task)

                send_response(connection, json.dumps({"tasks": tasks}))
            elif request.get("action") == "task.delete":
                task_data = request.get("data")
                title = task_data.get("title") if isinstance(task_data, dict) else None

                if not isinstance(title, str) or not title.strip():
                    send_response(connection, "Invalid task title")
                    continue

                with sqlite3.connect(DATABASE_PATH / "tasks.db") as database:
                    cursor = database.execute(
                        """
                        UPDATE tasks
                        SET is_delete = 1
                        WHERE title = ? AND is_delete = 0
                        """,
                        (title.strip(),),
                    )

                if cursor.rowcount:
                    send_response(connection, "Task marked as deleted successfully")
                else:
                    send_response(connection, "No such task exists")
            else:
                send_response(connection, "Invalid task data")

    except (ConnectionError, UnicodeDecodeError) as error:
        print(f"[CONNECTION ERROR] {address}: {error}")
    finally:
        connection.close()
        print(f"[DISCONNECTED] {address[0]}:{address[1]}")


def start_server():
    create_messages_database()
    create_tasks_database()


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
