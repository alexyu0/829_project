import argparse
import csv
import matplotlib.pyplot as plt
import numpy as np
import sys


# Default values.
bucketSize = 0.000005
minBucket = 0.0
maxBucket = 0.0009


# Raw CSV parser, includes the table headers.
def parseCSV(file):
	csvData = []
	with open(file, newline='') as csvfile:
		csvReader = csv.reader(csvfile)
		for row in csvReader:
			csvData.append(row)
	return csvData

# Plot possibly multiple files for latency.
def plotLatency(buckets, results, files):
	xaxis = buckets

	print("buckets", buckets)
	print("results", results)

	if len(results) == 0:
		plt.plot(xaxis[:len(results[0])], results[0])
		plt.title("Per Packet Latency for file %s" % files[0])
	else:
		for i in range(len(results)):
			plt.plot(xaxis[:len(results[i])], results[i], label=files[i].split("/")[-1].split(".")[0])
			plt.title("Per Packet Latency For One 100MB, One 1MB Downloads For Three Trials")
	plt.xlabel("Latency(in buckets of %0.2f seconds)" % bucketSize)
	plt.ylabel("Number of packets")
	plt.legend()
	plt.show()


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

# Main.
def getLatency():
	if len(sys.argv) <= 1:
		print("Please give at least one file as an argument.")
		exit()

	# 2D array of results. Indexing into results gives the data for the y-axis.
	results = []
	files = []

	numBuckets = int((maxBucket - minBucket) / float(bucketSize))
	buckets = np.linspace(minBucket, maxBucket, num=numBuckets, endpoint=False)

	for argNum in range(1, len(sys.argv)):
		file = sys.argv[argNum]
		files.append(file)
		print("Getting bandwidth calculations on file %s wtih bucket size %0.3f..." % (file, bucketSize))

		csvData = parseCSV(file)
		print("Got CSV data, row 1 = ", csvData[1])

		# Get the tail latency by keeping track of individual packets,
		# find when they are received (or ACK'd), and note that latency.
		# Group latency values into buckets to get tail latency (x-axis)
		# vs. number of packets (y-axis).

		#buckets, dataPerBucketList = calculateBandwidth(csvData, srcPort, destPort)

		#bandwidthPerBucket = divideByBuckets(buckets, dataPerBucketList, prefix)

		countsInBuckets = sortIntoBuckets(buckets, csvData)

		results.append(countsInBuckets)

		print("Calculations on file %s complete." % file)

	print("Plotting all files...")
	plotLatency(buckets, results, files)
	print("Plotting complete.")


getLatency()