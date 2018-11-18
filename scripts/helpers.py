import csv
import os
import sys
from collections import defaultdict

import constants

def group_files(file_to_csvrows, pair):
    """
    Groups multiple runs of a connection together, pairing client and server if
    specified
    """
    # if pair, is conn # -> run # -> tuple of data for paired client and server
    # if not pair, is endpoint conn # -> run # -> tuple of data for each
    if pair:
        runs = {}
    else:
        runs = defaultdict(list)
    for file_name in file_to_csvrows:
        if file_name.endswith(".zst"):
            f, pcap, zst = file_name.split(".")
            
            # assumes files are named as location_duration_endpoint_run
            l, d, e, r = f.split("_")

            digit_i = -1
            endpoint_no = ""
            while e[digit_i].isdigit():
                endpoint_no = e[digit_i] + endpoint_no
                digit_i -= 1
            endpoint_no = int(endpoint_no)
            endpoint = str(e[0:(digit_i + 1)])

            if pair:
                if endpoint_no not in runs:
                    runs[endpoint_no] = {}
                if r not in runs[endpoint_no]:
                    runs[endpoint_no][r] = {}
                runs[endpoint_no][r][endpoint] = file_to_csvrows[file_name]
            else:
                runs[e].append(file_to_csvrows[file_name])
    
    return runs

def parseCSV(file):
    """
    Raw CSV parser, includes the table headers.
    """
    csvData = []
    with open(file, newline='') as csvfile:
        csvReader = csv.reader(csvfile)
        for row in csvReader:
            csvData.append(row)
    return csvData

def calculate_time_bucket_data(csvData, data_fn):
    """
    Plots data on time scale graph in buckets of BUCKET_SIZE
    Uses data_fn argument to calculate data to be plotted on y axis
    """
    bucketStart = 0
    nextBucket = bucketStart + constants.BUCKET_SIZE

    time_buckets = []
    data_buckets = []
    curr_data_bucket = 0

    # Ignore title row (row 0).
    for i in range(1, len(csvData)):
        row = csvData[i]

        # See if we are on the next bucket.
        if float(row[constants.TIME_COL]) >= nextBucket:
            time_buckets.append(nextBucket)  # Append x-axis point.
            nextBucket += constants.BUCKET_SIZE  # Go to next bucket.
            data_buckets.append(curr_data_bucket)  # Append y-axis point.
            curr_data_bucket = 0  # Reset y-axis sum.

        curr_data_bucket += data_fn(row) # add to curr_data_bucket

    return time_buckets, data_buckets
    
# removes pcap file after creating csv file
def make_csv(pcapfile, analysis_type, save, root_csv_dir):
    csvfile = pcapfile.split(".")[0] + ".csv"
    if save:
        if analysis_type == "latency":
            csvfile = "{}/rtt/{}".format(root_csv_dir, os.path.basename(csvfile))
        else:
            csvfile = "{}/info/{}".format(root_csv_dir, os.path.basename(csvfile))

    # checks if csv already exists first
    if analysis_type == "latency": # latency
        if not os.path.exists(csvfile):
            os.system("tshark -r {} \
                -Y tcp.analysis.ack_rtt \
                -e tcp.analysis.ack_rtt \
                -T fields \
                -E separator=, \
                -E quote=d > {}".format(pcapfile, csvfile))
    else:
        if not os.path.exists(csvfile):
            os.system('tshark -r {} \
                -Y "tcp" \
                -e frame.time_relative \
                -e ip.id \
                -e tcp.srcport \
                -e tcp.dstport \
                -e tcp.seq \
                -e tcp.ack \
                -e tcp.len \
                -T fields \
                -E separator=, \
                > {}'.format(pcapfile, csvfile))

    os.system("rm {}".format(pcapfile))
    return csvfile

# takes a .zst file, doesn't remove the compressed version
def decompress(zstfile):
    pcapfile = zstfile.split(".zst")[0]
    os.system("zstd {} -d -o {}".format(zstfile, pcapfile))
    return pcapfile

# takes a pcap file
def compress(pcapfile):
    zstfile = pcapfile.split(".")[0] + ".zst"
    os.system("zstd --rm -19 -f {} -o {}".format(pcapfile, zstfile))
