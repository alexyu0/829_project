# GE model constants
GOOD_STATE = "G"
BAD_STATE = "B"

# Network and symbol constants
DUMMY = None
PACKET_PAYLOAD = 1300
PACKET_HEADER = 200
MTU_PACKETS = "MTU_SIZE"
SYMBOL_PACKETS = "1_SYMBOL_SIZE"
RATE_5Mbps = 625000 # in B/s, converted from 5 MHz = 5 Mbps

# video constants
RES_1080P = (1920, 1080)
FPS_60 = 60

# RaptorQ constants
RQ_OVERHEAD = 3
RQ_RATE = 0.9

# analysis constants
BUCKET_SIZE = 0.1
RAW_CSV_DIR = "models/raw_csvs"
BEST_CSV_DIR = "models/best_csvs"
RQ_CSV_PATH = "models/raw_csvs/RQ_results_{}_{}.csv"
MIDAS_CSV_PATH = "models/raw_csvs/MiDAS_results_{}_{}.csv"
ge_ref = {
    "1": "0.01,0.5,1,0",
    "2": "0.018,0.2401,0.9994,0.2946",
    "3": "0.0279,0.209,0.9944,0.177",
    "4": "0.0461,0.168,0.9884,0.108"
}
ge_bler_ref = {
    "1": 2,
    "2": 5,
    "3": 10,
    "4": 20
}
ge_ref_keys = ["1", "2", "3", "4"]
LATENCY_VALS = [40, 50, 75, 100]
METRICS = ["agg", "latency", "bw", "loss"]
GRAPH_DIR = "models/analysis_graphs"
metric_col_map = {
    ("RQ", "agg"): 8,
    ("RQ", "latency"): 5,
    ("RQ", "bw"): 6,
    ("RQ", "loss"): 7,
    ("MiDAS", "agg"): 11,
    ("MiDAS", "latency"): 8,
    ("MiDAS", "bw"): 9,
    ("MiDAS", "loss"): 10
}
METRIC_LABELS = {
    "agg" : "Aggregate metric", 
    "latency" : "Latency of frame delivery (ms)", 
    "bw" : "Additional data used (%)", 
    "loss" : "Percentage of data lost (%)"
}
METRIC_TITLES = {
    "agg" : "Aggregate Metric", 
    "latency" : "Frame Delivery Latency", 
    "bw" : "Additional Data", 
    "loss" : "Loss Rate"
}
