import model_constants
import random
from enum import Enum

class PacketType(Enum):
    ENCODE = 1
    REPAIR = 2
    REQUEST = 3
    SIGNAL = 4

class Packet:
    def __init__(self, num_symbols, packet_type, T):
        """
        Params:
         - num_symbols: number of symbols represented by this packet
         - is_encode: marks if packet carries encoding or repair symbols
        """
        self.num_symbols = num_symbols
        self.type = packet_type
        self.header_size = model_constants.PACKET_HEADER
        self.payload_size = num_symbols * T
        self.packet_size = self.header_size + self.payload_size

class NetworkBox:
    def __init__(self, recv_ge_model, send_ge_model, latency):
        """
        Params:
         - ge_model: instance of GE model to be used to simulate loss
         - latency: latency for packet to go from one endpoint to another, ms
        """
        self.recv_ge_model = recv_ge_model
        self.send_ge_model = send_ge_model
        self.latency = latency

class GEModel:
    def __init__(self, p, r, g_s, b_s):
        """
        Params:
         - p: probability of state transition G -> B
         - r: probability of state transition B -> G
         - g_s: probability of packet not being dropped in G, or k
         - b_s: probability of packet not being dropped in B, or h
        """
        self.p = model_constants.p if p is None else p
        self.r = model_constants.r if r is None else r
        self.good_success = model_constants.GOOD_SUCCESS if g_s is None else g_s
        self.good_error = 1 - self.good_success # probability of packet being dropped in G
        self.bad_success = model_constants.BAD_SUCCESS if b_s is None else b_s
        self.bad_error = 1 - self.bad_success # probability of packet being dropped in B

        self.state = model_constants.GOOD_STATE # always start in good state

        # set up random generator
        random.seed()
        self.random_gen = random.Random()

    def process_packet(self, pkt):
        # check if state should be transitioned
        state_trans = self.random_gen.uniform(0.0, 1.0)
        if self.state == model_constants.GOOD_STATE and state_trans <= self.p:
            self.state = model_constants.BAD_STATE
        elif self.state == model_constants.BAD_STATE and state_trans <= self.r:
            self.state = model_constants.GOOD_STATE

        # check if packet should be dropped
        drop = self.random_gen.uniform(0.0, 1.0)
        if ((self.state == model_constants.GOOD_STATE and drop <= self.good_error) or
            (self.state == model_constants.BAD_STATE and drop <= self.bad_error)):
            return None
        else:
            return pkt
