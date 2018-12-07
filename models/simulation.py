import os
import argparse
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

def run_RQ_simulation(ge_args, rq_args, trace_dir):
    """
    Runs simulation of using RaptorQ
    """
    # generate stream of frames to use with 1080 60fps for 5 min
    print("Running simulation with RaptorQ...")
    with open("TEMP_RES_RQ", "a+") as f:
        f.write("Running simulation with RaptorQ...\n")
    
    recv_ge = network_model.GEModel(ge_args)
    box = network_model.NetworkBox(recv_ge, rq_args.latency, model_constants.RATE_5Mbps)
    rq = raptorq_model.RaptorQ(rq_args, box)
    stream_gen = streams.FixedSizeStream(model_constants.RES_1080P, model_constants.FPS_60)
    for trace_path in os.listdir(trace_dir):
        if ".swp" in trace_path:
            continue

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
    analysis.analyze(metrics, total_symbols, "RQ")

def run_streaming_simulation(ge_args, m_args, trace_dir):
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
    with open("TEMP_RES_MiDAS", "a+") as f:
        f.write("Running simulation with MiDAS...\n")
        f.write("Parameters are N = {}, B = {}, T = {}\n".format(midas.N, midas.B, midas.T))
    # generate stream of frames to use with 1080 60fps for 5 min
    stream_gen = streams.FixedSizeStream(model_constants.RES_1080P, model_constants.FPS_60)
    for trace_path in os.listdir(trace_dir):
        if ".swp" in trace_path:
            continue

        frames = stream_gen.from_trace(os.path.abspath(trace_dir + "/" + trace_path))

        # initialize GE models and network box
        midas.box.recv_ge_model = network_model.GEModel(ge_args)

        # use streaming
        print("Using {} frames with size {}...".format(len(frames), frames[0].size))
        metrics, loss = midas.transmit_source_blocks(frames)

    # average metrics
    analysis.analyze(metrics, len(frames) * midas.k, "MiDAS", latency=midas.box.latency, total_lost=loss)
    print(loss)
    # analysis.analyze_latency(metrics, len(frames) * midas.k)
    # analysis.analyze_bandwidth(metrics, len(frames) * midas.k)
    # analysis.analyze_loss(metrics, len(frames) * midas.k)

def run_simulations(args):
    """
    Runs all simulations
    """
    ge_args = [
        network_model.GEArgs(0.01, 0.5, 1, 0, "Flach2013_params"),
        # network_model.GEArgs(0.0058, 0.3613, 0.9997, 0.4053, "Kumar2013_params_1"),
        # network_model.GEArgs(0.018, 0.2401, 0.9994, 0.2946, "Kumar2013_params_5"),
        # network_model.GEArgs(0.0279, 0.209, 0.9944, 0.177, "Kumar2013_params_10"), 
        # network_model.GEArgs(0.0461, 0.168, 0.9884, 0.108, "Kumar2013_params_20")
    ]
    if args.baseline:
        for ge_arg_set in ge_args:
            baseline_loss_traces(ge_arg_set, os.path.abspath("models/video_traces"))
    elif args.raptorq:
        if os.path.exists("TEMP_RES_RQ"):
            os.remove("TEMP_RES_RQ")
        rq_args = [
            raptorq_model.RQArgs(
                250, 16,
                model_constants.MTU_PACKETS, 50,
                model_constants.RQ_OVERHEAD, model_constants.RQ_RATE, 100),
            raptorq_model.RQArgs(
                250, 16,
                model_constants.MTU_PACKETS, 50,
                model_constants.RQ_OVERHEAD, model_constants.RQ_RATE, 50)
        ]
        for ge_arg_set in ge_args:
            for rq_arg_set in rq_args:
                run_RQ_simulation(ge_arg_set, rq_arg_set, os.path.abspath("models/video_traces"))
    elif args.streaming:
        if os.path.exists("TEMP_RES_MiDAS"):
            os.remove("TEMP_RES_MiDAS")
        m_args = []
        for N in range(1, 35):
            for B in range(1, 35):
                m_args.append(midas_streaming_model.MidasArgs(N, B, 100, 50, model_constants.MTU_PACKETS))
        for ge_arg_set in ge_args:
            for m_arg_set in m_args:
                run_streaming_simulation(ge_arg_set, m_arg_set, os.path.abspath("models/video_traces"))

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
parser = argparse.ArgumentParser(prog="PROG",
    description="848 Project Code and Loss Simulations",
    usage="python run_analysis.py",
    formatter_class=formatter)
parser.set_defaults(func=run_simulations)

required_args = parser.add_argument_group("required")
required_args.add_argument("-B", "--baseline",
    action="store_true",
    help="baseline simulation on video traces\n")
required_args.add_argument("-R", "--raptorq",
    action="store_true",
    help="simulation with RaptorQ\n")
required_args.add_argument("-S", "--streaming",
    action="store_true",
    help="simulation with streaming codes (MiDAS)\n")

if __name__ == "__main__":
    args = parser.parse_args()
    args.func(args)
