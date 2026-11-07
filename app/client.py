import socket

import socket
import ssl


class Client:

    def __init__(self):
        """
        Constructor
        """
        self.internal_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.internal_connection.connect(("localhost", 9000))

    def connect(self, host, port=80, secure=False):
        """
        Establishes a connection
        """
        connection_port = port
        if secure:
            connection_port = 443
        self.internal_connection.connect((host, connection_port))
        if secure:
            self.internal_connection = ssl.wrap_socket(self.internal_connection, keyfile=None, certfile=None,
                                                       server_side=False, cert_reqs=ssl.CERT_NONE,
                                                       ssl_version=ssl.PROTOCOL_SSLv23)

    def send_request(self, request):
        """
        Sends an arbitrary request
        :param request: The request to send (as text)
        :return:
        """
        self.internal_connection.send(request.encode())

    def receive_header(self):
        """
        Waits and receives the response headers form the server
        :return:
        """
        return repr(self.internal_connection.recv(4096))

    def receive_body(self):
        """
        Waits and receives the response body form the server
        :return:
        """
        return repr(self.internal_connection.recv(4096))

    def close(self):
        """
        Closes the connection
        :return:
        """
        self.internal_connection.close()

    def main(self):
        url = input("choose an option: (start) (settings) (profile): ").encode("utf-8")
        self.internal_connection.send(url)
        response = self.internal_connection.recv(1024).decode("utf-8")
        print(response)


if __name__ == "__main__":
    Client = Client()
    Client.main()

