import argparse
import cv2
import logging
import numpy as np
import os
import sys
import time

from . import analytic_pb2

def default_output_func(frame, req, resp):
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

class Streamer:
    def __init__(self, func=None):
        self.analytic_func = func
        self.output_func = default_output_func

    def check_func(self):
        if not self.analytic_func:
            raise NotImplementedError
    
    def stream_camera(self, camera_id):
        """ Stream an attached camera to the analytic. """
        self.check_func()
        cap = cv2.VideoCapture(int(camera_id))
        frame_num = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                logging.info("No frame available")
                break
            self.process_frame(frame, timestamp=time.time(), frame_num=frame_num)
            frame_num += 1

    def stream_image(self, imagefile):
        self.check_func()
        img = cv2.imread(imagefile)
        req, resp = self.process_frame(img, timestamp=time.time(), frame_num=0)


    def stream_video(self, videofile):
        self.check_func()
        cap = cv2.VideoCapture(videofile)
        frame_num = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                logging.info("No frame available")
                break
            self.process_frame(frame, timestamp=time.time(), frame_num=frame_num)
            frame_num += 1

    def register_output_func(self, output_func):
        self.output_func = output_func

    def process_frame(self, frame, timestamp=None, frame_num=None):
        """ Process a video frame with the registered analytic """
        req = analytic_pb2.InputFrame(frame_num=frame_num, timestamp=timestamp)
        resp = analytic_pb2.FrameData()
        resp.start_time_millis = int(round(time.time()*1000))
        self.analytic_func(frame, req, resp)
        resp.end_time_millis = int(round(time.time()*1000))
        if self.output_func:
            print(frame.shape)
            self.output_func(frame, req, resp)
        return req, resp
        
    def run(self):
        """ The run function starts a process to send image/video data to the analtyic. Arguments can
        be used to specify a connected camera, video file, or image file to be processed, or used to
        run the application in server mode."""

        parser = argparse.ArgumentParser()
        parser.add_argument("--videofile", default=None, help="Video file to process")
        parser.add_argument("--imagefile", default=None, help="Image file to process")
        parser.add_argument("--camera_id", default=0, help="Camera ID on the host machine")
        args = parser.parse_args()

        if args.videofile:
            self.stream_video(args.videofile)
        elif args.imagefile:
            self.stream_image(args.imagefile)
        elif args.camera_id:
            self.stream_camera(args.camera_id)
        else:
            raise ValueError("No Valid option specified. Must specify a source (Video, Image, or Camera")


