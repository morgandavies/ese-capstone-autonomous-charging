# Image processing helper functions.
# Using simple color detection method.

import cv2
import numpy as np

# Given an opened photo and range of acceptable hsv values, create a mask highlighting pixels matching the target color
def create_mask(img, min_hsv, max_hsv, debug=False):
  hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
  mask = cv2.inRange(hsv, min_hsv, max_hsv) #mask for blue
  mask_blur = cv2.blur(mask, (5,5))
  mask_thresh = cv2.threshold(mask_blur, 200, 255, cv2.THRESH_BINARY)[1]
  if debug:
#     cv2.imshow("Image Search Mask",mask_thresh)
    cv2.imwrite("img_search_mask.jpg",mask_thresh)
  return mask_thresh

# Given an opened B&W photo, return the proportion of white pixels out of the total
def mask_ratio(img, debug=False):
  h, w = img.shape[:2]
  proportion = np.sum(img==255)/(h*w)
  return proportion
  
# Given an opened B&W photo, find center of mass
# Note that this function performs the function of mask_ratio() in addition to finding the center of mass
def find_com(mask, img, debug=False):
  # Determine if there are enough white pixels to identify the tape within the photo, or conclude the tape is out of the frame
  h, w = img.shape[:2]
  proportion = np.sum(mask==255)/(h*w)
  if debug:
    print(f'Flagged {np.sum(mask==255)} out of {h*w} = {proportion} of total pixels')
  if proportion < 0.01:     # Set minimum proportion of correctly colored pixels here
    if debug:
       print('Did not find marker')
       cv2.imwrite("img_search_circled.jpg",img)
    return None

  # Find center of mass of mask
  M = cv2.moments(mask)
  cX = int(M["m10"] / M["m00"])
  cY = int(M["m01"] / M["m00"])

  if debug:
    print(f'Found center of marker at ({cX},{cY})')
    img_circled = cv2.circle(img, (cX,cY), 1, (0,255,0), 2)
#    cv2.imshow("Circled Center of Marker",img_circled)
    cv2.imwrite("img_search_circled.jpg",img_circled)
  pix = np.sum(img==255)

  return [cX,cY,pix]

def img_circle(img,cX,cY):
   img = cv2.circle(img,(cX,cY),2,(0,255,0))
   return img
