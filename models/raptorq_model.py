import sys
from math import ceil
from enum import Enum

import analysis
import model_constants
import network_model

class Args:
    def __init__(self, k_min, T, packet_type, latency, recov_timeout, 
                 recov_config, timeout_or_signal):
        self.k_min = k_min
        self.T = T
        self.packet_type = packet_type
        self.latency = latency
        self.recov_timeout = recov_timeout
        self.recov_config = recov_config
        self.timeout_or_signal = timeout_or_signal

class ReceiverConfig(Enum):
    STREAM = 2 # sender streams encoding symbols and signals when done
    FIXED = 3 # sender sends fixed amount of encoding symbols and receiver times out

class RaptorQ:
    def __init__(self, packet_mode, overhead, k_min, receiver_config, box, T,
                 recovery_timeout, timeout_or_signal):
        """
        Params:
         - packet_mode: how symbols should be packetized
         - overhead: configured reception overhead
         - k_min: minimum size of each source block
         - receiver_config: which type of receiver setup to use
         - box: instance of NetworkBox class modeling lossy box to travel through
         - T: symbol size
         - recovery_timeout: timeout for waiting for repair symbols
         - timeout_or_signal: indicates if timeout or signal should be used
        """
        self.packet_mode = packet_mode # either MTU or SYMBOL
        self.overhead = overhead
        self.k_min = k_min
        self.recv_cfg = receiver_config
        self.box = box
        self.timeout = self.box.latency * 3 # should be at least 1 RTT?
        self.T = T
        self.recovery_timeout = recovery_timeout
        self.timeout_or_signal = timeout_or_signal

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
            while source_block_size < self.k_min * self.T:
                source_block_size += frames[frame_i].size
                frame_i += 1
            blk_K = ceil(float(source_block_size)/self.T)
            total_symbols += blk_K
            if blk_K not in block_symbols_cache:
                blk_symbols = [model_constants.DUMMY for i in range(0, blk_K)]
                block_symbols_cache[blk_K] = blk_symbols
            source_blocks.append(block_symbols_cache[blk_K])

        return source_blocks, total_symbols

    def transmit_source_block(self, block, rate=None):
        """
        Transmits symbols in a source block

        Params:
         - block: list of dummy symbols
         - timeout: timeout for waiting for repair symbols, ms
         - rate: desired K/N ratio

        Returns metrics class, consisting of:
         - delay: addidtional symbols needed until recovery         
         - latency: latency spent on recovery
         - bandwidth: bandwidth consumed for recovery
        """
        # generate packets
        K = len(block)
        metrics = analysis.BlockMetrics()
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
                    network_model.PacketType.ENCODE, 
                    self.T)
                packets.append(packet)
                data_bandwidth_use += packet.packet_size
            else:
                packet = network_model.Packet(
                    symbols_per_packet,
                    network_model.PacketType.ENCODE, 
                    self.T)
                packets.append(packet)
                data_bandwidth_use += packet.packet_size

        # packetize repair symbols
        for i in range(0, self.overhead, symbols_per_packet):
            if i + symbols_per_packet >= self.overhead:
                packets.append(
                    network_model.Packet(
                        self.overhead % symbols_per_packet, 
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
            metrics.latency += self.box.latency
        
        # use corresponding type of receiver/decoder
        received_symbols = 0
        for packet in received_packets:
            if packet is not None:
                received_symbols += packet.num_symbols
        if self.recv_cfg == ReceiverConfig.STREAM:
            self.recv_stream(
                metrics, 
                symbols_per_packet, 
                received_symbols - K,
                self.recovery_timeout,
                self.timeout_or_signal)
        elif self.recv_cfg == ReceiverConfig.FIXED:
            lim = 1.0/rate * K * 0.1 # TODO is temp set at 10%
            self.recv_fixed(
                metrics, 
                symbols_per_packet, 
                received_symbols - K, 
                lim,
                self.recovery_timeout,
                self.timeout_or_signal)
        else:
            print("Receiver config {} not valid".format(self.recv_cfg))
            sys.exit(1)

        # compute bandwidth increase
        metrics.bandwidth_overhead = float(metrics.bandwidth)/data_bandwidth_use * 100

        return metrics

    def recv_stream(self, metrics, symbols_per_packet, received_symbols, 
                    recovery_timeout=None, timeout=False):
        """
        Receiver config where receiver streams additional repair symbols until
        it signals the sender for completion.
        Has an optional timeout parameter 
        """
        # continue until K + overhead received
        # TODO: handle timeout
        lost = False
        while received_symbols < self.overhead:
            # receive stream of additional symbols
            if timeout and metrics.latency > recovery_timeout:
                lost = True
                break

            repair_pkt = network_model.Packet(
                symbols_per_packet, 
                network_model.PacketType.REPAIR, 
                self.T)
            metrics.bandwidth += repair_pkt.packet_size
            repair_recv = self.box.recv_ge_model.process_packet(repair_pkt)
            if repair_recv is not None:
                metrics.latency += self.box.latency # send -> recv
                received_symbols += repair_recv.num_symbols

        # calculate lost symbols
        if lost:
            # assume we lose as least as many symbols as the reception overhead
            metrics.lost_symbols = self.overhead - received_symbols

        # send stop signal until received
        signal_pkt = network_model.Packet(0, network_model.PacketType.SIGNAL, self.T)
        signal_recv = self.box.send_ge_model.process_packet(signal_pkt)
        while True:
            metrics.bandwidth += signal_pkt.packet_size
            metrics.latency += self.box.latency * 2 # recv -> send and back for ack
            if signal_recv is not None:
                break
        
    def recv_fixed(self, metrics, symbols_per_packet, received_symbols, 
                   symbol_lim, timeout, signal=False):
        """
        Receiver config where sender sends for a pre-configured amount of
        additional repair symbols based on expected network loss.
        Receiver times out if not enough symbols received and
        Optional argument for receiver to signal recovery completion
        """
        # TODO: handle timeout
        # continue until K + overhead received
        encoding_symbols_sent = 0
        while encoding_symbols_sent < symbol_lim:
            # TODO: how many repair symbols to be sent? symbol per packet size for no
            # receive additional symbols up to configured amount
            repair_pkt = network_model.Packet(
                symbols_per_packet, 
                network_model.PacketType.REPAIR, 
                self.T)
            encoding_symbols_sent += symbols_per_packet
            metrics.bandwidth += repair_pkt.packet_size
            repair_recv = self.box.recv_ge_model.process_packet(repair_pkt)
            if repair_recv is not None:
                metrics.latency += self.box.latency # send -> recv
                received_symbols += repair_recv.num_symbols
                if received_symbols > self.overhead:
                    break

        if received_symbols < self.overhead:
            # assume we lose as least as many symbols as the reception overhead
            metrics.lost_symbols = self.overhead - received_symbols
        else:
            if signal:
                # send stop signal until received
                signal_pkt = network_model.Packet(0, network_model.PacketType.SIGNAL, self.T)
                signal_recv = self.box.send_ge_model.process_packet(signal_pkt)
                while True:
                    metrics.bandwidth += signal_pkt.packet_size
                    metrics.latency += self.box.latency * 2 # recv -> send and back for ack
                    if signal_recv is not None:
                        break
