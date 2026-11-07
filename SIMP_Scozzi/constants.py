from enum import Enum

# SIMP protocol types:
class SIMP_Operations(Enum):
    SYN = 0x02
    ERR = 0x01
    ACK = 0x04
    FIN = 0x08


# client-daemon communication protocol (CDCP) types:
class CDCP_Operations(Enum):
    REGISTER_USERNAME = 0x00
    CONNECT_REQUEST = 0x01
    MESSAGE = 0x02
    DISCONNECT_REQUEST = 0x03
    RESPONSE = 0x04
    CONNECTION_ESTABLISHED = 0x05
    CONNECTION_REQUEST_REJECTED = 0x06
    ACKNOWLEDGMENT = 0x07
    ERROR = 0x08
    CONNECTION_ENDED = 0x09


class SIMP_Types(Enum):
    CONTROL = 0x01
    CHAT = 0x02


class CDCP_Types(Enum):
    COMMUNICATION = 0x01
    DISCONNECT = 0x02
