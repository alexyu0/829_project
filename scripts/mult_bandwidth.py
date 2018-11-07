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

class Packet():
	def __init__(self, seqNum, startTime):
		self.seqNum = seqNum
		self.acked = False
		self.minTime = startTime
		self.maxTime = 0

	def getLatency(self):
		if not self.acked: # Not acked yet, no latency yet.
			return -1
		return self.maxTime - self.minTime

	def updateTime(self, receivedTime):
		if self.maxTime == 0 or self.maxTime == self.minTime:
			self.maxTime = receivedTime
		elif receivedTime > self.maxTime:
			self.maxTime = receivedTime

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
		return True, "s"

	# See if the message is between dest > src.
	if ("%d  >  %d" % (destPort, srcPort)) in info:
		return True, "d"

	return False, "n"

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

# Gets the sequence number.
def getInfoField(info, field):
	for infoField in info.split(" "):
		if field in infoField:
			seqInfo = infoField.split("=")
			# The amount of data is after the equals sign.
			return int(seqInfo[1])
	return -1 # Should never get here.



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
		is_btwn_ports, from_which = isBetweenPorts(row[INFO_COL], srcPort, destPort)
		if is_btwn_ports:
			isData, dataLen = isDataTransferred(row[INFO_COL])
			if isData:
				dataForBucket += dataLen  # Length of data transferred.

	return buckets, dataPerBucketList


# With the given map of packets, get the latencies per packet.
def convertMapToLatency(buckets, dataPerBucket, packets):
	for key in packets:
		pkt = packets[key]
		latency = pkt.getLatency()
		if latency != -1:
			index = 0
			while index < len(buckets) and buckets[index] < latency:
				index += 1
			# At the index to add a count for this packet.
			if index != len(buckets):
				dataPerBucket[index] += 1



# Sum up the information in the maps.
def calculatePacketsLatency(srcPackets, destPackets):

	# Change x-axis here!
	numElements = 20
	buckets = np.linspace(0.0, 2.0, num=numElements, endpoint=True)
	dataPerBucketList = np.zeros(numElements)

	convertMapToLatency(buckets, dataPerBucketList, srcPackets)
	convertMapToLatency(buckets, dataPerBucketList, destPackets)

	return buckets, dataPerBucketList


# Get the tail latency by keeping track of individual packets,
# find when they are received (or ACK'd), and note that latency.
# Group latency values into buckets to get tail latency (x-axis)
# vs. number of packets (y-axis).
def calculateTailLatency(csvData, srcPort, destPort):
	srcPackets = dict() # Keys are SeqNums sent from the srcPort.
	destPackets = dict() # Keys are SeqNums sent from the destPort.
	

	# print("Not implemented error")
	# # TODO: remove when implemented
	# pass

	print("Calculating tail latency between port %d and port %d..." % (srcPort, destPort))

	bucketI = 0
	bucketStart = 0
	nextBucket = bucketStart + bucketSize

	buckets = []
	dataPerBucketList = []
	dataForBucket = 0

	# Ignore title row (row 0).
	for i in range(1, len(csvData)):
		row = csvData[i]
		info = row[INFO_COL]

		is_btwn_ports, from_which = isBetweenPorts(row[INFO_COL], srcPort, destPort)
		if is_btwn_ports:
			seqNum = int(getInfoField(info, "Seq"))
			ackNum = int(getInfoField(info, "Ack"))
			#receivedTime = int(getInfoField(info, "TSval"))
			receivedTime = float(row[TIME_COL])

			# Depending on who sent it, update the dictionaries of packets.
			if from_which == "s":  # Source sent to dest.
				# Check if this source packet exists, if not then add it.
				if seqNum not in srcPackets:
					srcPackets[seqNum] = Packet(seqNum, receivedTime)
				# Check if this is acknowledging a dest packet.
				if ackNum in destPackets:
					pkt = destPackets[ackNum]
					pkt.acked = True
					pkt.updateTime(receivedTime)

			elif from_which == "d":  # Dest sent to source.
				# Check if this dest packet exists, if not then add it.
				if seqNum not in destPackets:
					destPackets[seqNum] = Packet(seqNum, receivedTime)
				# Check if this is acknowledging a src packet.
				if ackNum in srcPackets:
					pkt = srcPackets[ackNum]
					pkt.acked = True
					pkt.updateTime(receivedTime)
			
	buckets, dataPerBucketList = calculatePacketsLatency(srcPackets, destPackets)

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
def plotBandwidth(minBucket, maxBucket, results, prefix, files, metric):
	xaxis = np.arange(minBucket, maxBucket, bucketSize)

	if len(results) == 0:
		plt.plot(xaxis[:len(results[0])], results[0])
		if metric == "bw":
			plt.title("Bandwidth vs. Time for file %s" % files[0])
		elif metric == "latency":
			plt.title("Per Packet Latency for file %s" % files[0])
	else:
		for i in range(len(results)):
			plt.plot(xaxis[:len(results[i])], results[i], label=files[i].split("/")[-1])
			if metric == "bw":
				plt.title("Bandwidth vs. Time")
			elif metric == "latency":
				plt.title("Per Packet Latency")
	plt.xlabel("Time (in buckets of %0.2f seconds)" % bucketSize)
	if metric == "bw":
		plt.ylabel("Bandwidth (in data %sB/second)" % prefix)
	elif metric == "latency":
		plt.ylabel("Latency (in seconds)")
	plt.legend()
	plt.show()


# Main.
def main(metric):
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

		if metric == "bw":
			buckets, dataPerBucketList = calculateBandwidth(csvData, srcPort, destPort)

			bandwidthPerBucket = divideByBuckets(buckets, dataPerBucketList, prefix)

			print("Bandwidth per bucket = ", bandwidthPerBucket)
			results.append(bandwidthPerBucket)

		elif metric == "latency":
			buckets, dataPerBucketList = calculateTailLatency(csvData, srcPort, destPort)

			results.append(dataPerBucketList)

		if buckets[-1] > maxBucket:
			maxBucket = buckets[-1] #+ bucketSize  # Include max (last num is excluded).

		print("Buckets = ", buckets)
		print("Data per bucket = ", dataPerBucketList)


		print("Calculations on file %s complete." % file)

	print("Plotting all files...")
	plotBandwidth(minBucket, maxBucket, results, prefix, files, metric)
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


main("latency")
