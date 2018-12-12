"""
    with open("TEMP_RES_" + code, "a+") as f:
        f.write("Average block latency: {:.3f} ms\n".format(avg_latency))
        # f.write("Total latency: {:.3f} ms\n".format(total_latency))
        f.write("Average transmission bandwidth: {:.3f} bytes, {}% increase\n".format(
            avg_bandwidth, avg_bandwidth_overhead))
        # f.write("Average irrecoverable symbols: {:.3f} symbols, {}%\n".format(
        #     avg_lost_symbols, float(avg_lost_symbols)/total_symbols * 100))
        if total_lost is None:
            f.write("Total irrecoverable symbols: {:.3f} symbols, {}%\n".format(
                total_lost_symbols, float(total_lost_symbols)/total_symbols * 100))
        else:
            f.write("Total irrecoverable symbols: {:.3f} symbols, {}%\n".format(
                total_lost, float(total_lost)/total_symbols * 100))


with open("TEMP_RES_MiDAS", "a+") as f:
        f.write("Parameters are \n  N = {}  B = {}  T = {}\n  R = {}  k = {}  n = {}\n".format(
            midas.N, midas.B, midas.T, midas.R, midas.k, midas.n))


with open("TEMP_RES_RQ", "a+") as f:
        f.write("Parameters are \n  K_min = {}  rate = {}  delay = {}\n".format(
                rq.k_min, rq.rate, rq.recovery_timeout))
"""
