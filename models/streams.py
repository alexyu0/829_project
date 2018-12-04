from enum import Enum

import model_constants

class CompressionType(Enum):
    # all in bytes per second
    NETFLIX_HD = 1740000
    YOUTUBE_HD = 2400000
    H_264 = 16800000

class Frame:
    def __init__(self, size):
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
        return [Frame(compressed_frame_size) for i in range(0, self.fps * duration)]
