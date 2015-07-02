#!/usr/bin/env python
import yaml
from datetime import datetime
import time
import picamera
import os
import RPi.GPIO as GPIO

class GliderCamera:
  def __init__(self):
    print "[GliderCamera]"
    self.mission_name = "test"
    self.init_date = datetime.now()
    self.end_date = self.init_date
    self.freq = 10
    self.readConfig("config.yaml")
    self.readCameraConfig("camera_config.yaml")
    self.startLed()
    self.capture()

  def __del__(self):
    GPIO.output(self.led, 0)

  def readCameraConfig(self, filename):
    stream = open(filename, 'r')
    ys = yaml.load(stream)
    self.camera_config = ys

  def readConfig(self, filename):
    stream = open(filename, 'r')
    ys = yaml.load(stream)
    self.init_date = datetime.strptime(ys["init_date"], '%d/%m/%Y %H:%M')
    self.end_date = datetime.strptime(ys["end_date"], '%d/%m/%Y %H:%M')
    self.mission_name = ys["mission_name"]
    self.freq = ys["freq"];
    print "Mission configuration:"
    print "\t* Mission:   %s" % self.mission_name
    print "\t* Init date: %s" % self.init_date
    print "\t* End date:  %s" % self.end_date
    print "\t* Frequency: %s" % self.freq

  def startLed(self):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    self.led = self.camera_config["led_pin"]
    GPIO.setup(self.led, GPIO.OUT)
    self.led_time_on = self.camera_config["led_delay_on"]
    self.led_time_off = self.camera_config["led_delay_off"]
    GPIO.output(self.led, 0)

  def shutdown(self):
    #TODO: change shutdown to power off
    command = "/usr/bin/sudo /sbin/shutdown -k now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print output

  def capture(self):
    self.camera = picamera.PiCamera()
    width = self.camera_config["width"]
    height = self.camera_config["height"]
    self.camera.resolution = (width,height)
    self.camera.sharpness = self.camera_config["sharpness"]
    self.camera.brightness = self.camera_config["brightness"]
    #self.camera.contrast = self.camera_config["contrast"]
    self.camera.iso = self.camera_config["iso"]
    self.camera.exposure_mode = self.camera_config["exposure_mode"]
    self.camera.drc_strength = self.camera_config["drc"]
    #self.camera.shutter_speed = self.camera_config["shutter_speed"]
    '''self.camera.start_preview()'''
    time.sleep(1)
    path = os.getcwd() + "/" + self.mission_name
    if not os.path.exists(path):
      os.makedirs(path)
    if datetime.now() < self.init_date:
      d = self.init_date - datetime.now()
      print "Capture will start in " + repr(d.days) + " days..."
    while datetime.now() < self.init_date:
      time.sleep(10)
    while datetime.now() > self.init_date and datetime.now() < self.end_date:
      GPIO.output(self.led , 1)
      time.sleep(self.led_time_on)
      ini_aux = datetime.now()
      image_time = time.strftime("%Y%m%d-%H%M%S")
      self.camera.capture(path + '/img-' + image_time + '.jpg')
      print("Saved img-" + image_time + ".jpg")
      fin_aux = datetime.now()
      capture_time = (fin_aux - ini_aux).total_seconds()
      print (capture_time)
      time.sleep(self.led_time_off)
      GPIO.output(self.led , 0)
      remaining = self.freq - self.led_time_on - self.led_time_off - capture_time
      if remaining > 0:
        time.sleep(remaining)
    if datetime.now() > self.end_date:
      print "Capture time ended. Shutdown..."
      self.shutdown()

if __name__ == "__main__":
  try:
   GliderCamera()
  except KeyboardInterrupt:
    print(" Stopping camera...")