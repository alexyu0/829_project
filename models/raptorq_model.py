import sys
from math import ceil
from enum import Enum

import analysis
import model_constants
import network_model

class RQArgs:
    def __init__(self, k_min, T, packet_type, latency, overhead, rate, delay):
        """
        Params:
         - k_min: minimum size of each source block
         - T: symbol size
         - packet_type: how symbols should be packetized
         - latency: latency of network connection, one way
         - delay: timeout for waiting for repair symbols
         - overhead: configured reception overhead
         - rate: additional protection to be added
        """
        self.k_min = k_min
        self.T = T
        self.packet_type = packet_type
        self.latency = latency
        self.delay = delay
        self.overhead = overhead
        self.rate = rate

class RaptorQ:
    def __init__(self, args, box):
        """
        Params:
         - args: instance of RQArgs
         - box: instance of NetworkBox class modeling lossy box to travel through
        """
        self.packet_mode = args.packet_type # either MTU or SYMBOL
        self.overhead = args.overhead
        self.k_min = args.k_min
        self.box = box
        self.T = args.T
        self.recovery_timeout = args.delay
        self.rate = args.rate

    def form_source_blocks(self, frames):
        """
        PSEUDOCODE FROM: Kumar2013

        Takes a list of streams.Frame instances that represent a stream and form
        them into appropriately sized source blocks

        Params:
         - frames: stream of freames

         Returns:
         - list of source blocks, which are just lists of dummy symbols
         - total number of symbols to be transmitted
        """
        source_blocks = []
        frame_i = 0
        block_symbols_cache = {}
        total_symbols = 0
        while frame_i < len(frames):
            source_block_size = 0
            first_ts = frames[frame_i].ts
            while source_block_size < self.k_min * self.T and frame_i < len(frames):
                source_block_size += frames[frame_i].size
                frame_i += 1
            last_ts = frames[frame_i - 1].ts
            blk_K = ceil(float(source_block_size)/self.T)
            total_symbols += blk_K
            if blk_K not in block_symbols_cache:
                blk_symbols = [model_constants.DUMMY for i in range(0, blk_K)]
                block_symbols_cache[blk_K] = blk_symbols
            source_blocks.append((block_symbols_cache[blk_K], (last_ts - first_ts) * 1000))

        return source_blocks, total_symbols

    def transmit_source_block(self, block_info, rate=None):
        """
        Transmits symbols in a source block

        Params:
         - block: list of dummy symbols and delay from waiting to form block
         - rate: desired K/N ratio

        Returns metrics class instance
        """
        # generate packets
        block, delay = block_info
        K = len(block)
        metrics = analysis.BlockMetrics()
        metrics.latency = delay
        packets = []
        symbols_per_packet = 0
        if self.packet_mode == model_constants.MTU_PACKETS:
            # use packet that fills MTU size
            symbols_per_packet = ceil(model_constants.PACKET_PAYLOAD/self.T)
        elif self.packet_mode == model_constants.SYMBOL_PACKETS:
            # each packet is just 1 symbol
            symbols_per_packet = 1
        else:
            print("Packet mode {} not valid, use MTU or SYMBOL".format(self.packet_mode))
            sys.exit(1)
        
        # packetize source block
        data_bandwidth_use = 0
        for i in range(0, K, symbols_per_packet):
            if i + symbols_per_packet >= K:
                packet = network_model.Packet(
                    K % symbols_per_packet,
                    network_model.PacketType.SOURCE, 
                    self.T)
                packets.append(packet)
                data_bandwidth_use += packet.packet_size
            else:
                packet = network_model.Packet(
                    symbols_per_packet,
                    network_model.PacketType.SOURCE, 
                    self.T)
                packets.append(packet)
                data_bandwidth_use += packet.packet_size

        # packetize repair symbols at given rate
        for i in range(0, int(1.0/rate * K - K), symbols_per_packet):
            if i + symbols_per_packet >= self.overhead:
                packets.append(
                    network_model.Packet(
                        (1.0/rate * K - K) % symbols_per_packet, 
                        network_model.PacketType.REPAIR, 
                        self.T))
            else:
                packets.append(
                    network_model.Packet(
                        symbols_per_packet,
                        network_model.PacketType.REPAIR, 
                        self.T))

        received_packets = []
        for packet in packets:
            received_packets.append(self.box.recv_ge_model.process_packet(packet))
            metrics.bandwidth += packet.packet_size
            metrics.latency += self.box.data_transfer_time(packet.packet_size)
        
        # use corresponding type of receiver/decoder
        received_symbols = 0
        received_source_symbols = 0
        for packet in received_packets:
            if packet is not None:
                received_symbols += packet.num_symbols
                if packet.type == network_model.PacketType.SOURCE:
                    received_source_symbols += packet.num_symbols
        (lost, additional_source) = self.recover(
            metrics, 
            symbols_per_packet, 
            received_symbols - K,
            self.recovery_timeout)
        metrics.latency += self.box.latency
        if lost:
            metrics.lost_symbols += K - received_source_symbols + additional_source

        # compute bandwidth increase
        metrics.bandwidth_overhead = float(metrics.bandwidth - data_bandwidth_use)/data_bandwidth_use * 100

        return metrics
        
    def recover(self, metrics, symbols_per_packet, received_symbols, timeout):
        """
        Receiver and decoding
        """
        # continue until timeout reached
        add_source = 0
        # print(metrics.latency, timeout)
        while metrics.latency < timeout:
            # receive additional symbols up to configured amount
            repair_pkt = network_model.Packet(
                symbols_per_packet, 
                network_model.PacketType.REPAIR, 
                self.T)
            metrics.bandwidth += repair_pkt.packet_size
            metrics.latency += self.box.data_transfer_time(repair_pkt.packet_size)
            repair_recv = self.box.recv_ge_model.process_packet(repair_pkt)
            if repair_recv is not None:
                received_symbols += repair_recv.num_symbols
                if repair_recv.type == network_model.PacketType.SOURCE:
                    add_source += repair_recv.num_symbols
                if received_symbols > self.overhead:
                    break

        if received_symbols < self.overhead:
            return (True, add_source)
            
        # send stop signal 
        signal_pkt = network_model.Packet(0, network_model.PacketType.SIGNAL, self.T)
        metrics.bandwidth += signal_pkt.packet_size
        return (False, 0)
