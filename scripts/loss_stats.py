import sys
import os
import matplotlib.pyplot as plt

import constants
import helpers

def get_csv_name(fname):
    return os.path.basename(fname).strip(".csv")

def loss_length_hist(fname, data_lines):
    """
    Graphs histogram of bursts of loss experienced
    """
    loss_bursts = {}

    loss_active = False
    loss_count = 0
    for line in data_lines:
        if "not captured" in line:
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
    
    plt.xticks([int(k) for k in loss_bursts.keys()])
    plt.bar(loss_bursts.keys(), loss_bursts.values(), width=1)
    plt.xlabel("Burst size")
    plt.ylabel("Frequency")
    plt.title("Frequency of loss burst sizes for {}".format(get_csv_name(fname)))
    plt.savefig("{}{}/LossBurstHist_{}.png".format(
        constants.RESULT_DIR,
        csv_subdir_str,
        get_csv_name(fname)))
    plt.clf()
    plt.close()

def is_loss(csv_row):
    if "not captured" in csv_row[constants.INFO_COL]:
        return 1
    else:
        return 0

def loss_timescale(fname, data_lines):
    """
    Graphs loss on timescale graph
    """
    time_buckets, data_buckets = helpers.calculate_time_bucket_data(
        helpers.parseCSV(fname),
        is_loss)

    plt.plot(time_buckets, data_buckets)
    plt.xlabel("Time (in buckets of %0.2f seconds)" % constants.BUCKET_SIZE)
    plt.ylabel("Packets lost")
    plt.title("Packets lost over time for {}".format(get_csv_name(fname)))
    plt.savefig("{}{}/LossTime_{}.png".format(
        constants.RESULT_DIR,
        csv_subdir_str,
        get_csv_name(fname)))
    plt.clf()
    plt.close()

def overall_stats(fname, data_lines):
    """
    Calculate overall statistics of loss and write to file
    """
    lost_packets = 0
    total_packets = 0

    for line in data_lines:
        if "not captured" in line:
            lost_packets += 1
        total_packets += 1

    outfile = "{}{}/LossStats_{}.csv".format(
        constants.RESULT_DIR,
        csv_subdir_str,
        get_csv_name(fname))
    with open(outfile, "w") as out_f:
        out_f.write("Lost packets: {}\n".format(lost_packets))
        out_f.write("Total packets: {}\n".format(total_packets))
        out_f.write("Loss rate: {:f}%\n".format(float(lost_packets)/total_packets * 100))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scrape_loss_stats.py <path to wireshark csv>")
        sys.exit(1)

    csv_dir = os.path.dirname(os.path.abspath(sys.argv[1]))
    if os.path.basename(os.getcwd()) != "829_project":
        print("Run from project repo root")
        sys.exit(1)

    # create directory for results if needed
    global csv_subdir_str
    csv_subdir_str = ""
    if os.path.basename(csv_dir) != "csv":
        csv_subdir = []
        while os.path.basename(csv_dir) != "csv":
            csv_subdir.append(os.path.basename(csv_dir))
            csv_dir = os.path.dirname(csv_dir)
        csv_subdir_str = "/".join(csv_subdir[::-1])
        if not os.path.exists("{}/{}{}".format(os.getcwd(), constants.RESULT_DIR, csv_subdir_str)):
            os.makedirs("{}/{}{}".format(os.getcwd(), constants.RESULT_DIR, csv_subdir_str))

    with open(sys.argv[1]) as f:
        data = f.readlines()
        loss_length_hist(f.name, data)
        loss_timescale(f.name, data)
        overall_stats(f.name, data)
