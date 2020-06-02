import cv2
import logging
from vidstreamer import Streamer, analytic_pb2

def analytic_foo(frame, req, resp):
    print("Frame size: {!s}".format(frame.shape))
    roi = analytic_pb2.RegionOfInterest()
    roi.classification = "Person"
    roi.confidence = 0.506
    resp.roi.append(roi)

def render(frame, req, resp):
    output = [req.frame_num]
    outstring = """Detections for frame_num: {!s}\n"""
    for roi in resp.roi:
        # Assume bounding box for now
        # TODO check for bounding box vs pixel mask
        roi_string = "\t Class: {!s} \t Confidence:{!s}"
        outstring += roi_string
        if roi.classification == "":
            roi.classification = "No classification"
        output.append(roi.classification)
        output.append(roi.confidence)
    print(outstring.format(*output))
    cv2.imshow("frame", frame)
    cv2.waitKey(1)
    

if __name__ == "__main__":
    streamer = Streamer(func=analytic_foo)
    streamer.register_output_func(render)
    try:
        streamer.run()
    finally:
        cv2.destroyAllWindows()