import socket
#from user import User


class Server:
    def __init__(self):
        self.internal_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.internal_connection.bind(("localhost", 9000))
        self.internal_connection.listen()
        self.internal_connection, address = self.internal_connection.accept()

        #if self.path == "start":
            #self.send_response(200, "Hello Veronica, what do you want to do today?")


if __name__ == "__main__":
    s = Server()
    print(f"Started server on port 9000")
    #action = s.recv(1024).decode("utf-8")
    #if action == "start":
        #if len(User.user) == 1:
            #msg = f"Hello {User.user[0].name}, what do you want to do today?".encode("utf-8")
            #s.send(msg)
        #else:
        #msg = "Welcome".encode("utf-8")
        #s.send(msg)
            #user = User()
