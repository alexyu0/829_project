
class BlockMetrics:
    def __init__(self):
        self.latency = 0 # units - ms
        self.bandwidth = 0 # units - bytes
        self.bandwidth_overhead = 0.0 # units - % increase
        self.lost_symbols = 0 # units - symbols
        # self.delay = 0 # units - symbols

def analyze(metrics, total_symbols, code, latency=0, total_lost=None):
    """
    Analyzes given metrics and averages over it

    Params:
        - metrics: list of BlockMetrics instances from each source block
    """
    avg_latency = 0.0
    avg_bandwidth = 0.0
    avg_bandwidth_overhead = 0.0
    total_latency = 0.0
    total_lost_symbols = 0.0
    for metric in metrics:
        avg_latency += float(metric.latency)
        avg_bandwidth += float(metric.bandwidth)
        avg_bandwidth_overhead += float(metric.bandwidth_overhead)
        total_lost_symbols += float(metric.lost_symbols)
        total_latency += float(metric.latency)
    avg_latency /= len(metrics)
    avg_bandwidth /= len(metrics)
    avg_bandwidth_overhead /= len(metrics)
    if code == "MiDAS":
        total_latency += latency
    with open("TEMP_RES_" + code, "a+") as f:
        f.write("Average block latency: {:.3f} ms\n".format(avg_latency))
        f.write("Total latency: {:.3f} ms\n".format(total_latency))
        # f.write("Average transmission bandwidth: {:.3f} bytes, {}% increase\n".format(
        #     avg_bandwidth, avg_bandwidth_overhead))
        # f.write("Average irrecoverable symbols: {:.3f} symbols, {}%\n".format(
        #     avg_lost_symbols, float(avg_lost_symbols)/total_symbols * 100))
        if total_lost is None:
            f.write("Total irrecoverable symbols: {:.3f} symbols, {}%\n".format(
                total_lost_symbols, float(total_lost_symbols)/total_symbols * 100))
        else:
            f.write("Total irrecoverable symbols: {:.3f} symbols, {}%\n".format(
                total_lost, float(total_lost)/total_symbols * 100))


if __name__ == "__main__":
    # temp to analyze MiDAS results
    min_losses = [] # (loss, i)
    min_latencies = [] # (latency, i)
    with open("TEMP_RES_MiDAS") as f:
        lines = f.readlines()
        for i in range(0, len(lines) - 5, 5):
            total_latency_line = lines[i + 3]
            total_loss_line = lines[i + 4]
            latency = float(total_latency_line.split()[2])
            loss = float(total_loss_line.split()[3])
            min_latencies.append((latency, i))
            min_losses.append((loss, i))

    min_latencies.sort()
    # print(min_latencies)
    min_latencies = min_latencies[0:5]
    min_losses.sort()
    min_losses = min_losses[0:5]
    with open("TEMP_RES_MiDAS") as f:
        lines = f.readlines()
        for tup in min_latencies:
            print(lines[tup[1]:tup[1]+5])
        for tup in min_losses:
            print(lines[tup[1]:tup[1]+5])
