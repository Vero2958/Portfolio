import struct
# header: Type (1 byte), Operation (1 byte), Sequence (1 byte), User (32 bytes), Length (4 bytes)
# Implementation of protocol methods:


def create_datagram(datagram_type, operation, sequence, username, payload="None"):
    """
    creates a datagram, meant to be used for daemon to daemon communication
    :param datagram_type: could be 1 or 2 based on whether it is a control datagram or a chat datagram.
    :param operation: for chat datagram, default value here, while for control datagrams it specifies if it is an ERR (1),
    a SYN (2), an ACK (4) or a FIN (8).
    :param sequence: sequence number
    :param username: username of the user sanding the datagram
    :param payload: payload of datagram, default is "None". Specify one for type 2 datagrams.
    :return: datagram (header+payload)
    """
    user_field = username.encode('ascii')[:32].ljust(32, b'\x00')
    payload_data = payload.encode('ascii')
    length = len(payload_data)
    header = struct.pack("BBB32sI", datagram_type, operation, sequence, user_field, length)

    return header + payload_data


def parse_datagram(data):
    """
    parse a datagram, meant to be used for daemon to daemon communication
    :param data: datagram to be parsed
    :return: a dictionary representing the datagram
    """
    header = struct.unpack("BBB32sI", data[:40])
    payload = data[40:].decode('ascii')  # Extract payload

    return {
        "Type": header[0],
        "Operation": header[1],
        "Sequence": header[2],
        "User": header[3].decode('ascii').rstrip('\x00'),  # Remove padding
        "Length": header[4],
        "Payload": payload
    }

# add other functions you may need
