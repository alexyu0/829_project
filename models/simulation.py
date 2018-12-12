import os
import argparse
import csv
from collections import defaultdict

import analysis
import model_constants
import network_model
import raptorq_model
import midas_streaming_model
import streams
import loss_stats

def baseline_loss_traces(ge_args, trace_dir):
    """
    Runs loss model on the video traces
    """
    # run trace through GE model and observe loss patterns
    stream_gen = streams.FixedSizeStream(model_constants.RES_1080P, model_constants.FPS_60)
    loss_hists = []
    loss_timescales = []
    for trace_path in os.listdir(trace_dir):
        if ".swp" in trace_path:
            continue

        pkts = stream_gen.from_trace(os.path.abspath(trace_dir + "/" + trace_path))

        # initialize GE models and network box
        recv_ge = network_model.GEModel(ge_args)
        box = network_model.NetworkBox(recv_ge, 0, model_constants.RATE_5Mbps)

        # run 
        loss_hist = defaultdict(int)
        time_buckets = []
        data_buckets = []
        in_burst = False
        burst_len = 0
        bucketStart = 0
        nextBucket = bucketStart + model_constants.BUCKET_SIZE
        curr_data_bucket = 0
        for pkt in pkts:
            res = box.recv_ge_model.process_packet(pkt)
            if res == None:
                in_burst = True
                burst_len += 1
                curr_data_bucket += 1
            else:
                if in_burst:
                    loss_hist[burst_len] += 1
                    burst_len = 0
                    in_burst = False

            if pkt.ts >= nextBucket:
                time_buckets.append(nextBucket)  # Append x-axis point.
                nextBucket += model_constants.BUCKET_SIZE  # Go to next bucket.
                data_buckets.append(curr_data_bucket)  # Append y-axis point.
                curr_data_bucket = 0  # Reset y-axis sum.
        loss_hists.append(loss_hist)
        loss_timescales.append((time_buckets, data_buckets))

    # graph it
    print("calculating averages for {}...".format(ge_args.args_name))
    avg_loss_bursts = loss_stats.compute_average_hist(loss_hists)
    avg_loss_timescale = loss_stats.compute_average_timescale(loss_timescales)
    loss_stats.graph_hist(avg_loss_bursts, "", ge_args.args_name, os.path.abspath("models/graphs"))
    loss_stats.graph_loss_timescale(avg_loss_timescale, "", ge_args.args_name, os.path.abspath("models/graphs"))
    print("...done")

def run_RQ_simulation(ge_args, rq_args, trace_dir, csv_path):
    """
    Runs simulation of using RaptorQ
    """
    # generate stream of frames to use with 1080 60fps for 5 min
    print("Running simulation with RaptorQ...")
    
    recv_ge = network_model.GEModel(ge_args)
    box = network_model.NetworkBox(recv_ge, rq_args.latency, model_constants.RATE_5Mbps)
    rq = raptorq_model.RaptorQ(rq_args, box)
    stream_gen = streams.FixedSizeStream(model_constants.RES_1080P, model_constants.FPS_60)
    
    trace_path = "cbr2500.txt"
    # for trace_path in os.listdir(trace_dir):
    #     if ".swp" in trace_path:
    #         continue

    frames = stream_gen.from_trace(os.path.abspath(trace_dir + "/" + trace_path))

    # initialize new GE models
    rq.box.recv_ge_model = network_model.GEModel(ge_args)

    # use RaptorQ
    print("Using {} frames with size {}...".format(len(frames), frames[0].size))
    source_blks, total_symbols = rq.form_source_blocks(frames)
    print("Using {} source blocks...".format(len(source_blks)))
    metrics = []
    for blk in source_blks:
        metrics.append(rq.transmit_source_block(
            blk,
            model_constants.RQ_RATE))

    # average metrics
    analysis.analyze(metrics, total_symbols, "RQ", rq, csv_path)

def run_streaming_simulation(ge_args, m_args, trace_dir, csv_path):
    """
    Runs simulation of using MiDAS
    """
    print("Running simulation with MiDAS...")

    recv_ge = network_model.GEModel(ge_args)
    box = network_model.NetworkBox(recv_ge, m_args.latency, model_constants.RATE_5Mbps)
    midas = midas_streaming_model.MiDAS(m_args, box)
    if not midas.valid_rate():
        print("not valid set of parameter, skipping")
        return
    print("Parameters are N = {}, B = {}, T = {}".format(midas.N, midas.B, midas.T))
    
    # generate stream of frames to use with 1080 60fps for 5 min
    stream_gen = streams.FixedSizeStream(model_constants.RES_1080P, model_constants.FPS_60)
    trace_path = "cbr2500.txt"
    # for trace_path in os.listdir(trace_dir):
    #     if ".swp" in trace_path:
    #         continue

    frames = stream_gen.from_trace(os.path.abspath(trace_dir + "/" + trace_path))

    # initialize GE models and network box
    midas.box.recv_ge_model = network_model.GEModel(ge_args)

    # use streaming
    print("Using {} frames with size {}...".format(len(frames), frames[0].size))
    metrics, loss = midas.transmit_source_blocks(frames)

    # average metrics
    analysis.analyze(metrics, len(frames) * midas.k, "MiDAS", midas, csv_path,
        latency=midas.box.latency, total_lost=loss)

def raptorq_wrapper(ge_args):
    rq_args = []
    for K_min in [50, 100, 150, 200, 250, 300, 350, 400, 450, 500]:
        for rate in [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]:
            rq_args.append(raptorq_model.RQArgs(
                K_min, 16,
                model_constants.MTU_PACKETS, 50,
                model_constants.RQ_OVERHEAD, rate, 100))
    for latency in model_constants.LATENCY_VALS:
        for i in range(0, len(ge_args)):
            ge_arg_set = ge_args[i]
            csv_path = model_constants.RQ_CSV_PATH.format(latency, i + 1)
            with open(csv_path, mode="w") as f:
                f_writer = csv.writer(f, delimiter=',', quotechar='"', 
                    quoting=csv.QUOTE_MINIMAL)
                f_writer.writerow(["K_min", "Rate", "Delay", "Packet latency (ms)",
                    "Latency (ms)", "Bandwidth increase (%)", "Loss rate (%)"])

            for rq_arg_set in rq_args:
                rq_arg_set.latency = latency
                run_RQ_simulation(ge_arg_set, rq_arg_set, 
                    os.path.abspath("models/video_traces"), csv_path)

def streaming_wrapper(ge_args):
    m_args = []
    for N in range(1, 20):
        for B in range(2, 20):
            m_args.append(midas_streaming_model.MidasArgs(N, B, 100, 50, model_constants.MTU_PACKETS))
    for latency in model_constants.LATENCY_VALS:
        for i in range(0, len(ge_args)):
            ge_arg_set = ge_args[i]
            csv_path = model_constants.MIDAS_CSV_PATH.format(latency, i + 1)
            with open(csv_path, mode="w") as f:
                f_writer = csv.writer(f, delimiter=',', quotechar='"', 
                    quoting=csv.QUOTE_MINIMAL)
                f_writer.writerow(["N", "B", "T", "Packet latency (ms)", "R", "k", "n",
                    "Frame latency (ms)", "Bandwidth increase (%)", "Loss rate (%)"])

            for m_arg_set in m_args:
                m_arg_set.latency = latency
                run_streaming_simulation(ge_arg_set, m_arg_set, 
                    os.path.abspath("models/video_traces"), csv_path)

def run_simulations(args):
    """
    Runs all simulations
    """
    ge_args = [
        network_model.GEArgs(0.01, 0.5, 1, 0, "Flach2013_params"),
        network_model.GEArgs(0.018, 0.2401, 0.9994, 0.2946, "Kumar2013_params_5"),
        network_model.GEArgs(0.0279, 0.209, 0.9944, 0.177, "Kumar2013_params_10"), 
        network_model.GEArgs(0.0461, 0.168, 0.9884, 0.108, "Kumar2013_params_20")
    ]
    if args.overwrite:
        if args.baseline:
            for ge_arg_set in ge_args:
                baseline_loss_traces(ge_arg_set, os.path.abspath("models/video_traces"))
        elif args.raptorq:
            raptorq_wrapper(ge_args)
        elif args.streaming:
            streaming_wrapper(ge_args)
        elif args.all:
            raptorq_wrapper(ge_args)
            streaming_wrapper(ge_args)
        elif args.individual:
            analysis.rq_argset_results("latency")
            analysis.rq_argset_results("loss")
            analysis.rq_argset_results("bw")
            analysis.midas_argset_results("latency")
            analysis.midas_argset_results("loss")
            analysis.midas_argset_results("bw")
        elif args.normalized:
            # analysis.normalized_results("RQ")
            # analysis.normalized_results("MiDAS")
            analysis.normalized_results()
        elif args.graph:
            analysis.graph()

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
parser = argparse.ArgumentParser(prog="PROG",
    description="848 Project Code and Loss Simulations",
    usage="python run_analysis.py",
    formatter_class=formatter)
parser.set_defaults(func=run_simulations)

required_args = parser.add_argument_group("required")
model_args = parser.add_mutually_exclusive_group(required=True)
model_args.add_argument("-B", "--baseline",
    action="store_true",
    help="baseline simulation on video traces\n")
model_args.add_argument("-R", "--raptorq",
    action="store_true",
    help="simulation with RaptorQ\n")
model_args.add_argument("-S", "--streaming",
    action="store_true",
    help="simulation with streaming codes (MiDAS)\n")
model_args.add_argument("-A", "--all",
    action="store_true",
    help="simulation with streaming codes (MiDAS) and RaptorQ\n")
model_args.add_argument("-I", "--individual",
    action="store_true",
    help="calculate best result from each arg set/CSV file for individual metrics\n")
model_args.add_argument("-N", "--normalized",
    action="store_true",
    help="calculate best result from each arg set/CSV file for normalized metric\n")
model_args.add_argument("-G", "--graph",
    action="store_true",
    help="graphs everything\n")
required_args.add_argument("--overwrite",
    action="store_true",
    help="overwrite existing CSVs with new analyses results\n")


if __name__ == "__main__":
    args = parser.parse_args()
    args.func(args)
