# starting point for the app
import client
import server
#import user

if __name__ == "__main__":
    #User = user.User()
    s = server.Server()
    s.internal_connection.bind(("localhost", 9000))
    s.internal_connection.listen()
    s, address = s.internal_connection.accept()
    print(f"Started server on port 9000")
    Client = client.Client()
    Client.main()
    action = s.recv(1024).decode("utf-8")
    if action == "start":
        #if len(user.User.user) == 1:
            #msg = f"Hello {user.User.user[0].name}, what do you want to do today?".encode("utf-8")
            #s.send(msg)
        #else:
        msg = "Welcome".encode("utf-8")
        s.send(msg)
            #user = user.User()
    #Client.main()
