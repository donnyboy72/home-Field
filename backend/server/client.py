import socket


HEADER = 64
PORT = 5050
FORMAT = "utf-8"
DISCONNECT_MESSAGE = "!DISCONNECT"
SERVER = "192.168.0.218"
ADDRESS = (SERVER, PORT)


def send_message(client, message):
    """send one length-prefixed message and return the server response"""
    encoded_message = message.encode(FORMAT)
    message_length = str(len(encoded_message)).encode(FORMAT)

    if len(message_length) > HEADER:
        raise ValueError("Message is too large for the header")

    padded_header = message_length + b" " * (HEADER - len(message_length))
    client.sendall(padded_header)
    client.sendall(encoded_message)

    return client.recv(2048).decode(FORMAT)


def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        try:
            client.connect(ADDRESS)
        except ConnectionRefusedError:
            print(f"Could not connect to {SERVER}:{PORT}.")
            print("Start server.py")
            return

        print(f"Connected to the server at {SERVER}:{PORT}")
        print("Type a message and press Enter.")
        print("Type /quit to disconnect.\n")

        try:
            while True:
                message = input("Message: ")

                if message.lower() == "/quit":
                    response = send_message(client, DISCONNECT_MESSAGE)
                    print(f"Server: {response}")
                    break

                if not message:
                    print("Message cannot be empty.")
                    continue

                response = send_message(client, message)
                print(f"Server: {response}")

        except (ConnectionError, KeyboardInterrupt):
            print("\nConnection closed.")


if __name__ == "__main__":
    start_client()
