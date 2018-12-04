import analysis
import model_constants
import network_model
import raptorq_model
import streams

def run_RQ_simulation(args):
    """
    Runs simulation of using RaptorQ
    """
    # generate stream of frames to use with 1080 60fps for 5 min
    stream_gen = streams.FixedSizeStream(model_constants.RES_1080P, model_constants.FPS_60)
    frames = stream_gen.generate_stream(5 * 60, streams.CompressionType.H_264)

    # initialize GE models and network box
    recv_ge = network_model.GEModel(
        model_constants.p, 
        model_constants.r, 
        model_constants.GOOD_SUCCESS, 
        model_constants.BAD_SUCCESS)
    send_ge = network_model.GEModel(
        model_constants.p, 
        model_constants.r, 
        model_constants.GOOD_SUCCESS, 
        model_constants.BAD_SUCCESS)
    box = network_model.NetworkBox(recv_ge, send_ge, args.latency)

    # use RaptorQ
    print("Running simulation with RaptorQ...")
    print("Using {} frames with size {}...".format(len(frames), frames[0].size))
    rq = raptorq_model.RaptorQ(
        args.packet_type, model_constants.OVERHEAD,
        args.k_min, args.recov_config,
        box, args.T, args.recov_timeout,
        args.timeout_or_signal)
    source_blks, total_symbols = rq.form_source_blocks(frames)
    print("Using {} source blocks...".format(len(source_blks)))
    metrics = []
    for blk in source_blks:
        metrics.append(rq.transmit_source_block(
            blk,
            model_constants.RATE))

    # average metrics
    analysis.analyze(metrics, total_symbols)

def run_simulations():
    """
    Runs all simulations
    """
    rq_args = []
    rq_args.append(raptorq_model.Args(
        250, 16,
        model_constants.MTU_PACKETS,
        50, 500, 
        raptorq_model.ReceiverConfig.FIXED, False))
    for args in rq_args:
        run_RQ_simulation(args)

if __name__ == "__main__":
    run_simulations()
