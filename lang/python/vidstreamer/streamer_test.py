import unittest
import numpy as np
from . import analytic_pb2
from .__init__ import Streamer


def analytic_test_func(frame, req, resp):
    if frame.shape != (256, 256):
        return
    if req.timestamp != 506:
        return
    if req.frame_num != 16:
        return

    roi = analytic_pb2.RegionOfInterest()
    roi.classification = "TestObject"
    roi.confidence = 0.506



class TestStreamer(unittest.TestCase):

    def test_proto(self):
        
        frame = np.ones((256, 256), dtype=int)
        streamer = Streamer(func=analytic_test_func)
        
        req, resp = streamer.process_frame(frame, timestamp=506, frame_num=16)
        self.assertEqual()


if __name__ == "__main__":
    unittest.main()