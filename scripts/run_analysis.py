import os
import time
import io
import sys
import argparse
import subprocess
import time
import random
import atexit
import bandwidth as bw
import csv

from constants import PORT_START

# removes csv file after extracting csv data
def parseCSV(file):
    csvData = []
    with open(file, newline='') as csvfile:
        csvReader = csv.reader(csvfile)
        for row in csvReader:
            csvData.append(row)
    csvfile.close()
    # remove csv file after use.
    os.system("rm {}".format(file))
    return csvData

# removes pcap file after creating csv file
def make_csv(pcapfile, analysis_type):
    csvfile = pcapfile.split(".")[0] + ".csv"

    if analysis_type == "Y": # latency
        os.system("tshark -r {} -Y tcp.analysis.ack_rtt -e tcp.analysis.ack_rtt -T fields -E separator=, -E quote=d > {}".format(pcapfile, csvfile))
    else:
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

def analysis(args):
    """
    main analysis function
    """
    print("Getting necessary files for ", end="")
    analysis_type = ""
    if args.bandwidth:
        analysis_type = "bandwidth"
        print("bandwidth ",end="")
    elif args.loss:
        analysis_type = "loss"
        print("loss ",end="")
    elif args.latency:
        analysis_type = "latency"
        print("latency ",end="")
    else:
        print("Invalid analysis specified")
        sys.exit(1)
    print("analysis...")
    # make file name
    duration = ""
    short_duration = ""
    if args.time is not None:
        duration = "-t {}".format(args.time)
        name_duration = "{}s".format(str(args.time))
        short_duration = "-t {}".format(int(int(args.time) * 0.01))
        name_short_duration = "{}s".format(str(int(int(args.time) * 0.01)))
    elif args.size is not None:
        duration = "--bytes {}".format(int(args.size) * 1000000)
        name_duration = "{}s".format(str(int(args.size) * 1000000))
        short_duration = "--bytes {}".format(int(int(args.size) * 10000))
        name_short_duration = "{}MB".format(str(int(int(args.size) * 10000)))
    file_name = "{}_{}".format(args.location, name_duration)
    file_name_short = ""
    if args.longshort:
        file_name_short = "{}_{}".format(args.location, name_short_duration)

    # set up directories
    args.path = args.path.rstrip("/")
    root_analysis_dir = os.path.abspath(args.path)
    root_dir = "/".join(root_analysis_dir.split("/")[:len(root_analysis_dir.split("/"))-1]) + "/"
    root_test_dir = root_dir + args.testdir
    root_graph_dir = root_dir + args.graphdir
    if args.concurrentlong:
        analysis_dir = "{}/{}/{}".format(root_analysis_dir, "concurrent_long", file_name)
        test_dir = "{}/{}/{}".format(root_test_dir, "concurrent_long", file_name)
        graph_dir = "{}/{}/{}/{}".format(root_graph_dir, analysis_type, "concurrent_long", file_name)
    elif args.longshort:
        analysis_dir = "{}/{}/{}".format(root_analysis_dir, "long_and_short", file_name)
        test_dir = "{}/{}/{}".format(root_test_dir, "long_and_short", file_name)
        graph_dir = "{}/{}/{}/{}".format(root_graph_dir, analysis_type, "long_and_short", file_name)
    elif args.normal:
        analysis_dir = "{}/{}/{}".format(root_analysis_dir, "normal", file_name)
        test_dir = "{}/{}/{}".format(root_test_dir, "normal", file_name)
        graph_dir = "{}/{}/{}/{}".format(root_graph_dir, analysis_type, "normal", file_name)
    else:
        print("NO VALID FILE FORMAT")
        sys.exit(1)
    if not os.path.exists(test_dir):
        print("Test dir {} doesn't exist!".format(test_dir))
        sys.exit(1)
    if not os.path.exists(graph_dir):
        os.makedirs(graph_dir)
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)
    print("Analysis_dir {} set up to analyze test_dir {}.".format(analysis_dir, test_dir))

    # decompress files one at a time and extract information from them
    csv_data_for_files = {}
    for file_name in os.listdir(test_dir):
        if file_name.endswith(".zst"):
            file_with_path = test_dir + "/" + file_name
            # decompress one at a time size these files are big
            pcapfile = decompress(file_with_path)
            if not os.path.exists(pcapfile):
                print("Failed to create pcap file for {}".format(file_name))
                sys.exit(1)
            # make different csv depending on the test
            csvfile = make_csv(pcapfile, analysis_type) # removes pcapfile
            if not os.path.exists(csvfile):
                print("Failed to create csv file for {}".format(file_name))
                sys.exit(1)
            # extract data for each file
            csv_data_for_files[file_name] = parseCSV(csvfile) # removes csvfile
            # compress to save storage 
            #compress(pcapfile)


    # run analysis on files
    if args.bandwidth:
        print("Analyzing bandwidth...")
        bw.getBandwidth(csv_data_for_files, graph_dir)
    elif args.loss:
        print("Analyzing packet loss...")

    elif args.latency:
        print("Analyzing per packet latency...")
        #getLatency(csv_data_for_files)
        
    print("Analysis complete.")
    return

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
parser = argparse.ArgumentParser(prog="PROG",
    description="829 Project Network Trace Analysis",
    usage="python run_analysis.py",
    formatter_class=formatter)

required_args = parser.add_argument_group("required")
required_args.add_argument("-l", "--location",
    help="location trace is taken in, used for file name\n")
# required_args.add_argument("-I", "--ips",
#     help="file containing list of server IPs, \n*** DON'T INCLUDE ENDPOINT OR TRIAL # ***\n")
required_args.add_argument("-P", "--path", 
    help="path to root directory of analysis results\n")
required_args.add_argument("-T", "--testdir",
    help="directory name of the test directory (not full path)")
required_args.add_argument("-G", "--graphdir",
    help="directory name for where the graphs should be saved (not full path)")
# required_args.add_argument("-n", "--numtests", 
#     help="number of times to run analysis\n")
# required_args.add_argument("-i", "--keyfile",
#     help="path to public key file\n")

test_args = parser.add_mutually_exclusive_group(required=True)
test_args.add_argument("-t", "--time",
    help="amount of time to run test for, in seconds\n")
test_args.add_argument("-s", "--size",
    help="size of data to be transmitted, in MB\n")

test_style_args = parser.add_mutually_exclusive_group(required=True)
test_style_args.add_argument("-C", "--concurrentlong",
    action="store_true",
    help="true if running concurrent long downloads analysis, false otherwise")
test_style_args.add_argument("-L", "--longshort",
    action="store_true",
    help="true if running long download with short downloads analysis, false otherwise")
test_style_args.add_argument("-N", "--normal",
    action="store_true",
    help="true if running normal download analysis, false otherwise")

test_args = parser.add_mutually_exclusive_group(required=True)
test_args.add_argument("-B", "--bandwidth",
    action="store_true",
    help="analyze bandwidth\n")
test_args.add_argument("-X", "--loss",
    action="store_true",
    help="analyze loss\n")
test_args.add_argument("-Y", "--latency",
    action="store_true",
    help="analyze per packet latency\n")

parser.set_defaults(func=analysis)

if __name__ == '__main__':
    random.seed()
    args = parser.parse_args()
    args.func(args)
