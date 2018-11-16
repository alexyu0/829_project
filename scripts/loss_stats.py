import sys
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import pprint

import constants
from helpers import make_csv, decompress

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
    for row_all in client_data:
        row = row_all.split(",")
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
    for row_all in server_data:
        row = row_all.split(",")
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
def loss_length_hist(data_lines):
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

def loss_timescale(data_lines):
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
# *********************************** END *********************************** #

# ******************************** GRAPHING ********************************** #
def graph_hist(fname, endpoint, loss_bursts):
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
    plt.title("Frequency of loss burst sizes for {} {}".format(
        get_test_name(fname, endpoint),
        endpoint))

    height_space = int(max(loss_bursts.values()) * 0.02)
    for i in range(0, len(g.patches)):
        rect = g.patches[i]
        ax.text(rect.get_x() + rect.get_width()/2,
            rect.get_height() + height_space,
            loss_bursts[keys[i]],
            ha="center",
            va="bottom").set_fontsize(7)

    plt.savefig("{}{}/LossBurstHist_{}_{}.png".format(
        constants.RESULT_DIR,
        csv_subdir_str,
        get_test_name(fname, endpoint),
        endpoint))
    plt.clf()
    plt.close()

def graph_loss_timescale(fname, endpoint, time_buckets, data_buckets):
    plt.plot(time_buckets, data_buckets)
    plt.xlabel("Time (in buckets of %0.2f seconds)" % constants.BUCKET_SIZE)
    plt.ylabel("Packets lost")
    plt.title("Packets lost over time for {} {}".format(
        get_test_name(fname, endpoint),
        endpoint))
    plt.savefig("{}{}/LossTime_{}_{}.png".format(
        constants.RESULT_DIR,
        csv_subdir_str,
        get_test_name(fname, endpoint),
        endpoint))
    plt.clf()
    plt.close()
# *********************************** END *********************************** #

# ******************************** SCRIPTS ********************************** #
def run_all_zst(grouped_files, name_pre, analysis_dir, csv_dir):
    """
    Runs analysis on all the compressed files from grouped_files
    grouped_files is test -> endpoint -> list of runs
    """
    for test in grouped_files:
        # make directories as needed
        if not os.path.exists("{}/{}".format(analysis_dir, test)):
            os.makedirs("{}/{}".format(analysis_dir, test))
        if not os.path.exists("{}/{}".format(csv_dir, test)):
            os.makedirs("{}/{}".format(csv_dir, test))

        loss_hists = defaultdict(list) # endpoint -> results
        loss_timescales = defaultdict(list) # endpoint -> results
        for endpoint in grouped_files[test]:
            print("Analyzing connection {}...".format(endpoint))
            for (client_zst, server_zst) in grouped_files[test][endpoint]:
                # decompress
                client_pcapfile = decompress(client_zst)
                server_pcapfile = decompress(server_zst)

                # make csvs
                client_csv_file = make_csv(client_pcapfile, "X", csv_dir)
                server_csv_file = make_csv(server_pcapfile, "X", csv_dir)

                client_e = "client" + endpoint
                server_e = "server" + endpoint

                # do things
                client_fname = os.path.abspath(client_csv_file)
                server_fname = os.path.abspath(server_csv_file)
                client_f = open(client_csv_file)
                server_f = open(server_csv_file)
                client_data = client_f.readlines()
                server_data = server_f.readlines()
                client_loss_data, server_loss_data = get_lost_packets(
                    client_data, server_data)
                client_loss_bursts = loss_length_hist(client_loss_data)
                client_loss_timescale = loss_timescale(client_loss_data)
                server_loss_bursts = loss_length_hist(server_loss_data)
                server_loss_timescale = loss_timescale(server_loss_data)
                loss_hists[client_e].append(client_loss_bursts)
                loss_timescales[client_e].append(client_loss_timescale)
                loss_hists[server_e].append(server_loss_bursts)
                loss_timescales[server_e].append(server_loss_timescale)
                client_f.close()
                server_f.close()

                # remove decompressed files
                os.system("rm {} {}".format(client_pcapfile, server_pcapfile))

            # average and then graph
            graph_hist(loss_bursts, endpoint, name_pre, csv_dir):
        
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
        loss_length_hist(client_fname, client_loss_data, "client")
        loss_timescale(client_fname, client_loss_data, "client")
        overall_stats(client_fname, client_loss_data, "client")
        loss_length_hist(server_fname, server_loss_data, "server")
        loss_timescale(server_fname, server_loss_data, "server")
        overall_stats(server_fname, server_loss_data, "server")

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
