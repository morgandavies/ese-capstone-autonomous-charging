# Helper functions for PiCamera usage

from picamera import PiCamera
import picamera.array
import cv2
import numpy as np

# Simple init function
# Assumes camera itself has been initiated with the with block and initializes settings and stream
def cam_init(cam, CAM_WIDTH,CAM_HEIGHT):
  cam.resolution= (CAM_WIDTH,CAM_HEIGHT)
  cam.framerate = 30    # Using same frame rate as from ESE 205, which is also the default (30)
  stream = picamera.array.PiRGBArray(cam)
  return stream

# Capture a photo. If debug is true, a camera feed will also display
def cam_cap(cam, stream, debug=False):
  cam.capture(stream, format='bgr')
  img = stream.array
  stream.truncate(0)
  if debug:
#    cv2.imshow("Capture",img)
    cv2.imwrite("cam_cap_debug.jpg",img)
  return img

# Given an opened photo, find center of mass of a given color if there is enough of the color visible
def img_search(img, min_hsv, max_hsv, debug=False):
  hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
  mask = mask = cv2.inRange(hsv, min_hsv, max_hsv)
  mask_blur = cv2.blur(mask, (5,5))
  mask_thresh = cv2.threshold(mask_blur, 200, 255, cv2.THRESH_BINARY)[1]
  if debug:
#    cv2.imshow("Image Search Mask",mask_thresh)
    cv2.imwrite("img_search_mask.jpg",mask_thresh)

  # Determine if there are enough white pixels to identify the tape within the photo, or conclude the tape is out of the frame
  h, w = img.shape[:2]
  proportion = np.sum(mask_thresh==255)/(h*w)
  if debug:
    print(f'Flagged {np.sum(mask_thresh==255)} out of {h*w} = {proportion} of total pixels')
  if proportion < 0.01:     # Set minimum proportion of correctly colored pixels here
    if debug:
       print('Did not find marker')
    return None

  # Find center of mass of mask
  M = cv2.moments(mask_thresh)
  cX = int(M["m10"] / M["m00"])
  cY = int(M["m01"] / M["m00"])

  if debug:
    print(f'Found center of marker at ({cX},{cY})')
#   img_circled = cv2.circle(img, (cX,cY), (0,255,0), 2)
#   cv2.imshow("Circled Center of Marker",img_circled)
#   cv2.imwrite("marker_circled.jpg",img_circled)

  return [cX,cY]

def img_circle(img,cX,cY):
   img = cv2.circle(img,(cX,cY),2,(0,255,0))
   return img
