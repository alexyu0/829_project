import csv
from collections import defaultdict
import numpy
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from math import ceil

import model_constants

class BlockMetrics:
    def __init__(self):
        self.latency = 0 # units - ms
        self.bandwidth = 0 # units - bytes
        self.bandwidth_overhead = 0.0 # units - % increase
        self.lost_symbols = 0 # units - symbols
        # self.delay = 0 # units - symbols

def analyze(metrics, total_symbols, code, code_obj, csv_path, latency=0, total_lost=None):
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
    
    # write to csv
    if code == "MiDAS":
        with open(csv_path, mode="a+") as f:
            f_writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            f_writer.writerow([
                code_obj.N, 
                code_obj.B, 
                code_obj.T,
                code_obj.box.latency, 
                code_obj.R,
                code_obj.k,
                code_obj.n,
                avg_latency,
                avg_bandwidth_overhead,
                float(total_lost_symbols if total_lost is None else total_lost)/total_symbols * 100
            ])
    else:
        with open(csv_path, mode="a+") as f:
            f_writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            f_writer.writerow([
                code_obj.k_min, 
                code_obj.rate, 
                code_obj.recovery_timeout,
                code_obj.box.latency,
                avg_latency,
                avg_bandwidth_overhead,
                float(total_lost_symbols if total_lost is None else total_lost)/total_symbols * 100
            ])

def rq_argset_results(metric):
    for latency in model_constants.LATENCY_VALS:
        # find relevant CSV files, build dictionary of argset to result total
        result_dict = defaultdict(list)
        for argset_key in model_constants.ge_ref_keys:
            csv_file_path = "{}/RQ_results_{}_{}.csv".format(
                model_constants.RAW_CSV_DIR, latency, argset_key)
            with open(csv_file_path, "r") as f:
                f_reader = csv.reader(f, delimiter=',')
                cnt = 0
                for row in f_reader:
                    if cnt == 0:
                        cnt += 1
                        continue
                    
                    if metric == "latency":
                        col = 4
                    elif metric == "bw":
                        col = 5
                    elif metric == "loss":
                        col = 6
                    result_dict[" ".join(row[0:2])].append((row, float(row[col])))
        
        csv_path = "{}/RQ_best_{}_{}.csv".format(model_constants.BEST_CSV_DIR, latency, metric)
        with open(csv_path, "w") as f_res:
            f_res_writer = csv.writer(f_res, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            min_metric = 1000000000
            min_arg = []
            for v in result_dict.values():
                curr_val = sum([value for (row, value) in v])
                if curr_val < min_metric:
                    min_metric = curr_val
                    min_arg = v
            
            f_res_writer.writerow(["GE ref", "K_min", "Rate", "Delay", "Packet latency (ms)",
                    "Latency (ms)", "Bandwidth increase (%)", "Loss rate (%)"])
            for i in range(0, len(min_arg)):
                f_res_writer.writerow([i+1] + min_arg[i][0])

def midas_argset_results(metric):
    for latency in model_constants.LATENCY_VALS:
        # find relevant CSV files, build dictionary of argset to result total
        result_dict = defaultdict(list)
        for argset_key in model_constants.ge_ref_keys:
            csv_file_path = "{}/MiDAS_results_{}_{}.csv".format(
                model_constants.RAW_CSV_DIR, latency, argset_key)
            with open(csv_file_path, "r") as f:
                f_reader = csv.reader(f, delimiter=',')
                cnt = 0
                for row in f_reader:
                    if cnt == 0:
                        cnt += 1
                        continue
                    
                    if metric == "latency":
                        col = 7
                    elif metric == "bw":
                        col = 8
                    elif metric == "loss":
                        col = 9
                    result_dict[" ".join(row[0:2])].append((row, float(row[col])))

        csv_path = "{}/MiDAS_best_{}_{}.csv".format(model_constants.BEST_CSV_DIR, latency, metric)
        with open(csv_path, "w") as f_res:
            f_res_writer = csv.writer(f_res, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            min_metric = 1000000000
            min_arg = []
            for v in result_dict.values():
                curr_val = sum([value for (row, value) in v])
                if curr_val < min_metric:
                    min_metric = curr_val
                    min_arg = v
            
            f_res_writer.writerow(["GE ref", "N", "B", "T", "Packet latency (ms)", "R", "k", "n",
                    "Frame latency (ms)", "Bandwidth increase (%)", "Loss rate (%)"])
            for i in range(0, len(min_arg)):
                f_res_writer.writerow([i+1] + min_arg[i][0])

def mean_max_min(d):
    aggregates = []
    for i in model_constants.ge_ref_keys:
        latencies = [v[1] for v in d[i]]
        bws = [v[2] for v in d[i]]
        losses = [v[3] for v in d[i]]
        # print(latencies)
        # print(numpy.mean(latencies))
        aggregates.append([numpy.mean(latencies),
            numpy.amax(latencies),
            numpy.amin(latencies),
            numpy.mean(bws),
            numpy.amax(bws),
            numpy.amin(bws),
            numpy.mean(losses),
            numpy.amax(losses),
            numpy.amin(losses)])
    
    return aggregates

def normalized_val(aggregates, val, i):
    # print(val, aggregates)
    # print(val[i][1], aggregates[0], aggregates[1], aggregates[2])
    normalized_latency = (val[i][1] - aggregates[2])/(aggregates[1] - aggregates[2])
    normalized_bw = (val[i][2] - aggregates[5])/(aggregates[4] - aggregates[5])
    normalized_loss = (val[i][3] - aggregates[8])/(aggregates[7] - aggregates[8])
    return (normalized_latency + normalized_bw + normalized_loss)/3

def normalized_results():
    for latency in model_constants.LATENCY_VALS:
        # find relevant CSV files, build dictionary of argset to result total
        result_dict = defaultdict(list)
        rq_result_dict = defaultdict(list)
        midas_result_dict = defaultdict(list)
        for code in ["RQ", "MiDAS"]:
            for argset_key in model_constants.ge_ref_keys:
                csv_file_path = "{}/{}_results_{}_{}.csv".format(
                    model_constants.RAW_CSV_DIR, code, latency, argset_key)
                with open(csv_file_path, "r") as f:
                    f_reader = csv.reader(f, delimiter=',')
                    cnt = 0
                    for row in f_reader:
                        if cnt == 0:
                            cnt += 1
                            continue

                        if code == "RQ":
                            result_dict[argset_key].append((row, 
                                float(row[4]),
                                float(row[5]),
                                float(row[6])))
                            rq_result_dict[" ".join(row[0:2])].append((row, 
                                float(row[4]),
                                float(row[5]),
                                float(row[6])))
                        else:
                            result_dict[argset_key].append((row, 
                                float(row[7]),
                                float(row[8]),
                                float(row[9])))
                            midas_result_dict[" ".join(row[0:2])].append((row, 
                                float(row[7]),
                                float(row[8]),
                                float(row[9])))

        # normalize
        aggregates = mean_max_min(result_dict)
        print(aggregates)

        for code in ["RQ", "MiDAS"]:
            # mean_latency, max_latency, min_latency = aggregates[0], aggregates[1], aggregates[2]
            # mean_bw, max_bw, min_bw = aggregates[3], aggregates[4], aggregates[5]
            # mean_loss, max_loss, min_loss = aggregates[6], aggregates[7], aggregates[8]
            csv_path = "{}/{}_best_{}_agg.csv".format(model_constants.BEST_CSV_DIR, code, latency)
            with open(csv_path, "w") as f_res:
                f_res_writer = csv.writer(f_res, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                min_metric = 1000000000
                min_arg = []
                if code == "RQ":
                    r_dict = rq_result_dict
                else:
                    r_dict = midas_result_dict
                for v in r_dict.values():
                    vals = []
                    for i in model_constants.ge_ref_keys:
                        vals.append(normalized_val(aggregates[int(i)-1], v, int(i)-1))
                    curr_val = sum(vals)
                    if curr_val < min_metric:
                        min_metric = curr_val
                        min_arg = v
                
                # print(min_arg)
                if code == "MiDAS":
                    f_res_writer.writerow(["GE ref", "N", "B", "T", "Packet latency (ms)", "R", "k", "n",
                            "Frame latency (ms)", "Bandwidth increase (%)", "Loss rate (%)", "Aggregate"])
                else:
                    f_res_writer.writerow(["GE ref", "K_min", "Rate", "Delay", "Packet latency (ms)",
                        "Latency (ms)", "Bandwidth increase (%)", "Loss rate (%)", "Aggregate"])
                for i in range(0, len(min_arg)):
                    f_res_writer.writerow(
                        ([i+1] + min_arg[i][0] + [normalized_val(aggregates[i], min_arg, i)]))

def graph():
    for latency in model_constants.LATENCY_VALS:
        for metric in model_constants.METRICS:
            fig, ax = plt.subplots()
            ax.yaxis.set_major_formatter(FormatStrFormatter("%.2f"))

            RQ_path = "{}/RQ_best_{}_{}.csv".format(model_constants.BEST_CSV_DIR, latency, metric)
            midas_path = "{}/MiDAS_best_{}_{}.csv".format(model_constants.BEST_CSV_DIR, latency, metric)

            # x-axis is BLER, y-axis is whatever metric
            x_vals = model_constants.ge_bler_ref.values()
            rq_y_vals = []
            midas_y_vals = []

            K_min = None
            N = None
            B = None
            with open(RQ_path, "r") as f:
                f_reader = csv.reader(f, delimiter=',')
                cnt = 0
                for row in f_reader:
                    if cnt == 0:
                        cnt += 1
                        continue
                    rq_y_vals.append(float(row[model_constants.metric_col_map[("RQ", metric)]]))
                K_min = row[1]
            with open(midas_path, "r") as f:
                f_reader = csv.reader(f, delimiter=',')
                cnt = 0
                for row in f_reader:
                    if cnt == 0:
                        cnt += 1
                        continue
                    midas_y_vals.append(float(row[model_constants.metric_col_map[("MiDAS", metric)]]))
                N = row[1]
                B = row[2]
            
            y_max = max(rq_y_vals + midas_y_vals) * 1.05
            plt.ylim(bottom=0, top=(ceil(y_max) if y_max > 1 else y_max))
            plt.xlim(left=0, right=22)
            plt.plot(x_vals, rq_y_vals, 
                linestyle='--', marker='o', color='b', 
                label="RaptorQ (K_min = {})".format(K_min))
            plt.plot(x_vals, midas_y_vals, 
                linestyle='--', marker='o', color='r', 
                label="MiDAS (N = {}, B = {})".format(N, B))
            ax.legend()
            # for a,b in zip(x_vals, rq_y_vals): 
            #     plt.text(a, b, str(b))
            # for a,b in zip(x_vals, midas_y_vals): 
            #     plt.text(a, b, str(b))
            # plt.ylim(top=50000)
            plt.xlabel("Overall error rate")
            plt.ylabel(model_constants.METRIC_LABELS[metric])
            # plt.title("{} vs Error Rate for Packet Latency of {}ms".format(
            #     model_constants.METRIC_TITLES[metric], latency))
            plt.savefig("{}/{}_{}.png".format(model_constants.GRAPH_DIR, metric, latency))
            plt.clf()
            plt.close()
            print("graphed {} {}".format(metric, latency))

if __name__ == "__main__":
    pass
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
