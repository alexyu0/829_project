import sys
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import pprint

import constants
import helpers

# **************************** DATA EXTRACTION ****************************** #
def get_lost_packets(client_data, server_data):
    """
    Main functionality
    Looks at difference between packets sent and received at each endpoint
    Stores into dict of results for each direction that has following format
    key: (seq, ack)
    value: [[is_lost : bool, relative time : float, UTC : float] .... ]
    """
    client_out_packets = defaultdict(list) # client -> server
    server_out_packets = defaultdict(list) # server -> client
    client_ports = set([str(constants.CLIENT_1_PORT), str(constants.CLIENT_2_PORT)])
    server_port = str(constants.SERVER_PORT)

    # parse data to populate respective dicts
    client_in_data = [] # data to match against for server_out_packets
    for row in client_data:
        if row[constants.SRC_PORT_COL] in client_ports and row[constants.DST_PORT_COL] == server_port:
            payload_size = int(row[constants.DATA_LEN_COL])
            seq = int(row[constants.SEQ_NUM_COL])
            ack = int(row[constants.ACK_NUM_COL])
            if payload_size == 0:
                client_out_packets[(seq, ack)].append([
                    True,
                    row[constants.REL_TIME_COL],
                    int(row[constants.IP_ID_COL], 16)
                ])
            else:
                end = int(payload_size/constants.MTU)
                if payload_size % constants.MTU != 0:
                    end += 1
                for i in range(0, end):
                    # breaks down larger payloads into MTU sized packets
                    client_out_packets[(seq + i * constants.MTU, ack)].append([
                        True,
                        row[constants.REL_TIME_COL],
                        int(row[constants.IP_ID_COL], 16)
                    ])
        elif row[constants.SRC_PORT_COL] == server_port and row[constants.DST_PORT_COL] in client_ports:
            client_in_data.append(row)
    
    server_in_data = [] # data to match against for client_out_packets
    for row in server_data:
        if row[constants.SRC_PORT_COL] == server_port and row[constants.DST_PORT_COL] in client_ports:
            payload_size = int(row[constants.DATA_LEN_COL])
            seq = int(row[constants.SEQ_NUM_COL])
            ack = int(row[constants.ACK_NUM_COL])
            if payload_size == 0:
                server_out_packets[(seq, ack)].append([
                    True,
                    row[constants.REL_TIME_COL],
                    int(row[constants.IP_ID_COL], 16)
                ])
            else:
                end = int(payload_size/constants.MTU)
                if payload_size % constants.MTU != 0:
                    end += 1
                for i in range(0, end):
                    # breaks down larger payloads into MTU sized packets
                    server_out_packets[(seq + i * constants.MTU, ack)].append([
                        True,
                        row[constants.REL_TIME_COL],
                        int(row[constants.IP_ID_COL], 16) + i
                    ])
        elif row[constants.SRC_PORT_COL] in client_ports and row[constants.DST_PORT_COL] == server_port:
            server_in_data.append(row)

    # go through data of opposite direction to determine which packets were lost
    for row in client_in_data:
        seq = int(row[constants.SEQ_NUM_COL])
        ack = int(row[constants.ACK_NUM_COL])

        # any packet received should definitely have been sent so can assume will never get key err
        for i in range(0, len(server_out_packets[(seq, ack)])):
            if server_out_packets[(seq, ack)][i][2] == int(row[constants.IP_ID_COL], 16):
                server_out_packets[(seq, ack)][i][0] = False
                break

    for row in server_in_data:
        seq = int(row[constants.SEQ_NUM_COL])
        ack = int(row[constants.ACK_NUM_COL])

        # any packet received should definitely have been sent so can assume will never get key err
        for i in range(0, len(client_out_packets[(seq, ack)])):
            if client_out_packets[(seq, ack)][i][2] == int(row[constants.IP_ID_COL], 16):
                client_out_packets[(seq, ack)][i][0] = False
                break

    # convert to list sorted by timestamp
    client = []
    for packets in client_out_packets.values():
        client.extend([(ts, lost) for (lost, ts, utc) in packets])
    client.sort()
    server = []
    for packets in server_out_packets.values():
        server.extend([(ts, lost) for (lost, ts, utc) in packets])
    server.sort()

    return client, server

def get_test_name(fname, endpoint):
    """
    Get file name of CSV data file
    """
    run_no = ""
    last_digit_i = -5
    while fname[last_digit_i].isdigit():
        run_no = fname[last_digit_i] + run_no
        last_digit_i -= 1
    
    testname = os.path.basename(fname[0:fname.index(endpoint)]).rstrip(".csv")
    return "{}_{}".format(testname, run_no)

# *********************************** END *********************************** #

# ************************** STATISTIC ANALYSES ***************************** #
def loss_length_hist(data_lines, graph_individual=False):
    """
    Returns histogram of bursts of loss experienced
    """
    loss_bursts = {}
    loss_active = False
    loss_count = 0
    for (ts, lost) in data_lines:
        if lost:
            loss_count += 1
            if not loss_active:
                loss_active = True
        else:
            if loss_active:
                # reset burst count and write to dict
                if loss_count not in loss_bursts:
                    loss_bursts[loss_count] = 1
                else:
                    loss_bursts[loss_count] += 1
                loss_active = False
                loss_count = 0
    
    return loss_bursts

def loss_timescale(data_lines, graph_individual=False):
    """
    Returns loss on timescale
    """
    bucketStart = 0
    nextBucket = bucketStart + constants.BUCKET_SIZE

    time_buckets = []
    data_buckets = []
    curr_data_bucket = 0

    for (ts, lost) in data_lines:
        # See if we are on the next bucket.
        if float(ts) >= nextBucket:
            time_buckets.append(nextBucket)  # Append x-axis point.
            nextBucket += constants.BUCKET_SIZE  # Go to next bucket.
            data_buckets.append(curr_data_bucket)  # Append y-axis point.
            curr_data_bucket = 0  # Reset y-axis sum.

        if lost:
            curr_data_bucket += 1

    return (time_buckets, data_buckets)

def compute_average_hist(loss_bursts):
    average_loss_bursts = defaultdict(int)
    for hist in loss_bursts:
        for length in hist:
            average_loss_bursts[length] += hist[length]
    
    to_del = []
    for length in average_loss_bursts:
        average_loss_bursts[length] = int(average_loss_bursts[length] / len(loss_bursts))
        if (average_loss_bursts[length] == 0):
            to_del.append(length)
    for length in to_del:
        average_loss_bursts.pop(length, None)
    
    return average_loss_bursts

def compute_average_timescale(loss_timescales):
    time_buckets = []
    average_data_buckets = []
    for buckets in loss_timescales:
        for i in range(0, len(buckets[1])):
            if i >= len(average_data_buckets):
                # first one so can just append
                average_data_buckets.append(buckets[1][i])
            else:
                average_data_buckets[i] += buckets[1][i]

            if i >= len(time_buckets):
                # first one so can just append
                time_buckets.append(buckets[0][i])
    
    for i in range(0, len(average_data_buckets)):
        average_data_buckets[i] = int(average_data_buckets[i] / len(loss_timescales))

    return (time_buckets, average_data_buckets)
# *********************************** END *********************************** #

# ******************************** GRAPHING ********************************** #
def graph_hist(loss_bursts_s, endpoint, name_pre, graph_dir):
    """
    Graphs the histogram generated from loss_length_hist
    """
    for loss_bursts in loss_bursts_s:
        keys = sorted([int(k) for k in loss_bursts.keys()])
        g = plt.bar(range(0, len(keys)), [v for (k,v) in sorted(loss_bursts.items())], width=0.8)
        ax = plt.gca()
        plt.xticks(range(0, len(keys)))
        if len(keys) > 20:
            ax.set_xticklabels(keys, fontsize=7)
        else:
            ax.set_xticklabels(keys)

        height_space = 0
        if len(loss_bursts.values()) != 0:
            height_space = int(max(loss_bursts.values()) * 0.02)
        for i in range(0, len(g.patches)):
            rect = g.patches[i]
            ax.text(rect.get_x() + rect.get_width()/2,
                rect.get_height() + height_space,
                loss_bursts[keys[i]],
                ha="center",
                va="bottom").set_fontsize(7)

    plt.xlabel("Burst size")
    plt.ylabel("Frequency")
    plt.title("Frequency of loss burst sizes for {} {}".format(name_pre, endpoint))
    plt.savefig("{}/LossBurstHist_{}_{}.png".format(
        graph_dir, name_pre, endpoint))
    plt.clf()
    plt.close()

def graph_loss_timescale(timescales, endpoint, name_pre, graph_dir):
    for timescale in timescales:
        time_buckets, data_buckets = timescale
        plt.plot(time_buckets, data_buckets)
    plt.ylim(top=50000)
    plt.xlabel("Time (in buckets of %0.2f seconds)" % constants.BUCKET_SIZE)
    plt.ylabel("Packets lost")
    plt.title("Packets lost over time for {} {}".format(name_pre, endpoint))
    plt.savefig("{}/LossTime_{}_{}.png".format(
        graph_dir, name_pre, endpoint))
    plt.clf()
    plt.close()

# *********************************** END *********************************** #

# ******************************** SCRIPTS ********************************** #
def analyze_loss(file_to_csvrows, graph_dir, test_str, aggregate=False):
    """
    Runs analysis on data for some files, assumed to be from the same test
    """
    print(file_to_csvrows.keys())
    l, d, e, r = list(file_to_csvrows.keys())[0].split("_")
    name_pre = "{}_{}_{}_".format(test_str, l, d)

    # group by connection number and run number
    print("Analyzing loss...")
    runs = helpers.group_files(file_to_csvrows, True)

    # do the thing
    for conn_no in runs:
        print("\n")
        print("analyzing connection {}...".format(conn_no))
        loss_hists = defaultdict(list)
        loss_timescales = defaultdict(list)
        for run_no in runs[conn_no]:
            print("analyzing connection {} run {}...".format(conn_no, run_no))
            client_data = runs[conn_no][run_no]["client"]
            server_data = runs[conn_no][run_no]["server"]

            # run statistics analysis
            print("figuring out lost packets...")
            client_loss_data, server_loss_data = get_lost_packets(
                client_data, server_data)
            print("processing client...")
            client_loss_bursts = loss_length_hist(client_loss_data)
            client_loss_timescale = loss_timescale(client_loss_data)
            print("processing server...")
            server_loss_bursts = loss_length_hist(server_loss_data)
            server_loss_timescale = loss_timescale(server_loss_data)

            client_e = "client" + str(conn_no)
            server_e = "server" + str(conn_no)
            loss_hists[client_e].append(client_loss_bursts)
            loss_timescales[client_e].append(client_loss_timescale)
            loss_hists[server_e].append(server_loss_bursts)
            loss_timescales[server_e].append(server_loss_timescale)
            print("...connection {} run {} done\n".format(conn_no, run_no))
        for endpoint in loss_hists:
            # SERVER means packets lost from server to client
            # CLIENT means packets lost from client to server
            print("calculating average for {}...".format(endpoint))
            avg_loss_bursts = compute_average_hist(loss_hists[endpoint])
            avg_loss_timescale = compute_average_timescale(loss_timescales[endpoint])
            graph_hist([avg_loss_bursts], endpoint, name_pre, graph_dir)
            graph_loss_timescale([avg_loss_timescale], endpoint, name_pre, graph_dir)
            print("...done")
    
    if aggregate:
        return (loss_hists, loss_timescales)

def aggregate_loss(file_to_csvrows, graph_dir, test_str):
    # get aggregate data
    campus = {}
    home = {}
    starbucks = {}
    for (key, values) in file_to_csvrows.items():
        print(key)
        if "campus" in key:
            campus[key] = values
        elif "home" in key:
            home[key] = values
        elif "starbucks" in key:
            starbucks[key] = values

    campus_hist, campus_timescale = analyze_loss(campus, graph_dir, test_str, True)
    home_hist, home_timescale = analyze_loss(home, graph_dir, test_str, True)
    starbucks_hist, starbucks_timescale = analyze_loss(starbucks, graph_dir, test_str, True)

    for endpoint in campus_hist:
        c_avg_loss_bursts = compute_average_hist(campus_hist[endpoint])
        h_avg_loss_bursts = compute_average_hist(home_hist[endpoint])
        s_avg_loss_bursts = compute_average_hist(starbucks_hist[endpoint])

        c_avg_loss_timescale = compute_average_timescale(campus_timescale[endpoint])
        h_avg_loss_timescale = compute_average_timescale(home_timescale[endpoint])
        s_avg_loss_timescale = compute_average_timescale(starbucks_timescale[endpoint])

        graph_hist([c_avg_loss_bursts, h_avg_loss_bursts, s_avg_loss_bursts], 
            endpoint, "asdfasdf", graph_dir)
        graph_loss_timescale([c_avg_loss_timescale, h_avg_loss_timescale, s_avg_loss_timescale], 
            endpoint, "adfasdf", graph_dir)

# *********************************** END *********************************** #

# ********************************** MAIN *********************************** #
if __name__ == "__main__":
    if len(sys.argv) < 2 or (len(sys.argv) < 3 and sys.argv[1] != "--all"):
        print("Usage: python scrape_loss_stats.py --all \n OR \n \
            python scrape_loss_stats.py <client dump> <server dump>")
        sys.exit(1)

    pp = pprint.PrettyPrinter(indent=2)

    # loop through all CSVs possible if running all
    csvs_dict = {}
    if sys.argv[1] == "--all":
        for dir_contents in os.walk(os.getcwd() + "/new_csv"):
            runs = defaultdict(list)
            for f in dir_contents[2]:
                if f.endswith(".csv"):
                    # figure out which run this file was from
                    last_digit_i = -5
                    run_no = ""
                    while f[last_digit_i].isdigit():
                        run_no = f[last_digit_i] + run_no
                        last_digit_i -= 1
                    run_no = int(run_no)
                    runs[run_no].append("{}/{}".format(dir_contents[0], f))

            csvs_dict[dir_contents[0]] = runs.values()
        
        # flatten
        csvs = []
        for csv_list in csvs_dict.values():
            csvs.extend(csv_list)
    else:
        csvs = [[sys.argv[1], sys.argv[2]]]
    
    analyze(csvs)

# *********************************** END *********************************** #

# ******************************* DEPRECATED ********************************* #
def analyze(csvs):
    for (client_csv_file, server_csv_file) in csvs:
        print("Analyzing {} and {}...".format(
            os.path.basename(client_csv_file),
            os.path.basename(server_csv_file)))
        csv_dir = os.path.dirname(os.path.abspath(client_csv_file))
        if os.path.basename(os.getcwd()) != "829_project":
            print("Run from project repo root")
            sys.exit(1)

        # create directory for results if needed
        global csv_subdir_str
        csv_subdir_str = ""
        if os.path.basename(csv_dir) != "new_csv":
            csv_subdir = []
            while os.path.basename(csv_dir) != "new_csv":
                csv_subdir.append(os.path.basename(csv_dir))
                csv_dir = os.path.dirname(csv_dir)
            csv_subdir_str = "/".join(csv_subdir[::-1])
            if not os.path.exists("{}/{}{}".format(os.getcwd(), constants.RESULT_DIR, csv_subdir_str)):
                os.makedirs("{}/{}{}".format(os.getcwd(), constants.RESULT_DIR, csv_subdir_str))

        client_fname = os.path.abspath(client_csv_file)
        server_fname = os.path.abspath(server_csv_file)
        client_f = open(client_csv_file)
        server_f = open(server_csv_file)
        client_data = client_f.readlines()
        server_data = server_f.readlines()
        
        client_loss_data, server_loss_data = get_lost_packets(client_data, server_data)
        loss_length_hist(client_loss_data)
        loss_timescale(client_loss_data)
        loss_length_hist(server_loss_data)
        loss_timescale(server_loss_data)

        client_f.close()
        server_f.close()
        
        print("...done")

def overall_stats(fname, data_lines, endpoint):
    """
    Calculate overall statistics of loss and write to file
    """
    lost_packets = 0
    total_packets = 0

    for (ts, lost) in data_lines:
        if lost:
            lost_packets += 1
        total_packets += 1

    outfile = "{}{}/LossStats_{}_{}.csv".format(
        constants.RESULT_DIR,
        csv_subdir_str,
        get_test_name(fname, endpoint),
        endpoint)
    with open(outfile, "w") as out_f:
        out_f.write("Lost packets: {}\n".format(lost_packets))
        out_f.write("Total packets: {}\n".format(total_packets))
        out_f.write("Loss rate: {:f}%\n".format(float(lost_packets)/total_packets * 100))
# *********************************** END *********************************** #
