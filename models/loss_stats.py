import sys
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import pprint

import model_constants

def compute_average_hist(loss_bursts):
    average_loss_bursts = defaultdict(int)
    for hist in loss_bursts:
        for length in hist:
            average_loss_bursts[length] += hist[length]
    
    to_del = []
    for length in average_loss_bursts:
        average_loss_bursts[length] = int(average_loss_bursts[length] / len(loss_bursts))
        if (average_loss_bursts[length] == 0):
            to_del.append(length)
    for length in to_del:
        average_loss_bursts.pop(length, None)
    
    return average_loss_bursts

def compute_average_timescale(loss_timescales):
    time_buckets = []
    average_data_buckets = []
    for buckets in loss_timescales:
        for i in range(0, len(buckets[1])):
            if i >= len(average_data_buckets):
                # first one so can just append
                average_data_buckets.append(buckets[1][i])
            else:
                average_data_buckets[i] += buckets[1][i]

            if i >= len(time_buckets):
                # first one so can just append
                time_buckets.append(buckets[0][i])

    for i in range(0, len(average_data_buckets)):
        average_data_buckets[i] = int(average_data_buckets[i] / len(loss_timescales))

    return (time_buckets, average_data_buckets)

def graph_hist(loss_bursts, endpoint, name_pre, graph_dir):
    """
    Graphs the histogram generated from loss_length_hist
    """
    keys = sorted([int(k) for k in loss_bursts.keys()])
    g = plt.bar(range(0, len(keys)), [v for (k,v) in sorted(loss_bursts.items())], width=0.8)
    ax = plt.gca()
    plt.xticks(range(0, len(keys)))
    if len(keys) > 20:
        ax.set_xticklabels(keys, fontsize=7)
    else:
        ax.set_xticklabels(keys)
    plt.xlabel("Burst size")
    plt.ylabel("Frequency")
    plt.title("Frequency of loss burst sizes for {} {}".format(name_pre, endpoint))

    height_space = 0
    if len(loss_bursts.values()) != 0:
        height_space = int(max(loss_bursts.values()) * 0.02)
    for i in range(0, len(g.patches)):
        rect = g.patches[i]
        ax.text(rect.get_x() + rect.get_width()/2,
            rect.get_height() + height_space,
            loss_bursts[keys[i]],
            ha="center",
            va="bottom").set_fontsize(7)

    plt.savefig("{}/LossBurstHist_{}_{}.png".format(
        graph_dir, name_pre, endpoint))
    plt.clf()
    plt.close()

def graph_loss_timescale(timescale, endpoint, name_pre, graph_dir):
    time_buckets, data_buckets = timescale
    plt.plot(time_buckets, data_buckets)
    plt.xlabel("Time (in buckets of %0.2f seconds)" % model_constants.BUCKET_SIZE)
    plt.ylabel("Packets lost")
    plt.title("Packets lost over time for {} {}".format(name_pre, endpoint))
    plt.savefig("{}/LossTime_{}_{}.png".format(
        graph_dir, name_pre, endpoint))
    plt.clf()
    plt.close()
