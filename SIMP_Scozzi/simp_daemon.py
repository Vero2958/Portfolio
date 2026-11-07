import socket
import sys
import threading
from Simp_Protocol import *
from Daemon_Client_communication_protocol import *
from constants import *

client_port = 7778
daemon_port = 7777


class SimpDaemon:
    def __init__(self, ip, daemon_port=7777, client_port=7778):
        self.ip = ip
        self.daemon_port = daemon_port
        self.client_port = client_port
        self.pending_syn = False
        self.pending_fin = False
        self.last_sequence_number_received = None
        self.last_sequence_number_sent = 0

        # Sockets for client and daemon communication
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.bind((self.ip, self.client_port))
        self.client_socket.settimeout(None)

        self.daemon_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.daemon_socket.bind((self.ip, self.daemon_port))
        self.daemon_socket.settimeout(None)

        # State Management
        self.connected_client = None
        self.client_username = None
        self.chat_queue = []  # Queue for pending chat requests
        self.connected_daemon = None  # Address of the currently connected daemon
        self.busy = False
        self.last_packet_sent = None
        self.last_packet_sent_type = None  # can be either "daemon" or "client"

    def start(self):
        """Start the daemon with concurrent threads."""
        threading.Thread(target=self.connect_to_client).start()
        #threading.Thread(target=self.listen_to_client, daemon=True).start()
        threading.Thread(target=self.listen_to_daemons, daemon=True).start()
        print(f"Daemon running on {self.ip}:{self.daemon_port}")
        threading.Event().wait()

    def retransmit_to_daemon(self, packet):
        self.daemon_socket.sendto(packet, self.connected_daemon)
        self.last_packet_sent = packet
        self.last_packet_sent_type = "daemon"
        self.client_socket.settimeout(5)

    def retransmit_to_client(self, packet):
        self.client_socket.sendto(packet, self.connected_client)
        self.last_packet_sent = packet
        self.last_packet_sent_type = "client"
        self.client_socket.settimeout(5)

    def connect_to_client(self):
        """connect to client"""
        while not self.connected_client:
            data, client_addr = self.client_socket.recvfrom(1024)
            if data.decode('ascii') == "Hello":
                print('received hello from client')
                self.connected_client = client_addr
                ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, 0x00, "acknowledgment")
                self.client_socket.sendto(ack, client_addr)
                self.last_sequence_number_sent = 0
                self.send_queue()  # missing implementation on daemon side
                self.listen_to_client()
            else:
                print("received something in the connect_to_client", data)

    def listen_to_client(self):
        """listen to client's requests"""
        try:
            while self.connected_client:

                # receive data from client and parse it
                data, client_addr = self.client_socket.recvfrom(1024)
                header = parse_client_datagram(data)

                # check which type of data it is:
                if header["Type"] == CDCP_Types.COMMUNICATION.value:
                    if header["Operation"] == CDCP_Operations.REGISTER_USERNAME.value:  # register username
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.client_socket.sendto(ack, client_addr)
                        self.client_username = header["Payload"]
                        print(f"Registered username: {self.client_username}")
                    elif header["Operation"] == CDCP_Operations.CONNECT_REQUEST.value:  # connect to another user request
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.client_socket.sendto(ack, client_addr)
                        print(f"Sending syn to {header["Payload"]} and sent ask back to user")
                        chat_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.SYN.value, header["Sequence"], self.client_username, header["Payload"])
                        self.connected_daemon = (header["Payload"], self.daemon_port)
                        self.daemon_socket.sendto(chat_packet, self.connected_daemon)
                        self.last_packet_sent = chat_packet
                        self.last_packet_sent_type = "daemon"
                        self.daemon_socket.settimeout(5)
                        self.pending_syn = True
                    elif header["Operation"] == CDCP_Operations.MESSAGE.value:  # message, user should be in chat
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.client_socket.sendto(ack, client_addr)
                        if self.connected_daemon:
                            print(f"Relaying message to {self.connected_daemon}: {header['Payload']}")
                            chat_packet = create_datagram(SIMP_Types.CHAT.value, 0x01, header["Sequence"], self.client_username, header["Payload"])
                            self.daemon_socket.sendto(chat_packet, self.connected_daemon)
                            self.last_packet_sent = chat_packet
                            self.last_packet_sent_type = "daemon"
                            self.daemon_socket.settimeout(5)
                        else:
                            print("no connected daemon, sending error message back to client")
                            error_packet = build_chat_datagram(CDCP_Operations.ERROR.value, self.last_sequence_number_sent + 1, "no daemon connected, no client to forward message to")
                            self.client_socket.sendto(error_packet, client_addr)
                            self.last_packet_sent = error_packet
                            self.last_packet_sent_type = "client"
                            self.client_socket.settimeout(5)
                            self.last_sequence_number_sent += 1
                    elif header["Operation"] == CDCP_Operations.DISCONNECT_REQUEST.value:
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.client_socket.sendto(ack, client_addr)
                        if self.busy:
                            print("user wishes to disconnect from current chat, forwarding fin request to other daemon")
                            fin_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.FIN.value, self.last_sequence_number_sent + 1, self.client_username, "disconnect from chat request")
                            self.daemon_socket.sendto(fin_packet, self.connected_daemon)
                            self.last_packet_sent = fin_packet
                            self.last_packet_sent_type = "daemon"
                            self.daemon_socket.settimeout(5)
                            self.pending_fin = True
                            self.last_sequence_number_sent += 1
                    elif header["Operation"] == CDCP_Operations.RESPONSE.value:  # this case means we previously got a syn request from another daemon
                        ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment")
                        self.client_socket.sendto(ack, client_addr)

                        # check payload to find out user decision:
                        if header["Payload"] == "y":  # sending a syn to complete 3 way handshake, ack sent already
                            print("received user decision on incoming pending request, request was accepted")
                            conf_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.SYN.value, header["Sequence"], self.client_username, header["Payload"])
                            self.daemon_socket.sendto(conf_packet, self.connected_daemon)
                            self.last_packet_sent = conf_packet
                            self.last_packet_sent_type = "daemon"
                            self.daemon_socket.settimeout(5)
                            self.busy = True
                            user_packet = build_chat_datagram(CDCP_Operations.CONNECTION_ESTABLISHED.value, self.last_sequence_number_sent + 1, "connection established")
                            self.client_socket.sendto(user_packet, client_addr)
                            self.last_packet_sent = user_packet
                            self.last_packet_sent_type = "client"
                            self.client_socket.settimeout(5)
                            self.last_sequence_number_sent += 1
                        elif header["Payload"] == "n":
                            print("received user decision on incoming pending request, request was rejected")
                            fin_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.FIN.value, header["Sequence"], self.client_username, header["Payload"])
                            self.daemon_socket.sendto(fin_packet, self.connected_daemon)
                            self.last_packet_sent = fin_packet
                            self.last_packet_sent_type = "daemon"
                            self.daemon_socket.settimeout(5)
                        else:
                            print("received user decision on incoming pending request, but response is invalid, sending error message")
                    elif header["Operation"] == CDCP_Operations.ACKNOWLEDGMENT.value:  # ack
                        self.client_socket.settimeout(None)
                        print(f"acknowledgment received from client for packet {header['Sequence']}")
                elif header["Type"] == CDCP_Types.DISCONNECT.value:
                    print("received disconnect request")
                    ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "acknowledgment, free to disconnect")
                    self.client_socket.sendto(ack, client_addr)
                    print("acknowledgment sent, client can disconnect")
                    self.connected_client = None
                    self.client_username = None
                else:
                    print("received something wrong, check client implementation", data)
        except TimeoutError:
            print("Timeout expired in listen to client, attempting retransmission")
            if self.last_packet_sent_type == "daemon":
                self.retransmit_to_daemon(self.last_packet_sent)
            else:
                self.retransmit_to_client(self.last_packet_sent)


    def listen_to_daemons(self):
        """listen to daemon's requests"""
        try:
            while True:

                # receive data from other daemons and parse it
                data, daemon_addr = self.daemon_socket.recvfrom(1024)
                header = parse_datagram(data)

                # check data type:
                if header["Type"] == SIMP_Types.CONTROL.value:  # control datagram

                    # check operation for control datagram and react accordingly
                    if header["Operation"] == SIMP_Operations.ERR.value and header["Payload"] == "client not in chat anymore":  # error datagram
                        pass
                    elif header["Operation"] == SIMP_Operations.ERR.value and header["Payload"] == "client disconnected":
                        pass
                    elif header["Operation"] == SIMP_Operations.SYN.value:
                        if self.pending_syn and self.connected_client:
                            ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                            self.daemon_socket.sendto(ack, daemon_addr)  # last ack of 3-way handshake
                            self.pending_syn = False
                            print("client's connection request was accepted")
                            self.busy = True
                            self.connected_daemon = daemon_addr
                            user_conf_packet = build_chat_datagram(CDCP_Operations.CONNECTION_ESTABLISHED.value, header["Sequence"], "connection established")
                            self.client_socket.sendto(user_conf_packet, self.connected_client)
                            self.last_packet_sent = user_conf_packet
                            self.last_packet_sent_type = "client"
                            self.client_socket.settimeout(5)
                        elif not self.pending_syn and self.connected_client:
                            ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                            self.daemon_socket.sendto(ack, daemon_addr)
                            if self.busy:
                                print(f"Rejecting request from {daemon_addr} (busy)")
                                '''err_packet = create_datagram(0x01, 0x01, self.last_sequence_number_sent + 1, "Daemon", "User busy")
                                self.daemon_socket.sendto(err_packet, daemon_addr)
                                self.last_packet_sent = err_packet
                                self.last_packet_sent_type = "daemon"
                                self.daemon_socket.settimeout(5)
                                self.last_sequence_number_sent += 1'''
                                fin_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.FIN.value, self.last_sequence_number_sent + 1, "Daemon")
                                self.daemon_socket.sendto(fin_packet, daemon_addr)
                                self.last_packet_sent = fin_packet
                                self.last_packet_sent_type = "daemon"
                                self.daemon_socket.settimeout(5)
                                self.last_sequence_number_sent += 1
                            else:
                                print(f"Forwarding request from {header['User']} to client.")
                                packet = build_chat_datagram(CDCP_Operations.REGISTER_USERNAME.value, header["Sequence"], header["User"])
                                self.client_socket.sendto(packet, self.connected_client)
                                self.last_packet_sent = packet
                                self.last_packet_sent_type = "client"
                                self.client_socket.settimeout(5)
                                self.connected_daemon = daemon_addr
                        elif not self.connected_client:
                            if len(self.chat_queue) == 0:
                                print(f"queuing request from {header['User']} at {daemon_addr}")
                                ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], "None","Acknowledgment")
                                self.daemon_socket.sendto(ack, daemon_addr)
                                packet = build_chat_datagram(CDCP_Operations.REGISTER_USERNAME.value, header["Sequence"], header["User"])
                                self.chat_queue.append(packet)
                                self.connected_daemon = daemon_addr
                            else:
                                print(f"Rejecting request from {daemon_addr} (client disconnected and another pending request already present)")
                                #err_packet = create_datagram(0x01, 0x01, self.last_sequence_number_sent + 1, "Daemon","User disconnected and another pending request already present")
                                #self.daemon_socket.sendto(err_packet, daemon_addr)
                                #self.last_packet_sent = err_packet
                                #self.last_packet_sent_type = "daemon"
                                #self.daemon_socket.settimeout(5)
                                #self.last_sequence_number_sent += 1
                                ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], "None", "Acknowledgment")
                                self.daemon_socket.sendto(ack, daemon_addr)
                                fin_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.FIN.value, self.last_sequence_number_sent + 1, "Daemon", "user is disconnected and has already another pending request")
                                self.daemon_socket.sendto(fin_packet, daemon_addr)
                                self.last_packet_sent = fin_packet
                                self.last_packet_sent_type = "daemon"
                                self.daemon_socket.settimeout(5)
                                self.last_sequence_number_sent += 1
                    elif header["Operation"] == SIMP_Operations.ACK.value:  # ack, nothing to be done
                        if self.pending_fin:  # send a confirmation that the other user knows client is leaving
                            self.daemon_socket.settimeout(None)
                            print("received acknowledgment to fin request, client can now leave the connection")
                            self.busy = False
                            ack = build_chat_datagram(CDCP_Operations.ACKNOWLEDGMENT.value, header["Sequence"], "fin request was acknowledged by the other client")
                            self.client_socket.sendto(ack, self.connected_client)
                            self.pending_fin = False
                        else:
                            self.daemon_socket.settimeout(None)
                            print(f"received acknowledgment for packet {header['Sequence']}")
                    elif header["Operation"] == SIMP_Operations.FIN.value:  # Fin packet
                        if self.pending_syn:
                            print("client's connection request was rejected")
                            ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                            self.daemon_socket.sendto(ack, daemon_addr)
                            self.pending_syn = False
                            user_conf_packet = build_chat_datagram(CDCP_Operations.CONNECTION_REQUEST_REJECTED.value, header["Sequence"], "connection rejected")
                            self.client_socket.sendto(user_conf_packet, self.connected_client)
                            self.last_packet_sent = user_conf_packet
                            self.last_packet_sent_type = "client"
                            self.client_socket.settimeout(5)
                            self.connected_daemon = None
                        elif self.busy:
                            print("other client wishes to close the connection, received a FIN")
                            ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                            self.daemon_socket.sendto(ack, daemon_addr)

                            # inform the client
                            fin_user_packet = build_chat_datagram(CDCP_Operations.CONNECTION_ENDED.value, self.last_sequence_number_sent + 1, "Received a fin request from other daemon")
                            self.client_socket.sendto(fin_user_packet, self.connected_client)
                            self.last_packet_sent = fin_user_packet
                            self.last_packet_sent_type = "client"
                            self.client_socket.settimeout(5)
                            self.busy = False
                            self.connected_daemon = None
                elif header["Type"] == SIMP_Types.CHAT.value:  # chat datagram
                    if self.connected_client and self.busy:  # client connected and in chat
                        ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                        self.daemon_socket.sendto(ack, daemon_addr)
                        print(f"forwarding chat message to client: {header['Payload']}")
                        packet = build_chat_datagram(SIMP_Types.CHAT.value, header["Sequence"], header["User"] + ": " + header["Payload"])
                        self.client_socket.sendto(packet, self.connected_client)
                        self.last_packet_sent = packet
                        self.last_packet_sent_type = "client"
                        self.client_socket.settimeout(5)
                    elif self.connected_client and not self.busy:  # client connected but not in chat anymore
                        print(f"client is not in chat anymore")
                        ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                        self.daemon_socket.sendto(ack, daemon_addr)
                        error_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ERR.value, self.last_sequence_number_sent + 1, self.client_username, "client not in chat anymore")
                        self.daemon_socket.sendto(error_packet, daemon_addr)
                        self.last_packet_sent = error_packet
                        self.last_packet_sent_type = "daemon"
                        self.daemon_socket.settimeout(5)
                        self.last_sequence_number_sent += 1
                    elif not self.connected_client:  # client is currently disconnected from daemon
                        print(f"client is not in chat anymore")
                        ack = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ACK.value, header["Sequence"], self.client_username, "Acknowledgment")
                        self.daemon_socket.sendto(ack, daemon_addr)
                        error_packet = create_datagram(SIMP_Types.CONTROL.value, SIMP_Operations.ERR.value, self.last_sequence_number_sent + 1, self.client_username, "client disconnected")
                        self.daemon_socket.sendto(error_packet, daemon_addr)
                        self.last_packet_sent = error_packet
                        self.last_packet_sent_type = "daemon"
                        self.daemon_socket.settimeout(5)
                        self.last_sequence_number_sent += 1
                else:
                    print("received something wrong from another daemon, check listen_to_client function", data)
        except TimeoutError:
            print("Timeout expired in listen to daemon, attempting retransmission")
            if self.last_packet_sent_type == "daemon":
                self.retransmit_to_daemon(self.last_packet_sent)
            else:
                self.retransmit_to_client(self.last_packet_sent)

    def send_queue(self):
        """send queue to the client"""
        if len(self.chat_queue) == 1:
            self.client_socket.sendto(self.chat_queue[0], self.connected_client)
            self.chat_queue.clear()
        else:  # can be only 1 or 0
            self.client_socket.sendto("None".encode('ascii'), self.connected_client)



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python simp_daemon.py <IP_ADDRESS>")
        sys.exit(1)

    ip_address = sys.argv[1]
    daemon = SimpDaemon(ip_address)
    daemon.start()
