from math import ceil
import sys

import network_model
import analysis
import model_constants

class MidasArgs:
    def __init__(self, N, B, delay, latency, packet_mode):
        """
        MiDAS codes with improved finite field size

        Params:
         - N: number of arbitrary erasures
         - B: maximum length burst
         - delay: delay for recovery
         - latency: latency of connection one way
         - packet_mode: MTU or single symbol
        """
        self.N = N
        self.B = B
        self.delay = delay
        self.latency = latency
        self.packet_mode = packet_mode

class MiDAS:
    def __init__(self, args, box):
        """
        Params:
         - args: instance of MidasArgs
         - box: instance of NetworkBox class modeling lossy box to travel through
        """
        self.packet_mode = args.packet_mode
        self.N = args.N
        self.B = args.B
        self.delay = args.delay
        self.T = int(self.delay/box.data_transfer_time(
            model_constants.PACKET_HEADER + model_constants.PACKET_PAYLOAD))
        self.T_eff = self.T - 1 
        self.W = self.T
        self.k_u = (self.T_eff - self.N + 1) * self.B
        self.k_v = (self.T_eff - self.N + 1) * (self.T_eff - self.B)
        self.k = self.k_u + self.k_v
        self.R = float(self.T_eff)/(self.T_eff + (float(self.B * self.T)/(self.T - self.N)))
        self.n = ceil(self.k/self.R)
        self.box = box
        self.q = self.T_eff^3
        self.symbol_size = ceil(self.q.bit_length()/8)

    def valid_rate(self):
        """
        Checks if parameters of instance is a valid and possible construction
        """
        bound = (float(self.R)/(1 - self.R)) * self.B + self.N
        bound_met = bound <= self.T_eff + 1 and bound > self.T_eff 
        if bound_met and self.k < model_constants.PACKET_PAYLOAD and self.N <= self.B:
        # if bound_met:
            return True
        else:
            return False
    
    def transmit_source_blocks(self, blocks):
        """
        Transmits source blocks, assumed to be MTU sized packets for now

        Params:
         - block: list of dummy symbols

        Returns 
         - metrics
         - loss
        """
        symbols_per_packet = 0
        if self.packet_mode == model_constants.MTU_PACKETS:
            # use packet that fills MTU size
            symbols_per_packet = ceil(model_constants.PACKET_PAYLOAD/self.symbol_size)
        elif self.packet_mode == model_constants.SYMBOL_PACKETS:
            # each packet is just 1 symbol
            symbols_per_packet = 1
        else:
            print("Packet mode {} not valid, use MTU or SYMBOL".format(self.packet_mode))
            sys.exit(1)
        
        received_packets = []
        all_metrics = []
        for block in blocks:
            # transmit each of the n channel packets
            metrics = analysis.BlockMetrics()
            for i in range(0, self.n, symbols_per_packet):
                if i + symbols_per_packet >= self.n:
                    packet = network_model.Packet(
                        self.n % symbols_per_packet,
                        None,
                        self.symbol_size)
                else:
                    packet = network_model.Packet(
                        symbols_per_packet,
                        None,
                        self.symbol_size)
                received_packets.append(self.box.recv_ge_model.process_packet(packet))
                metrics.bandwidth += packet.packet_size
            metrics.latency += self.box.latency
            metrics.latency += self.delay
            block_k_size = self.k * self.symbol_size
            metrics.bandwidth_overhead = float(metrics.bandwidth - block_k_size)/block_k_size * 100
            all_metrics.append(metrics)
        
        # check if can be recovered from
        print("checking recovery")
        window_start = 0
        window_end = self.W
        loss = 0
        while window_end < len(received_packets):
            bursts = []
            arbitrary = 0
            curr_burst = 0
            window = received_packets[window_start:window_end]
            i = 0
            pkt_size = 0
            while i < len(window):
                if window[i] is None:
                    arbitrary += 1
                    curr_burst += 1
                else:
                    if curr_burst > 1:
                        bursts.append(curr_burst)
                    curr_burst = 0
                    pkt_size = window[i].num_symbols
                i += 1
                # print(i, len(window))

            # print(window, bursts, arbitrary)
            burst_large = len(bursts) > 0 and max(bursts) > self.B 
            burst_many = len(bursts) > 1
            arbitrary_large = arbitrary > self.N
            if burst_large or (burst_many and arbitrary_large) or arbitrary_large:
                # print(burst_and_isolate, burst_large, arbitrary_large)
                # print(window, self.N, self.B)
                loss += pkt_size

            window_start += 1
            window_end += 1
            # print(window_end, len(received_packets))

        return (all_metrics, loss)
