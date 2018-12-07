import os
import time
import io
import sys
import argparse
import subprocess
import time
import atexit
import bandwidth as bw
import csv
from collections import defaultdict

from constants import PORT_START
from loss_stats import analyze_loss, aggregate_loss
from helpers import make_csv, decompress, compress
from latency import getLatency

# removes csv file after extracting csv data
def parseCSV(file, save):
    csvData = []
    with open(file, newline='') as csvfile:
        csvReader = csv.reader(csvfile)
        for row in csvReader:
            csvData.append(row)
    csvfile.close()

    # remove csv file after use if not save
    if not save:
        os.system("rm {}".format(file))
    return csvData

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
    if args.aggregate:
        file_name = "aggregate"

    # set up directories
    args.path = args.path.rstrip("/")
    root_analysis_dir = os.path.abspath(args.path)
    root_dir = os.path.dirname(root_analysis_dir) + "/"
    root_test_dir = root_dir + args.testdir
    root_graph_dir = root_dir + args.graphdir
    if args.savecsv:
        root_csv_dir = root_dir + args.csvdir
    else:
        root_csv_dir = ""
    test_str = ""
    if args.concurrentlong:
        analysis_dir = "{}/{}/{}".format(root_analysis_dir, "concurrent_long", file_name)
        test_dir = "{}/{}/{}".format(root_test_dir, "concurrent_long", file_name)
        graph_dir = "{}/{}/{}/{}".format(root_graph_dir, analysis_type, "concurrent_long", file_name)
        test_str = "concurrent_long"
    elif args.longshort:
        analysis_dir = "{}/{}/{}".format(root_analysis_dir, "long_and_short", file_name)
        test_dir = "{}/{}/{}".format(root_test_dir, "long_and_short", file_name)
        graph_dir = "{}/{}/{}/{}".format(root_graph_dir, analysis_type, "long_and_short", file_name)
        test_str = "long_and_short"
    elif args.normal:
        analysis_dir = "{}/{}/{}".format(root_analysis_dir, "normal", file_name)
        test_dir = "{}/{}/{}".format(root_test_dir, "normal", file_name)
        graph_dir = "{}/{}/{}/{}".format(root_graph_dir, analysis_type, "normal", file_name)
        test_str = "normal"
    l_info = file_name

    if not os.path.exists(test_dir) and not args.aggregate:
        print("Test dir {} doesn't exist!".format(test_dir))
        sys.exit(1)
    print(graph_dir)
    if not os.path.exists(graph_dir):
        os.makedirs(graph_dir)
    print(analysis_dir)
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)
    print("Analysis_dir {} set up to analyze test_dir {}.".format(analysis_dir, test_dir))

    # decompress files one at a time and extract information from them
    csv_data_for_files = {}
    if not args.aggregate:
        for file_name in os.listdir(test_dir):
            if file_name.endswith(".zst"):
                # check if saved first
                csvfile = os.path.abspath(file_name).split(".pcap.zst")[0] + ".csv"
                if args.savecsv:
                    if analysis_type == "latency":
                        csvfile = "{}/rtt/{}/{}/{}.csv".format(
                            root_csv_dir, test_str, l_info, file_name.split(".pcap.zst")[0])
                    else:
                        csvfile = "{}/info/{}/{}/{}.csv".format(
                            root_csv_dir, test_str, l_info, file_name.split(".pcap.zst")[0])
                
                if not os.path.exists(csvfile):
                    file_with_path = test_dir + "/" + file_name
                    # decompress one at a time size these files are big
                    print("Decompressing {}...".format(os.path.basename(file_name)))
                    pcapfile = decompress(file_with_path)
                    if not os.path.exists(pcapfile):
                        print("Failed to create pcap file for {}".format(file_name))
                        sys.exit(1)

                    # make different csv depending on the test, remove pcap too
                    print("Parsing {} to csv...".format(os.path.basename(file_name)))
                    new_csvfile = make_csv(pcapfile, csvfile, analysis_type)
                    if not os.path.exists(new_csvfile):
                        print("Failed to create csv file for {}".format(file_name))
                        sys.exit(1)

                # extract data for each file
                print("Extracting from {}...".format(os.path.basename(csvfile)))
                csv_data_for_files[file_name] = parseCSV(csvfile, args.savecsv) # removes csvfile
                print("...{} done".format(os.path.basename(file_name)))
    else:
        if args.concurrentlong:
            test_dir = "{}/{}".format(root_test_dir, "concurrent_long")
        elif args.longshort:
            test_dir = "{}/{}".format(root_test_dir, "long_and_short")
        elif args.normal:
            test_dir = "{}/{}".format(root_test_dir, "normal")
        for (curr_dir, dirs, files) in os.walk(test_dir):
            for file_name in files:
                if file_name.endswith(".zst"):
                    # check if saved first
                    csvfile = os.path.abspath(file_name).split(".pcap.zst")[0] + ".csv"
                    if args.savecsv:
                        if analysis_type == "latency":
                            csvfile = "{}/rtt/{}/{}/{}.csv".format(
                                root_csv_dir, test_str, os.path.basename(curr_dir), file_name.split(".pcap.zst")[0])
                        else:
                            csvfile = "{}/info/{}/{}/{}.csv".format(
                                root_csv_dir, test_str, os.path.basename(curr_dir), file_name.split(".pcap.zst")[0])
                    
                    if not os.path.exists(csvfile):
                        file_with_path = curr_dir + "/" + file_name
                        # decompress one at a time size these files are big
                        print("Decompressing {}...".format(os.path.basename(file_name)))
                        pcapfile = decompress(file_with_path)
                        if not os.path.exists(pcapfile):
                            print("Failed to create pcap file for {}".format(file_name))
                            sys.exit(1)

                        # make different csv depending on the test, remove pcap too
                        print("Parsing {} to csv...".format(os.path.basename(file_name)))
                        new_csvfile = make_csv(pcapfile, csvfile, analysis_type)
                        if not os.path.exists(new_csvfile):
                            print("Failed to create csv file for {}".format(file_name))
                            sys.exit(1)

                    # extract data for each file
                    print("Extracting from {}...".format(os.path.basename(csvfile)))
                    csv_data_for_files[file_name] = parseCSV(csvfile, args.savecsv) # removes csvfile
                    print("...{} done".format(os.path.basename(file_name)))
    
    # run analysis on files
    print("\n")
    if args.processcsv:
        sys.exit(0)
    elif args.bandwidth:
        print("Analyzing bandwidth...")
        bw.getBandwidth(csv_data_for_files, graph_dir)
    elif args.loss:
        print("Analyzing packet loss...")
        if args.aggregate:
            aggregate_loss(csv_data_for_files, graph_dir, test_str)
        else:
            analyze_loss(csv_data_for_files, graph_dir, test_str)
    elif args.latency:
        print("Analyzing per packet latency...")
        if args.aggregate:
            aggregate_latency(csv_data_for_files, graph_dir)
        else:
            getLatency(csv_data_for_files, graph_dir)
        
    print("Analysis complete.")
    return

formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=30)
parser = argparse.ArgumentParser(prog="PROG",
    description="829 Project Network Trace Analysis",
    usage="python run_analysis.py",
    formatter_class=formatter)

required_args = parser.add_argument_group("required")
location_args = required_args.add_mutually_exclusive_group(required=True)
location_args.add_argument("-l", "--location",
    help="location trace is taken in, used for file name\n")
location_args.add_argument("-A", "--aggregate",
    action="store_true",
    help="analyze aggregates\n")
# required_args.add_argument("-I", "--ips",
#     help="file containing list of server IPs, \n*** DON'T INCLUDE ENDPOINT OR TRIAL # ***\n")
required_args.add_argument("-p", "--processcsv", 
    action="store_true",
    help="only process csvs\n")
required_args.add_argument("-P", "--path", 
    help="path to root directory of analysis results\n")
required_args.add_argument("-T", "--testdir",
    help="directory name of the test directory (not full path)")
required_args.add_argument("-G", "--graphdir",
    help="directory name for where the graphs should be saved (not full path)")
required_args.add_argument("-c", "--csvdir", 
    help="path to root directory of where to store csvs\n")
required_args.add_argument("-S", "--savecsv",
    action="store_true",
    help="save CSVs and look for saved CSVs\n")
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
    args = parser.parse_args()
    args.func(args)
