import argparse
import cv2
import logging
import numpy as np
import os
import sys
import time

from flask import Flask, jsonify, request, Response
from . import analytic_pb2

class EndpointAction(object):

    def __init__(self, action):
        self.action = action

    def __call__(self, *args):
        answer = self.action()
        return answer

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

def render(frame, req, resp, window_name="Output"):
    for roi in resp.roi:
        if roi.HasField("box"):
            box = roi.box
            display_text = "{!s} - {!s}".format(roi.classification, roi.confidence)
            cv2.rectangle(frame, (box.corner1.x, box.corner1.y), (box.corner2.x, box.corner2.y), (255, 0, 0), 2)
            cv2.putText(frame, display_text, (box.corner1.x, box.corner1.y), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 0))
    cv2.imshow(window_name, frame)
    cv2.waitKey(1)

class AnalyticServer:
    def __init__(self, name, host="::", port=50051):
        self.app = Flask(name)
        self.host = host
        self.port = port
        self.func = None
        self.add_endpoint("/process", "process", self.process, methods=["POST"])
        
    def add_endpoint(self, endpoint=None, endpoint_name=None, handler=None, methods=None):
        self.app.add_url_rule(endpoint, endpoint_name, EndpointAction(handler), methods=methods)

    def run(self):
        logging.info("Server running on {!s}:{!s}".format(self.host, self.port))
        self.app.run(host=self.host, port=self.port)

    def register_process_func(self, func):
        self.process_func = func

    def register_output_func(self, output_func):
        self.output_func = output_func

    def process(self, req, resp):
        frame = cv2.imdecode(np.fromstring(req.frame.img, dtype=np.uint8), 1)
        self.process_func(frame, req, resp)
        if self.output_func:
            self.output_func(frame, req, resp)


class Streamer:
    def __init__(self, func=None, output_func="default"):
        self.analytic_func = func
        self.output_func = default_output_func
        if output_func == "render":
            self.output_func = render
        

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
        
    def serve(self, port=50051):
        analytic_server = AnalyticServer(name=__name__, port=port)
        analytic_server.register_process_func(self.process_frame)
        analytic_server.register_output_func(self.output_func)
        analytic_server.run()  


    def run(self):
        """ The run function starts a process to send image/video data to the analtyic. Arguments can
        be used to specify a connected camera, video file, or image file to be processed, or used to
        run the application in server mode."""

        parser = argparse.ArgumentParser()
        parser.add_argument("--videofile", default=None, help="Video file to process")
        parser.add_argument("--imagefile", default=None, help="Image file to process")
        parser.add_argument("--camera_id", default=0, help="Camera ID on the host machine")
        parser.add_argument("--serve", default=False, help="If true starts up an analytic service", action="store_true")
        parser.add_argument("--service_port", default=50051, help="Port on which to run the analytic service")
        args = parser.parse_args()

        if args.serve:
            self.serve(port=args.service_port)
        else:
            if args.videofile:
                self.stream_video(args.videofile)
            elif args.imagefile:
                self.stream_image(args.imagefile)
            elif args.camera_id:
                self.stream_camera(args.camera_id)
            else:
                raise ValueError("No Valid option specified. Must specify a source (Video, Image, or Camera")


