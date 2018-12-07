from enum import Enum

import model_constants

class CompressionType(Enum):
    # all in bytes per second
    NETFLIX_HD = 1740000
    YOUTUBE_HD = 2400000
    H_264 = 16800000

class Frame:
    def __init__(self, ts, size):
        self.ts = ts
        self.size = size

class FixedSizeStream:
    def __init__(self, resolution, fps):
        """
        Params:
         - resolution: resolution of video, (l, w)
         - fps: frame rate of video
        """
        self.resolution = resolution
        self.fps = fps
        self.frame_size_bytes = resolution[0] * resolution[1] * 3 # l * w * (RGB size)
    
    def generate_stream(self, duration, compression):
        """
        Generates a stream of frames of the given duration

        Params:
         - duration: duration of video in seconds
         - compression: which type of compression to be used
        """
        compressed_frame_size = (compression.value/self.fps) # compressed size per frame
        curr_ts = 0.0
        frames = []
        for i in range(0, self.fps * duration):
            frames.append(Frame(curr_ts, compressed_frame_size))
            curr_ts += 1.0/self.fps

        return frames

    def from_trace(self, trace_path):
        """
        Generates stream of frames in this format from trace specified by 
        trace_path
        """
        ts_col = 0
        frames = []
        with open(trace_path) as f:
            for line in f.readlines():
                line = line.split(" ")
                frames.append(Frame(
                    float((line[ts_col].split("="))[1]),
                    model_constants.PACKET_PAYLOAD + model_constants.PACKET_HEADER))
        
        return frames
