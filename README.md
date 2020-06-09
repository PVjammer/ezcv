# vidstreamer
v 0.1

# Overview 
VidStreamer is a library to enable wrapped prototyping of computer vision analytics for applications on images and videos. At present this library provides a typed schemas for input and output to obhect detectors that run on images or individual video frames. These schemas are used by the `Streamer` object (so named for it's eventual use in processing streaming video) to pass images to a registered object detection function and to process the results. The basic workflow is as follows:

 1) Create an object detection function 
 2) Instantiate the `Streamer` object in the main function of the program. Pass in the object detection function as an argument
 3) \[Optional\] Create and register an output function that acts on the output of the object detector (basic functions are included that display the images/frames with bounding box overlays or dump data to the command line.
 4) \[Optional\] Create parameters that will be optional arguments to the main command. Typical uses would be model specific parameters or paths for files to load
 5) \[Optional\] Create an init function which runs after arguments are parsed but before images/frames are processed.
 5) Call the `run()` method on the streamer, passing it any parameters you created and an init function if required
 
 Vidstreamer will create a Click based CLI with 3 commands
  1) `image`: which takes as argument an image file path and passes that to the object detector
  2) `video`: which takes as argument a video file path and passes each frame of the video to the object detector
  3) `camera`: which takes an optional argument for the camera ID and streams frames from the webcam to the object detector
  
 ## Installation
 ```bash
 $ git clone https://github.com/PVjammer/vidstreamer.git
 $ cd vidstreamer
 $ pip install .
 ```
 
  
 ## TODO
 * Add command to stand up service
 * Add support for other image/video functions
