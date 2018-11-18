import sys
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import pprint

import constants

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
    client_port = str(constants.CLIENT_1_PORT)
    server_port = str(constants.SERVER_PORT)

    # parse data to populate respective dicts
    client_in_data = [] # data to match against for server_out_packets
    for row in client_data:
        if row[constants.SRC_PORT_COL] == client_port and row[constants.DST_PORT_COL] == server_port:
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
        elif row[constants.SRC_PORT_COL] == server_port and row[constants.DST_PORT_COL] == client_port:
            client_in_data.append(row)
    
    server_in_data = [] # data to match against for client_out_packets
    for row in server_data:
        if row[constants.SRC_PORT_COL] == server_port and row[constants.DST_PORT_COL] == client_port:
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
        elif row[constants.SRC_PORT_COL] == client_port and row[constants.DST_PORT_COL] == server_port:
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

    print(len(server), len(client_in_data))
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
    
    for length in average_loss_bursts:
        average_loss_bursts[length] = int(average_loss_bursts[length] / len(loss_bursts))
    
    return average_loss_bursts

def compute_average_timescale(loss_timescales):
    average_data_buckets = [0 for i in range(0, len(loss_timescales[0][1]))]
    for buckets in loss_timescales:
        for i in range(0, len(buckets[1])):
            average_data_buckets[i] += buckets[1][i]
    
    for i in range(0, len(average_data_buckets)):
        average_data_buckets[i] = int(average_data_buckets[i] / len(loss_timescales))

    return average_data_buckets

# *********************************** END *********************************** #

# ******************************** GRAPHING ********************************** #
def graph_hist(loss_bursts, endpoint, name_pre, graph_dir):
    """
    Graphs the histogram generated from loss_length_hist
    """
    keys = sorted([int(k) for k in loss_bursts.keys()])
    g = plt.bar(range(0, len(keys)), [v for (k,v) in sorted(loss_bursts.items())], width=0.8)
    ax = plt.gca()
    plt.xticks(range(0, len(keys)))
    if len(keys) > 20:
        ax.set_xticklabels(keys, fontsize=7)
    else:
        ax.set_xticklabels(keys)
    plt.xlabel("Burst size")
    plt.ylabel("Frequency")
    plt.title("Frequency of loss burst sizes for {} {}".format(name_pre, endpoint))

    height_space = int(max(loss_bursts.values()) * 0.02)
    for i in range(0, len(g.patches)):
        rect = g.patches[i]
        ax.text(rect.get_x() + rect.get_width()/2,
            rect.get_height() + height_space,
            loss_bursts[keys[i]],
            ha="center",
            va="bottom").set_fontsize(7)

    plt.savefig("{}/LossBurstHist_{}_{}.png".format(
        graph_dir, name_pre, endpoint))
    plt.clf()
    plt.close()

def graph_loss_timescale(timescale, endpoint, name_pre, graph_dir):
    time_buckets, data_buckets = timescale
    plt.plot(time_buckets, data_buckets)
    plt.xlabel("Time (in buckets of %0.2f seconds)" % constants.BUCKET_SIZE)
    plt.ylabel("Packets lost")
    plt.title("Packets lost over time for {} {}".format(name_pre, endpoint))
    plt.savefig("{}/LossTime_{}_{}.png".format(
        graph_dir, name_pre, endpoint))
    plt.clf()
    plt.close()

# *********************************** END *********************************** #

# ******************************** SCRIPTS ********************************** #
def analyze_loss(file_to_csvrows, graph_dir, test_str):
    """
    Runs analysis on data for some files, assumed to be from the same test
    """
    name_pre = None 
    runs = {} # conn # -> run # -> tuple of data for paired client and server

    # group by connection number and run number
    print("Analyzing loss...")
    for file_name in file_to_csvrows:
        if file_name.endswith(".zst"):
            f, pcap, zst = file_name.split(".")
            
            # assumes files are named as location_duration_endpoint_run
            l, d, e, r = f.split("_")
            if name_pre is None:
                name_pre = "{}_{}_{}_".format(test_str, l, d)

            digit_i = -1
            endpoint_no = ""
            while e[digit_i].isdigit():
                endpoint_no = e[digit_i] + endpoint_no
                digit_i -= 1
            endpoint_no = int(endpoint_no)
            endpoint = str(e[0:(digit_i + 1)])

            if endpoint_no not in runs:
                runs[endpoint_no] = {}
            if r not in runs[endpoint_no]:
                runs[endpoint_no][r] = {}
            runs[endpoint_no][r][endpoint] = file_to_csvrows[file_name]

    # do the thing
    for conn_no in runs:
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
            print("calculating average for {}...", endpoint)
            avg_loss_bursts = compute_average_hist(loss_hists[endpoint])
            avg_loss_timescale = compute_average_timescale(loss_timescales[endpoint])
            graph_hist(avg_loss_bursts, endpoint, name_pre, graph_dir)
            graph_loss_timescale(avg_loss_timescale, endpoint, name_pre, graph_dir)
            print("...done")

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
