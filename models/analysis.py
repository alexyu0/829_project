
class BlockMetrics:
    def __init__(self):
        self.latency = 0 # units - ms
        self.bandwidth = 0 # units - bytes
        self.bandwidth_overhead = 0.0 # units - % increase
        self.lost_symbols = 0 # units - symbols
        # self.delay = 0 # units - symbols

def analyze(metrics, total_symbols):
    """
    Analyzes given metrics and averages over it

    Params:
        - metrics: list of BlockMetrics instances from each source block
    """
    avg_latency = 0.0
    avg_bandwidth = 0.0
    avg_bandwidth_overhead = 0.0
    avg_lost_symbols = 0.0
    for metric in metrics:
        avg_latency += float(metric.latency)
        avg_bandwidth += float(metric.bandwidth)
        avg_bandwidth_overhead += float(metric.bandwidth_overhead)
        avg_lost_symbols += float(metric.lost_symbols)
    avg_latency /= len(metrics)
    avg_bandwidth /= len(metrics)
    avg_bandwidth_overhead /= len(metrics)
    avg_lost_symbols /= len(metrics)
    print("STILL NEEDS TO BE FIXED - Average recovery latency: {:.3f} ms".format(avg_latency))
    print("Average transmission bandwidth: {:.3f} bytes, {}% increase".format(
        avg_bandwidth, avg_bandwidth_overhead))
    print("Average irrecoverable symbols: {:.3f} symbols, {}%".format(
        avg_lost_symbols, float(avg_lost_symbols)/total_symbols * 100))
