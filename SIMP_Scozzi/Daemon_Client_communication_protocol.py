import struct
#from Simp_Daemon import client_port, daemon_port
# functions that regulate communication between Client and Daemon:


def build_chat_datagram(operation, sequence, payload):
    """
    builds a chat datagram, meant to be used by the client to build datagram to send to the daemon
    :param operation: type of operation, could be
    1 for a "connect to another user" request,
    0 for a register username request,
    2 for a "message",
    3 for a "disconnect from user" request,
    4 for a response to a pending request (client-daemon),
    5 to inform client that his request was accepted/ connection is established.
    6 to inform that it was rejected,
    7 for ack.
    8 for error.
    9 to inform that a connection was finished (no matter if requested by them or by the other user and accepted by client)
    :param sequence: sequence number
    :param payload: in operation 1, IP address of the user to connect to, in case 2 the message the user wants to send
    to the other user, in case 3 there's no payload
    :return: datagram (header+payload)
    """
    payload_data = payload.encode('ascii')
    header = struct.pack("BBB", 0x01, operation, sequence)
    return header + payload_data


def parse_client_datagram(datagram):
    """
    parse chat datagram, meant to be used by the daemon to parse client's datagram
    :param datagram: the datagram to be parsed
    :return: a dictionary containing the decoded datagram fields
    """
    header = struct.unpack("BBB", datagram[:3])
    payload = datagram[3:].decode('ascii')  # Extract payload

    return {
        "Type": header[0],
        "Operation": header[1],
        "Sequence": header[2],
        "Payload": payload
    }


def build_disconnect_datagram(sequence):
    """
    builds a simple disconnect datagram, meant to be used by the client to build datagram to send to the daemon
    :param sequence: sequence number
    :return: datagram (header+payload)
    """
    header = struct.pack("BBB", 0x02, 0x00, sequence)
    payload_data = "leave chat request".encode('ascii')
    return header + payload_data

