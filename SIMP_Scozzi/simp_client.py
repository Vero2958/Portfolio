import socket
import threading
import sys
from Daemon_Client_communication_protocol import *
from constants import CDCP_Operations, CDCP_Types


class SimpClient:
    def __init__(self, daemon_ip, daemon_port=7778):
        self.daemon_ip = daemon_ip
        self.daemon_port = daemon_port
        self.username = None
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.queue = []  # Pending requests from the daemon
        self.connected = False
        self.in_chat = False
        self.pending_syn = False
        self.pending_fin = False
        self.received_first_message = False
        self.last_sequence_number_sent = 0
        self.disconnect_request_sent = False
        self.chat_ended = False
        self.last_packet_sent = None
        self.turn = False
        self.received_queue = False   # both this and the following flags are used for queuing
        self.chat_queued = False
        #self.stop_thread = False
        #self.suspend_listener = False
        #self.lock = threading.Lock()

    def start(self):
        """start listen to daemon thread"""
        threading.Thread(target=self.listen_to_daemon, daemon=True).start()
        threading.Event().wait()

    def retransmit(self, packet):
        self.sock.sendto(packet, (self.daemon_ip, self.daemon_port))
        self.sock.settimeout(5)

    def connect_to_daemon(self):
        """connect to daemon"""
        try:
            # build and send test packet
            test_packet = "Hello".encode('ascii')
            print("sending hello")
            self.sock.sendto(test_packet, (self.daemon_ip, self.daemon_port))
            self.last_sequence_number_sent = 0
            self.sock.settimeout(5)
            self.last_packet_sent = test_packet

            # receive and parse response
            response, addr = self.sock.recvfrom(1024)
            header = parse_client_datagram(response)

            # check if response is the expected one, if it is self.connected = True
            if header["Type"] == CDCP_Types.COMMUNICATION.value and header["Operation"] == CDCP_Operations.ACKNOWLEDGMENT.value:
                self.sock.settimeout(None)
                self.connected = True
                print("successfully connected to client")

        except Exception as e:
            print(f"Daemon is not running, run it first. Exception: {e}")
            sys.exit(1)

        except TimeoutError:
            print("Timeout expired in connect to daemon, reattempting retransmission")
            self.connect_to_daemon()


    def register_username(self):
        """Prompts the user for a username and sends it to the daemon."""
        try:
            self.username = input("Enter your username: ").strip()
            reg_packet = build_chat_datagram(CDCP_Operations.REGISTER_USERNAME.value, self.last_sequence_number_sent+1, self.username)
            self.sock.sendto(reg_packet, (self.daemon_ip, self.daemon_port))
            self.sock.settimeout(5)
            self.last_sequence_number_sent += 1
            self.last_packet_sent = reg_packet
            print(f"Username '{self.username}' registered with daemon.")
        except TimeoutError:
            print("Timeout expired in register username, reattempting retransmission")
            self.retransmit(self.last_packet_sent)

    def listen_to_daemon(self):
        """ listen to the daemon """
        try:
            while self.connected:
                data, daemon_addr = self.sock.recvfrom(1024)
                header = parse_client_datagram(data)  # Parse using the correct protocol
                print("got by listen_to_daemon", header)

                # check message type and react consequently:
                if header["Operation"] == CDCP_Operations.REGISTER_USERNAME.value:
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                    self.sock.sendto(ack, daemon_addr)
                    print(f"Incoming chat request from {header['Payload']}")
                    self.queue.append(header)
                    self.handle_queue()

                if header["Operation"] == CDCP_Operations.ACKNOWLEDGMENT.value:
                    self.sock.settimeout(None)
                    print(f"acknowledgment received from daemon for packet {header['Sequence']}")
                    if self.pending_fin and header["Payload"] == "fin request was acknowledged by the other client":
                        self.in_chat = False
                    if self.disconnect_request_sent and header["Payload"] == "acknowledgment, free to disconnect":
                        print("disconnecting")
                        self.connected = False
                    else:
                        print(f"received and acknowledgment for packet {header['Sequence']}")

                if header["Operation"] == CDCP_Operations.CONNECTION_ENDED.value:
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                    self.sock.sendto(ack, daemon_addr)
                    print("other user disconnected, chat is finished. Type whatever you want to leave the chat")
                    self.in_chat = False
                    self.chat_ended = True
                    #self.main()

                if header["Operation"] == CDCP_Operations.ERROR.value:
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                    self.sock.sendto(ack, daemon_addr)
                    print(header["Payload"])

                if header["Operation"] == CDCP_Operations.CONNECTION_REQUEST_REJECTED.value and self.pending_syn:
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                    self.sock.sendto(ack, daemon_addr)
                    print("Connection request was rejected")
                    self.turn = False
                    break

                if header["Operation"] == CDCP_Operations.CONNECTION_ESTABLISHED.value:
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                    self.sock.sendto(ack, daemon_addr)
                    if self.pending_syn:
                        print("connection request was accepted. Connection established")
                        self.in_chat = True
                        self.pending_syn = False
                        self.received_first_message = True
                        print(self.received_first_message)
                        self.chat_loop()
                        break
                    else:
                        print("Connection established")
                        self.in_chat = True
                        print(self.received_first_message)
                        #self.receive_first_message()
                        self.chat_loop()
                        break

                if header["Operation"] == CDCP_Operations.MESSAGE.value:
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                    self.sock.sendto(ack, daemon_addr)
                    print(f"{header['Payload']}")
                    #if not self.received_first_message:
                        #self.received_first_message = True

                if not self.received_queue:
                    self.received_queue = True
                    self.chat_queued = False
                    break
        except TimeoutError:
            print(f"Timeout expired in listen to daemon for packet {self.last_packet_sent}, reattempting retransmission")
            self.retransmit(self.last_packet_sent)

    def handle_queue(self):
        """Processes pending chat requests from the daemon."""
        try:
            # once handle queue is finished, we call self.main again, 'cause to get here we stopped it
            request = self.queue.pop(0)
            print(f"Chat request from {request['Payload']}")
            response = input(f"Do you want to accept chat request from {request['Payload']}? (Y/N): ").strip().lower()
            if response == "y":
                print("Request accepted.")
                accept_packet = build_chat_datagram(CDCP_Operations.RESPONSE.value, self.last_sequence_number_sent + 1, "y")
                self.last_sequence_number_sent += 1
                self.sock.sendto(accept_packet, (self.daemon_ip, self.daemon_port))
                self.sock.settimeout(5)
                self.last_packet_sent = accept_packet
                if self.chat_queued:
                    self.listen_to_daemon()
            elif response == "n":
                print("Request declined.")
                decline_packet = build_chat_datagram(CDCP_Operations.RESPONSE.value, self.last_sequence_number_sent + 1, "n")
                self.last_sequence_number_sent += 1
                self.sock.sendto(decline_packet, (self.daemon_ip, self.daemon_port))
                self.sock.settimeout(5)
                self.last_packet_sent = decline_packet
                self.main()
        except TimeoutError:
            print("Timeout expired in handle queue, reattempting retransmission")
            self.retransmit(self.last_packet_sent)

    def chat_loop(self):
        """ this loop allows users to send messages, until on of the 2 sends 'disconnect' """
        try:
            print("Chat session started! Type your messages below. Type 'disconnect' to end the chat.")
            while self.in_chat:
                msg = None
                if self.in_chat and not self.chat_ended and not self.received_first_message or not self.turn:
                    data, daemon_addr = self.sock.recvfrom(1024)
                    header = parse_client_datagram(data)
                    if header["Operation"] == CDCP_Operations.MESSAGE.value:
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.sock.sendto(ack, daemon_addr)
                        print(f"{header['Payload']}")
                        self.received_first_message = True
                        self.turn = True
                    else:
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.sock.sendto(ack, daemon_addr)
                        print("session ended, other user disconnected")
                        break
                elif self.in_chat and not self.chat_ended and self.received_first_message:
                    self.turn = True
                    msg = input("type: ")
                    # Send chat message
                    # Handle disconnect command
                    if msg == "disconnect":
                        self.turn = False
                        disconnect_packet = build_chat_datagram(CDCP_Operations.DISCONNECT_REQUEST.value, self.last_sequence_number_sent + 1, "disconnect")
                        self.last_sequence_number_sent += 1
                        self.sock.sendto(disconnect_packet, (self.daemon_ip, self.daemon_port))
                        self.sock.settimeout(5)
                        data, daemon_addr = self.sock.recvfrom(1024)
                        header = parse_client_datagram(data)
                        if header["Operation"] == CDCP_Operations.ACKNOWLEDGMENT.value:
                            self.sock.settimeout(None)
                        self.last_packet_sent = disconnect_packet
                        self.pending_fin = True
                        print("Disconnected from chat.")
                        self.in_chat = False
                        break
                    chat_packet = build_chat_datagram(CDCP_Operations.MESSAGE.value, self.last_sequence_number_sent + 1, msg)
                    self.sock.sendto(chat_packet, (self.daemon_ip, self.daemon_port))
                    self.last_sequence_number_sent += 1
                    self.sock.settimeout(5)
                    data, daemon_addr = self.sock.recvfrom(1024)
                    header = parse_client_datagram(data)
                    if header["Operation"] == CDCP_Operations.ACKNOWLEDGMENT.value:
                        self.sock.settimeout(None)
                    self.last_packet_sent = chat_packet
                    self.turn = False
                else:
                    print("\nExiting chat loop.")
                    break

                # Check if in_chat was externally set to False
                if not self.in_chat:
                    break

            print("Returning to main menu...")
            if self.chat_ended:
               self.chat_ended = False
        except TimeoutError:
            print("Timeout expired in chat, reattempting retransmission")
            self.retransmit(self.last_packet_sent)

    def main(self):
        """main function, here users can decide what to do"""
        try:
            while self.connected:
                if not self.received_queue:
                    self.chat_queued = True
                    self.listen_to_daemon()
                else:
                    action = input("Do you want to start a chat? (Y/N/q)").strip().lower()
                    if action == "y":
                        target_ip = input("Enter the IP address of the user you wish to contact: ").strip()
                        connect_packet = build_chat_datagram(CDCP_Operations.CONNECT_REQUEST.value, self.last_sequence_number_sent + 1, target_ip)
                        self.sock.sendto(connect_packet, (self.daemon_ip, self.daemon_port))
                        self.last_sequence_number_sent += 1
                        self.sock.settimeout(5)
                        self.last_packet_sent = connect_packet
                        self.pending_syn = True
                        self.turn = True
                        print("Request sent. Waiting for confirmation...")
                        self.listen_to_daemon()
                    elif action == "n":
                        print("Going idle. Waiting for incoming requests...")
                        self.listen_to_daemon()
                    elif action == "q":
                        quit_packet = build_disconnect_datagram(self.last_sequence_number_sent + 1)
                        self.sock.sendto(quit_packet, (self.daemon_ip, self.daemon_port))
                        self.last_sequence_number_sent += 1
                        self.sock.settimeout(5)
                        self.last_packet_sent = quit_packet
                        print("Bye")
                        sys.exit(0)
                    else:
                        print("Invalid input")
        except TimeoutError:
            print("Timeout expired in main, reattempting retransmission")
            self.retransmit(self.last_packet_sent)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simp_client.py <daemon_ip>")
        sys.exit(1)

    daemon_ip = sys.argv[1]
    client = SimpClient(daemon_ip)
    client.connect_to_daemon()
    client.register_username()
    client.main()
