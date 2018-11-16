import argparse
import csv
import matplotlib.pyplot as plt
import sys

# Default values.
bucketSize = 0.1
srcPort = "62388"
destPort = "5201"
prefix = "K"
#prefix = "M"

# Constants on where the data is located.
TIME_COL = 0
SRCPORT_COL = 2
DESTPORT_COL = 3
LEN_COL = 6

# Determines whether this message was between the given ports.
# The order of the ports doesn't matter.
# Note: 2 spaces between characters.
def isBetweenPorts(row):
	# See if the message is between src > dest.
	if row[SRCPORT_COL] == srcPort and row[DESTPORT_COL] == destPort:
		return True
	return False
	# if ("%s  >  %s" % (srcPort, destPort)) in info:
	# 	return True

	# # See if the message is between dest > src.
	# if ("%s  >  %s" % (destPort, srcPort)) in info:
	# 	return True

	# return False

# Determine if data is transferred by checking the info column
# and looking at the Len of the message sent.
# Non-zero Len is data transferred.
def isDataTransferred(row):
	length = int(row[LEN_COL])
	if length > 0:
		return True, length
	return False, 0
	# for infoField in info.split(" "):
	# 	if "Len=" in infoField:
	# 		lenInfo = infoField.split("=")
	# 		# The amount of data is after the equals sign.
	# 		return True, int(lenInfo[1])
	# return False, 0


def calculateBandwidth(csvData, srcPort, destPort):
	print("Calculating bandwidth between port %s and port %s..." % (srcPort, destPort))

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
		if isBetweenPorts(row):
			isData, dataLen = isDataTransferred(row)
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
def plotBandwidth(buckets, bandwidthPerBucket, prefix, filename, graphDir):
	print("Plotting bandwidth...")
	filename_no_ext = filename.split(".")[0]
	plt.plot(buckets, bandwidthPerBucket)
	plt.xlabel("Time (in buckets of %0.2f seconds)" % bucketSize)
	plt.ylabel("Bandwidth (in data %sB/second)" % prefix)
	plt.title("Bandwidth vs. Time for file %s" % (filename_no_ext))
	graphfile = graphDir + "/" + filename_no_ext + ".png"
	print("Saving figure to graph dir {} ...".format(graphDir))
	plt.savefig(graphfile)
	#plt.show()

# Main.
def getBandwidth(csvDataForFiles, graphDir):

	for filename in csvDataForFiles:
		print("Getting bandwidth calculations on file %s wtih bucket size %0.3f..." % (filename, bucketSize))

		csvData = csvDataForFiles[filename]
		print("Got CSV data, row 1 = ", csvData[1])

		buckets, dataPerBucketList = calculateBandwidth(csvData, srcPort, destPort)
		print("Separated bandwidth data into buckets...")

		bandwidthPerBucket = divideByBuckets(buckets, dataPerBucketList, prefix)
		print("Got bandwidth per bucket...")

		plotBandwidth(buckets, bandwidthPerBucket, prefix, filename, graphDir)
		print("Calculations on file %s complete." % filename)

# Command-line flags are defined here.
# def parse_arguments():
#     parser = argparse.ArgumentParser(description="Specify data to aggregate.")
#     parser.add_argument("--bucket-size", dest="bucketSize", type=float,
#     					default=bucketSize, help="Size of time buckets.")
#     return parser.parse_args()


# Parse command-line arguments.
# args = parse_arguments()
# bucketSize = args.bucketSize
# getBandwidth()