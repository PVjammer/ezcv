import argparse
import click
import cv2
import logging
import numpy as np
import os
import sys
import time

from flask import Flask, jsonify, request, Response
from . import analytic_pb2

class Context:
    pass

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
            self.output_func(frame, req, resp)
        return req, resp
        
    def serve(self, port=50051):
        analytic_server = AnalyticServer(name=__name__, port=port)
        analytic_server.register_process_func(self.process_frame)
        analytic_server.register_output_func(self.output_func)
        analytic_server.run()  

    def run(self, parameters=[], init_func=None):
        """ The run function starts a process to send image/video data to the analtyic. Arguments can
        be used to specify a connected camera, video file, or image file to be processed, or used to
        run the application in server mode. An optional intialization function that takes the streamer object 
        as an argument can be passed to do initialization steps (e.g., load a model using parameters passed in
        from the command line)"""
        x = CLI(self, options=parameters, init_func=init_func)
        if init_func:
            self.init_func = init_func
        x.run()

class StreamerParam:
    def __init__(self, name, default=None, type=None, helptext=None):
        self.name = name
        self.default = default
        self.type = type
        self.help = helptext

        # Convert any arguments passed in to options.
        if self.name[:2] != "--":
            self.name = "--{!s}".format(name)

class CLI:
    def __init__(self, streamer, options=[], init_func=None):
        """Creates a basic click CLI that can be extended with user options/arguments"""
        self.init_func = init_func
        def initialize(ctx, **kwargs):
            ctx.ensure_object(Context)
            ctx.obj.streamer = streamer
            ctx.obj.streamer.params = kwargs

        def image(ctx, imagefile):
            streamer = ctx.obj.streamer
            self.init_func(streamer)
            streamer.stream_image(imagefile)

        def video(ctx, videofile):
            streamer = ctx.obj.streamer
            self.init_func(streamer)
            streamer.stream_video(videofile)

        def camera(ctx, camera_id):
            streamer = ctx.obj.streamer
            self.init_func(streamer)
            streamer.stream_camera(camera_id)

        initialize = click.pass_context(initialize)
        image = click.pass_context(image)
        video = click.pass_context(video)

        opts = []
        for i in range(len(options)):
            opts.append(click.Option(param_decls=[options[i].name], default=options[i].default, type=options[i].type, help=options[i].help))
        self.main = click.Group(name="main", callback=initialize, params=opts)
        
        image_arg = click.Argument(param_decls=["imagefile"], type=str)
        img_cmd = click.Command(name="image", callback=image, params=[image_arg])
        self.main.add_command(img_cmd, name="image")

        video_arg = click.Argument(param_decls=["videofile"], type=str)
        vid = click.Command(name="video", callback=video, params=[video_arg])
        self.main.add_command(vid, name="video")

        camera_arg = click.Option(param_decls=["--camera_id"], default=0)
        cam = click.Command(name="camera", callback=camera, params=[camera_arg])
        self.main.add_command(cam, name="camera")
    
    def run(self):
        self.main(obj=Context())
    
    def add_options(self, options=[]):
        """Add options to the initialization function (main command) that can be passed 
        to all other functions. All option values are added to the streamer in the `streamer.params` 
        field"""
        opts = []
        for i in range(len(options)):
            opt.append(click.Option(param_decls=[options[i].name], default=options[i].default, type=options[i].type, help=options[i].help))