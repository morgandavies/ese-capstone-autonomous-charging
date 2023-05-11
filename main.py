# This is where we control the overall behavior of the guy

import RPi.GPIO as GPIO
import sys
import time
import picamera
import cv2
import numpy as np

import step_func
import mod7_func as linear_actuator
import camf
import img_proc_func

# Constants ----------------------------------
debug = True
stepper_pins = [13,11,15,12]
PAUSE = 0.008

in1 = 33
in2 = 35
en  = 37

min_hsv_target = (110, 60, 60)     # Currently set to outdoor partially cloudy purple
max_hsv_target = (170, 255, 255)
min_hsv_charge = (50, 204, 179)     # Currently set to outdoor partially cloudy purple
max_hsv_charge = (65, 255, 255)
CAM_WIDTH = 640
CAM_HEIGHT = 480

marker_pos_ideal = CAM_WIDTH/2
pix_steps_ratio = 1.9           # Estimated proportional conversion from pixel distance between marker actual and desired position
moves_history = []

sweep_direction = 1
sweep_count = -555
sweep_dist = 30

charge_history = []
time_check = time.time()

# Initializations ----------------------------
now = time.time()

GPIO.setmode(GPIO.BOARD)
step_func.stepper_init(*stepper_pins)
linear_actuator.motor_init(in1, in2, en, 1000, 90)

# Boolean control variables
# May delete some if we don't get around to implementing their functionality
Idle = False
Alignment = False
Plug_in = False
Charge = True
Unplug = False
Reset = False
# Live camera feed init
#feed = cv2.VideoCapture(0)
#feed.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_WIDTH)
#feed.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_HEIGHT)

# Functionality -----------------------------
# Continuously capture images from the camera and show circled marker center
# My break statements may or may not break all the way out of this while true loop. Crtl+C should still cause the program to exit, so like, oh well
try:
   while True:
      with picamera.PiCamera() as cam:

         stream = camf.cam_init(cam, CAM_WIDTH,CAM_HEIGHT)

         while Idle or Alignment:
   #         success, img = feed.read()
            success = cam != None
            if not success:
               sys.exit('ERROR: Unable to read from camera.')
            img = camf.cam_cap(cam, stream)
            img = cv2.flip(img,-1)

            # Find center of target color
            mask = img_proc_func.create_mask(img, min_hsv_target, max_hsv_target, debug)
            center = img_proc_func.find_com(mask, img, debug)
            if center:
               # Exit Idle state and enter Alignment state!
               Idle = False
               Alignment = True
               # Find the error of the marker position from the desired marker position in the field of view
               cX = center[0]
               e = marker_pos_ideal - cX     # If negative, Pi moves to the right from cam's pov; if positive, Pi moves to the left from cam's pov
               if debug:
                  print(f'Found error of {e} pixels')
               move = int(pix_steps_ratio * e)
               if np.absolute(move) < 10:    # Make sure the calculated adjustment is large enough for the stepper motor to realize
                  move = np.sign(move)*10
               if debug:
                  print(f'Moving to align with marker by {move} steps')
               moves_history.append(move)
               if len(moves_history) >= 2:
                  if np.absolute(moves_history[-1])<=10 and np.absolute(moves_history[-2])<=10:     # Changed condition for determining alignment
                     Alignment = False
                     Plug_in = True
                     moves_history = []
                     if debug:
                        print('Centered on charging port. Plugging in')
                     break
               # Motor moves, temporarily suspending camera feedback so we don't overshoot
               # TODO: Implement tighter/better edge control
               # Assume track is 2400 steps wide (should be conservative)
               # Travel 1200 steps each direction, then switch directions
               sweep_count += move
               if np.absolute(sweep_count) >= 600:
                  move = move - sweep_direction * (sweep_count - 1200)
                  sweep_count = sweep_direction * 600
                  sweep_direction = sweep_direction * (-1)
               step_func.stepper_move(*stepper_pins,move,PAUSE)

         # If no center is found, we continue sweeping by moving a small amount and taking photos intermittently
            else:
               Alignment = False
               Idle = True
               if np.absolute(sweep_count) >= 600:
                  sweep_direction = sweep_direction * (-1)
               step_func.stepper_move(*stepper_pins, sweep_direction * sweep_dist, PAUSE)
               sweep_count += sweep_direction * sweep_dist
            if debug:
               print(f'Placement along sweep: {sweep_count}')
               print(f'            Direction: {sweep_direction}')
         # Display feed
        # cv2.imshow('Marker Detection',img)

         while Plug_in:
            if debug:
               print('State: Plug_in')
            linear_actuator.motor_direction(in1, in2, 1)
            time.sleep(0.1)
            Plug_in = False
            Charge = True
            now = time.time()
            time_check = now + 60

         while Charge:
#            if debug:
#               print('State: Charging...')
         #time.sleep(10)
         
         # TODO
         # check what time it is
            now = time.time()
#            if debug:
#               print(f'Now is {now}, next capture is at {time_check}')
         # if it's time to take a photo...
            if now >= time_check:
            # Take a photo
               img = camf.cam_cap(cam, stream)
               img = cv2.flip(img,-1)
               if debug:
                  print("Took a photo")
               # Look for green and calulate the ratio of bright grreen pixels within the whole image
               img = img_proc_func.create_mask(img, min_hsv_charge, max_hsv_charge, debug)
               green = img_proc_func.mask_ratio(img, debug)
               # Update charge status history appropriately and count instances of green light
               if debug:
                  print(f'{green} of photo matches light color')
               if green > 0.0008:
                  charge_history.append(True)
                  if debug:
                     print("Found light on")
               else:
                  charge_history.append(False)
                  if debug:
                     print("Did not find light on")
               if len(charge_history) > 10:
                  charge_history.pop(0)
               hits = 0
               for status in charge_history:
                  if status:
                     hits += 1
               # Choose the appropriate time to next check for a full charge
               if hits > 0:
                  time_check += 0.03       # At near full charge, battery flashes every 1.25s
                                           # Interval of 0.36 will ensure that camera capture and flashes will not sync up
                                           # System will take 1.8s to detect full charge
               else:
                  time_check += 60
               # Check for constant green light output
               if len(charge_history) > 5 and hits == len(charge_history):
                  # clear results array and change states
                  charge_history = []
                  time_check = now
                  Charge = False
                  Unplug = True

         while Unplug:
            if debug:
               print('State: Unplug')
            linear_actuator.motor_direction(in1, in2, -1)
            time.sleep(1)
            Unplug = False
            Reset = True
            
         while Reset:
         # Wait for user input to reset to Idle state
         # This gives time for someone to manually move the model train car (and marker) out of the way...
         # ...and, unless we clean up the navigation of lateral movement, to slide the model station back to the designated end of its track
            print('State: Reset')
            linear_actuator.motor_direction(in1, in2, -1)      # I still haven't actually written code for the linear actuator yet so I'm just using the default -1 for now
            time.sleep(0.5)
            reset_move = int(input('Steps for manual reset: '))
            step_func.stepper_move(*stepper_pins,(-1)*reset_move,PAUSE)

            sweep_count = -555
            sweep_direction = 1     # Assume the charging station position is reset perfectly

            Reset = False
            Idle = True


# Closing sequence ---------------------------
except KeyboardInterrupt:
   print('Closing program...')
finally:
#   feed.release()
   cv2.destroyAllWindows()
   cam.close()
   linear_actuator.motor_direction(in1,in2,-1)
   time.sleep(2)
   GPIO.cleanup()
