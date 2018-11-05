import argparse
import csv
import matplotlib.pyplot as plt
import numpy as np
import sys

# Default values.
bucketSize = 0.1
prefix = "K"

# Constants on where the data is located.
TIME_NAME = "Time"
TIME_COL = 1
INFO_NAME = "Info"
INFO_COL = 6

# Hardcoded ports to file.
def getPortsBasedOnFile(file):
	srcPort = -1
	destPort = -1
	if "alexhome_10MB_1c_0l_client_1" in file:
		srcPort = 62387
		destPort = 5201
	elif "alexhome_10MB_1c_0l_client_2" in file:
		srcPort = 62388
		destPort = 5201
	elif "alexhome_100MB_1c_0l_client_1" in file:
		srcPort = 62387
		destPort = 5201
	elif "alexhome_100MB_1c_0l_client_2" in file:
		srcPort = 62388
		destPort = 5201
	return srcPort, destPort

# Raw CSV parser, includes the table headers.
def parseCSV(file):
	csvData = []
	with open(file, newline='') as csvfile:
		csvReader = csv.reader(csvfile)
		for row in csvReader:
			csvData.append(row)
	return csvData

# Determines whether this message was between the given ports.
# The order of the ports doesn't matter.
# Note: 2 spaces between characters.
def isBetweenPorts(info, srcPort, destPort):
	# See if the message is between src > dest.
	if ("%d  >  %d" % (srcPort, destPort)) in info:
		return True

	# See if the message is between dest > src.
	if ("%d  >  %d" % (destPort, srcPort)) in info:
		return True

	return False

# Determine if data is transferred by checking the info column
# and looking at the Len of the message sent.
# Non-zero Len is data transferred.
def isDataTransferred(info):
	for infoField in info.split(" "):
		if "Len=" in infoField:
			lenInfo = infoField.split("=")
			# The amount of data is after the equals sign.
			return True, int(lenInfo[1])
	return False, 0


def calculateBandwidth(csvData, srcPort, destPort):
	print("Calculating bandwidth between port %d and port %d..." % (srcPort, destPort))

	bucketI = 0
	bucketStart = 0
	nextBucket = bucketStart + bucketSize

	buckets = []
	dataPerBucketList = []
	dataForBucket = 0

	# Ignore title row (row 0).
	for i in range(1, len(csvData)):
		row = csvData[i]

		# See if we are on the next bucket.
		if float(row[TIME_COL]) >= nextBucket:
			buckets.append(nextBucket)  # Append x-axis point.
			nextBucket += bucketSize  # Go to next bucket.
			dataPerBucketList.append(dataForBucket)  # Append y-axis point.
			dataForBucket = 0  # Reset y-axis sum.

		# Sum the amount of data transferred, if it was in this row.
		if isBetweenPorts(row[INFO_COL], srcPort, destPort):
			isData, dataLen = isDataTransferred(row[INFO_COL])
			if isData:
				dataForBucket += dataLen  # Length of data transferred.

	return buckets, dataPerBucketList

# To get bandwidth, divide the data transferred in that bucket time range
# by the size of that time range.
# Also changes the amount to match the given prefix.
def divideByBuckets(buckets, dataPerBucketList, prefix):
	bandwidthPerBucket = []
	for i in range(len(buckets)):
		bw = float(dataPerBucketList[i]) / float(buckets[i])  # In bytes/sec.
		if prefix == "K":  # Kilo
			bw *= 1000
		elif prefix == "M":  # Mega
			bw *= 1000000
		bandwidthPerBucket.append(bw)
	return bandwidthPerBucket

# Plot.
def plotBandwidth(minBucket, maxBucket, results, prefix, files):
	xaxis = np.arange(minBucket, maxBucket, bucketSize)

	if len(results) == 0:
		plt.plot(xaxis[:len(results[0])], results[0])
		plt.title("Bandwidth vs. Time for file %s" % files[0])
	else:
		for i in range(len(results)):
			plt.plot(xaxis[:len(results[i])], results[i], label=files[i].split("/")[-1])
			plt.title("Bandwidth vs. Time")
	plt.xlabel("Time (in buckets of %0.2f seconds)" % bucketSize)
	plt.ylabel("Bandwidth (in data %sB/second)" % prefix)
	plt.legend()
	plt.show()


# Main.
def getBandwidth():
	if len(sys.argv) <= 1:
		print("Please give at least one file as an argument.")
		exit()

	# 2D array of results. Indexing into results gives the data for the y-axis.
	results = []
	files = []
	minBucket = 0.0 #+ bucketSize  # Don't include 0.
	maxBucket = 0.0  # Max interval on x-axis.

	for argNum in range(1, len(sys.argv)):
		file = sys.argv[argNum]
		files.append(file)
		print("Getting bandwidth calculations on file %s with bucket size %0.3f..." % (file, bucketSize))
		srcPort, destPort = getPortsBasedOnFile(file)

		print("Looking for data btwn ports %d and %d..." % (srcPort, destPort))

		csvData = parseCSV(file)
		print("Got CSV data, row 1 = ", csvData[1])

		buckets, dataPerBucketList = calculateBandwidth(csvData, srcPort, destPort)
		if buckets[-1] > maxBucket:
			maxBucket = buckets[-1] #+ bucketSize  # Include max (last num is excluded).

		print("Buckets = ", buckets)
		print("Data per bucket = ", dataPerBucketList)

		bandwidthPerBucket = divideByBuckets(buckets, dataPerBucketList, prefix)

		print("Bandwidth per bucket = ", bandwidthPerBucket)
		results.append(bandwidthPerBucket)

		print("Calculations on file %s complete." % file)

	print("Plotting all files...")
	plotBandwidth(minBucket, maxBucket, results, prefix, files)
	print("Plotting complete.")

	

# Command-line flags are defined here.
# def parse_arguments():
#     parser = argparse.ArgumentParser(description="Specify data to aggregate.")
#     parser.add_argument("--bucket-size", dest="bucketSize", type=float,
#     					default=bucketSize, help="Size of time buckets.")
#     return parser.parse_args()


# Parse command-line arguments.
# args = parse_arguments()
# bucketSize = args.bucketSize
getBandwidth()