#!/usr/bin/env python
import yaml
from datetime import datetime
import time
import picamera
import os
import RPi.GPIO as GPIO

class GliderCamera:
  def __init__(self):
    """ Constructor of GliderCamera class """
    print "[GliderCamera]"
    self.mission_name = "test"
    self.start_date = datetime.now()
    self.end_date = self.start_date
    self.period = 10
    self.readConfig("config.yaml", "camera_config.yaml")
    self.startLed()
    if self.mode == "master":
      self.captureMaster()
    elif self.mode == "slave":
      self.captureSlave()

  def __del__(self):
    """ Destructor of GliderCamera class """
    GPIO.output(self.led_output, 0)

  def readCameraConfig(self, filename):
    """ Reads the specified yaml configuration file """
    stream = open(filename, 'r')
    ys = yaml.load(stream)
    self.camera_config = ys

  def readConfig(self, config_filename, camera_config_filename):
    """ Reads both configurations and loads their parameters to the class """
    stream = open(config_filename, 'r')
    ys = yaml.load(stream)
    self.start_date = datetime.strptime(ys["start_date"], '%d/%m/%Y %H:%M')
    self.end_date = datetime.strptime(ys["end_date"], '%d/%m/%Y %H:%M')
    self.mission_name = ys["mission_name"]
    self.mode = ys["mode"]
    self.photos_per_cycle = ys["photos_per_cycle"]
    self.period = ys["period"];
    self.readCameraConfig(camera_config_filename)
    print "Mission configuration:"
    print "\t* Mission:          %s" % self.mission_name
    print "\t* Mode:             %s" % self.mode
    if self.mode == "slave":
      print "\t* Photos per cycle: %s" % self.photos_per_cycle
    print "\t* Init date:        %s" % self.start_date
    print "\t* End date:         %s" % self.end_date
    print "\t* Period:           %s" % self.period

  def startLed(self):
    """ Sets the configuration for the LED output """
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    self.led_output = self.camera_config["led_pin_output"]
    self.signal_input = self.camera_config["signal_pin_input"]
    GPIO.setup(self.led_output, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(self.signal_input, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    self.led_time_on = self.camera_config["led_delay_on"]
    self.led_time_off = self.camera_config["led_delay_off"]

  def shutdown(self):
    """ Shutdowns the entire system """
    #TODO: change shutdown to power off
    import subprocess
    subprocess.call(["sudo",  "shutdown",  "-k",  "+10",  '"RPi2 is going down to save battery. If you are planning to work, cancel it using < sudo shutdown -c > and remember to change the end date"'])

  def startCamera(self):
    """ Initializes the camera and its params """
    time.sleep(1)
    self.path = os.getcwd() + "/" + self.mission_name
    if not os.path.exists(self.path):
      os.makedirs(self.path)
    self.camera = picamera.PiCamera()
    width = self.camera_config["width"]
    height = self.camera_config["height"]
    self.camera.resolution = (width,height)
    self.camera.sharpness = self.camera_config["sharpness"]
    self.camera.brightness = self.camera_config["brightness"]
    self.camera.iso = self.camera_config["iso"]
    self.camera.exposure_mode = self.camera_config["exposure_mode"]
    self.camera.drc_strength = self.camera_config["drc"]

  def checkTime(self):
    time_now = datetime.now()
    if (time_now > self.start_date and time_now < self.end_date):
      return True
    elif time_now < self.start_date:
      d = self.start_date - time_now
      print "Capture will start in " + repr(d.days) + " days..."
      time.sleep(d.seconds)
    elif time_now > self.end_date:
      print "Capture time ended. Shutdown..."
      self.shutdown()
    time.sleep(10)
    return False

  def captureMaster(self):
    """ Automatic capture mode """
    self.startCamera()
    while self.checkTime():
      self.capture()

  def captureSlave(self):
    """ Slave capture mode. Capture cycles do NOT overlap """
    previous_signal = False
    slave_message_shown = False
    while self.checkTime():
      current_signal = GPIO.input(self.signal_input)
      if current_signal == previous_signal:
        # Wait
        if not slave_message_shown:
          print "Slave mode: Waiting for rising edge..."
          slave_message_shown = True
        #TODO how much time can we sleep?
        time.sleep(5)
      elif previous_signal == True:
        # Reset the previous value to be ready for the next rising edge
        previous_signal = False
      else:
        # Capture starts
        previous_signal = True
        self.startCamera()
        for i in range(0, self.photos_per_cycle):
          #TODO if time_now > end_date we are still taking pictures. Ask Marc.
          self.capture()
        self.camera.close()

  def capture(self):
    """ Captures an image whilst lightning the LED """
    GPIO.output(self.led_output, 1)
    time.sleep(self.led_time_on)
    ini_aux = datetime.now()
    image_time = time.strftime("%Y%m%d-%H%M%S")
    self.camera.capture(self.path + '/img-' + image_time + '.jpg')
    print("Saved img-" + image_time + ".jpg")
    fin_aux = datetime.now()
    capture_time = (fin_aux - ini_aux).total_seconds()
    time.sleep(self.led_time_off)
    GPIO.output(self.led_output , 0)
    remaining = self.period - self.led_time_on - self.led_time_off - capture_time
    if remaining > 0:
      time.sleep(remaining)

if __name__ == "__main__":
  try:
   GliderCamera()
  except KeyboardInterrupt:
    print(" Stopping camera...")
