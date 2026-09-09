import socket
import json
import uuid

HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"
SERVER = "10.2.176.217"
ADDRESS = (SERVER, PORT)


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


def send_message(client, message):
    """send one length-prefixed message and return the server response"""
    encoded_message = message.encode(FORMAT)
    message_length = str(len(encoded_message)).encode(FORMAT)

    if len(message_length) > HEADER:
        raise ValueError("Message is too large for the header")

    padded_header = message_length + b" " * (HEADER - len(message_length))
    client.sendall(padded_header)
    client.sendall(encoded_message)

    response_header = receive_exact(client, HEADER)
    if response_header is None:
        raise ConnectionError("Server disconnected before sending a response")

    response_length = int(response_header.decode(FORMAT).strip())
    response_data = receive_exact(client, response_length)
    if response_data is None:
        raise ConnectionError("Server disconnected during the response")

    return response_data.decode(FORMAT)


def create_task_request(task_data):
    """validate task data and build a task.create request"""
    if not isinstance(task_data, dict):
        raise ValueError("Task data must be a JSON object.")

    title = task_data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Task title must be a non-empty string.")

    description = task_data.get("description", "")
    status = task_data.get("status", "todo")

    if not isinstance(description, str):
        raise ValueError("Task description must be a string.")
    if status not in {"todo", "in_progress", "review", "done"}:
        raise ValueError(
            "Task status must be todo, in_progress, review, or done."
        )

    return {
        "action": "task.create",
        "request_id": str(uuid.uuid4()),
        "data": {
            "title": title.strip(),
            "description": description.strip(),
            "status": status,
        },
    }


def display_response(response):
    """display JSON responses, with support for the current plain-text server"""
    try:
        response_data = json.loads(response)
    except json.JSONDecodeError:
        print(f"Server: {response}")
        return

    print(f"Server: {json.dumps(response_data, indent=2)}")


def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        try:
            client.connect(ADDRESS)
        except ConnectionRefusedError:
            print(f"Could not connect to {SERVER}:{PORT}.")
            print("Start server.py")
            return

        print(f"Connected to the server at {SERVER}:{PORT}")
        print("Type /add to add a task.")
        print("Type /quit to disconnect.\n")

        try:
            while True:
                message = input("Message: ")

                if message.lower() == "/quit":
                    response = send_message(client, DISCONNECT_MESSAGE)
                    display_response(response)
                    break

                if not message:
                    print("Message cannot be empty.")
                    continue

                if message.lower() == "/help":
                    print("Type /quit to disconnect.")
                    print("Type /help to see this message again.")
                    print("Type /add to add a task.")
                    continue

                if message.lower() == "/add":
                    print(
                        'Enter task JSON (e.g., {"title": "Do laundry", '
                        '"description": "Wash and fold", "status": "todo"}):'
                    )
                    task_input = input("Task: ")
                    try:
                        task_data = json.loads(task_input)
                        request = create_task_request(task_data)
                        message = json.dumps(request)
                    except json.JSONDecodeError:
                        print("Invalid JSON format. Please try again.")
                        continue
                    except ValueError as error:
                        print(error)
                        continue

                # else:
                #     print("Unknown command. Type /help to see available commands.")
                #     continue

                response = send_message(client, message)
                display_response(response)

        except (ConnectionError, KeyboardInterrupt):
            print("\nConnection closed.")


if __name__ == "__main__":
    start_client()
