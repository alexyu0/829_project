import argparse
import csv
import matplotlib.pyplot as plt
import numpy as np
import sys
import os

from collections import defaultdict
from helpers import group_files


# Default values.
bucketSize = 0.00005
minBucket = 0.0
maxBucket = 0.009

# removes csv file after extracting csv data
def parseCSV(file, save):
    csvData = []
    with open(file, newline='') as csvfile:
        csvReader = csv.reader(csvfile)
        for row in csvReader:
            csvData.append(row)
    csvfile.close()
    return csvData


# Plot possibly multiple files for latency.
# def plotLatency(buckets, results, files, graphDir):
# 	xaxis = buckets

# 	print("results", results)

# 	if len(results) == 0:
# 		plt.plot(xaxis[:len(results[0])], results[0])
# 		plt.title("Per Packet Latency for file %s" % files[0])
# 	else:
# 		for i in range(len(results)):
# 			plt.plot(xaxis[:len(results[i])], results[i], label=files[i].split("/")[-1].split(".")[0])
# 			plt.title("Per Packet Latency For One 100MB, One 1MB Downloads For Three Trials")
# 	plt.xlabel("Latency(in buckets of %0.2f seconds)" % bucketSize)
# 	plt.ylabel("Number of packets")
# 	plt.legend()
# 	plt.show()
# 	graphfile = graphDir + "/" + filename_no_ext + ".png"
# 	print("Saving figure to graph dir {} ...".format(graphDir))
# 	plt.savefig(graphfile)


# plot single line for average latency across trials.
def plotLatency(buckets, results, endpoint_no, graphDir):
    yMax = max(results)
    plt.ylim(top=(yMax + yMax/8.0))
    # if "server" not in endpoint_no:
    #     for last_i in range(len(results) - 1, -1, -1):
    #         if int(results[last_i]) > 0:
    #             break
    #     buckets = buckets[:last_i]
    #     xMax = buckets[min(last_i + 1, len(buckets) - 1)]
    #     print(xMax, (xMax + xMax/8.0), yMax, (yMax + yMax/8.0))
    #     plt.xlim(left=(-xMax/8.0), right=(xMax + xMax/8.0))
    #     results = results[:last_i]

    plt.plot(buckets, results)
    plt.title("Per Packet Latency for endpoint %s" % endpoint_no)
    plt.xlabel("Latency(in buckets of %0.5f seconds)" % bucketSize)
    plt.ylabel("Number of packets")
    plt.legend()
    #plt.show()
    location = os.path.basename(graphDir)
    test_type = os.path.basename(os.path.dirname(graphDir))
    graphfile = "{}/Latency_{}_{}_{}.png".format(graphDir,
        test_type,
        location,
        endpoint_no)
    print("Saving figure {} to graph dir {} ...".format(graphfile, graphDir))
    plt.savefig(graphfile)

    plt.clf()
    plt.close()

def plotCDF(cdf_results, endpoint_no, graphDir):
    sorted_res = np.sort(cdf_results)
    y_values = np.arange(1, len(sorted_res) + 1) / len(sorted_res)
    plt.plot(sorted_res, y_values, marker=".", linestyle="none")

    plt.title("Per Packet Latency CDF for endpoint %s" % endpoint_no)

    # yMax = max(results)
    # plt.ylim(top=(yMax + yMax/8.0))
    # if "server" not in endpoint_no:
    #     for last_i in range(len(results) - 1, -1, -1):
    #         if int(results[last_i]) > 0:
    #             break
    #     buckets = buckets[:last_i]
    #     xMax = buckets[min(last_i + 1, len(buckets) - 1)]
    #     print(xMax, (xMax + xMax/8.0), yMax, (yMax + yMax/8.0))
    #     plt.xlim(left=0, right=(xMax + xMax/8.0))

    plt.xlabel("Latency(in buckets of %0.5f seconds)" % bucketSize)
    plt.ylabel("Percentile")
    plt.legend()
    #plt.show()
    location = os.path.basename(graphDir)
    test_type = os.path.basename(os.path.dirname(graphDir))
    graphfile = "{}/LatencyCDF_{}_{}_{}.png".format(graphDir,
        test_type,
        location,
        endpoint_no)
    print("Saving figure {} to graph dir {} ...".format(graphfile, graphDir))
    plt.savefig(graphfile)

    plt.clf()
    plt.close()


# Group the latencies (elements of CSV data) by the number of times they occur
# and are between the range given by the buckets.
def sortIntoBuckets(buckets, csvData):
    countsInBuckets = np.zeros(len(buckets))
    for i in range(len(buckets)):
        minVal = buckets[i]
        if i != len(buckets) - 1:
            maxVal = buckets[i+1]
        else:
            maxVal = maxBucket

        for latencyArr in csvData:
            latency = float(latencyArr[0])
            if minVal <= latency and latency < maxVal:
                countsInBuckets[i] += 1
    return countsInBuckets

# For each bucket, divide by the number of trials.
def averageOverTrials(results, num_trials):
    agg_results = np.zeros(max([len(r) for r in results]))
    for trial in results:
        for i in range(len(trial)):
            agg_results[i] = agg_results[i] + trial[i]
    return [result/float(num_trials) for result in agg_results]

# Main.
def getLatency(csvDataForFiles, graphDir):
    print("Running latency script...")

    numBuckets = int((maxBucket - minBucket) / float(bucketSize))
    buckets = np.linspace(minBucket, maxBucket, num=numBuckets, endpoint=False)

    # key is a run, each run's list should be averaged
    runs = group_files(csvDataForFiles, False)

    for endpoint_no in runs:
        # 2D array of results. Indexing into results gives the data for the y-axis.
        results = []
        cdf_results = []

        trials = runs[endpoint_no]
        num_trials = len(trials)

        for t in range(num_trials):

            csvData = trials[t]

            print("Getting latency calculations for endpoint %s trial %d with bucket size %f..." % (endpoint_no, t, bucketSize))

            # Get the tail latency by keeping track of individual packets,
            # find when they are received (or ACK'd), and note that latency.
            # Group latency values into buckets to get tail latency (x-axis)
            # vs. number of packets (y-axis).

            countsInBuckets = sortIntoBuckets(buckets, csvData)

            results.append(countsInBuckets)
            cdf_results.append([float(latencyArr[0]) for latencyArr in csvData])

            #print("Calculations for that trial complete." % file)

        print("All trials for endpoint %s gathered. Averaging over %d trials..." %(endpoint_no, num_trials))
        results = averageOverTrials(results, num_trials)
        cdf_results = averageOverTrials(cdf_results, num_trials)

        print("Plotting endpoint %s..." % endpoint_no)
        print("len bucks %d len res %d " % (len(buckets), len(results)))
        plotLatency(buckets, results, endpoint_no, graphDir)
        plotCDF(cdf_results, endpoint_no, graphDir)

    print("Plotting complete for all runs.")


# BELOW is for testing locally.
# CSV_DATA = parseCSV("tmp.csv", False)
# CSV_DATA_FOR_FILES = {}

# #location_duration_endpoint_run
# CSV_DATA_FOR_FILES["tmploc_120s_client1_1.pcap.zst"] = CSV_DATA
# getLatency(CSV_DATA_FOR_FILES, "tmp")
