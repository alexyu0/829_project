import constants
import csv

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
