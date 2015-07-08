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
    self.start_date = datetime.now()
    self.end_date = self.start_date
    self.period = 10
    self.readConfig("config.yaml")
    self.readCameraConfig("camera_config.yaml")
    self.startLed()
    if self.mode == "master":
      self.captureMaster()
    elif self.mode == "slave":
      self.captureSlave()

  def __del__(self):
    GPIO.output(self.led_output, 0)

  def readCameraConfig(self, filename):
    stream = open(filename, 'r')
    ys = yaml.load(stream)
    self.camera_config = ys

  def readConfig(self, filename):
    stream = open(filename, 'r')
    ys = yaml.load(stream)
    self.start_date = datetime.strptime(ys["start_date"], '%d/%m/%Y %H:%M')
    self.end_date = datetime.strptime(ys["end_date"], '%d/%m/%Y %H:%M')
    self.mission_name = ys["mission_name"]
    self.mode = ys["mode"]
    self.photos_per_cycle = ys["photos_per_cycle"]
    self.period = ys["period"];
    print "Mission configuration:"
    print "\t* Mission:          %s" % self.mission_name
    print "\t* Mode:             %s" % self.mode
    if self.mode == "slave":
      print "\t* Photos per cycle: %s" % self.photos_per_cycle
    print "\t* Init date:        %s" % self.start_date
    print "\t* End date:         %s" % self.end_date
    print "\t* Period:           %s" % self.period

  def startLed(self):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    self.led_output = self.camera_config["led_pin_output"]
    self.signal_input = self.camera_config["signal_pin_input"]
    GPIO.setup(self.led_output, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(self.signal_input, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    self.led_time_on = self.camera_config["led_delay_on"]
    self.led_time_off = self.camera_config["led_delay_off"]
    # GPIO.output(self.led_output, 0)

  def shutdown(self):
    #TODO: change shutdown to power off
    import subprocess
    subprocess.call(["sudo",  "shutdown",  "-k",  "+10",  '"RPi2 is going down to save battery. If you are planning to work, cancel it using < sudo shutdown -c > and remember to change the end date"'])

  def startCamera(self):
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

  def captureMaster(self):
    self.startCamera()
    time.sleep(1)
    path = os.getcwd() + "/" + self.mission_name
    if not os.path.exists(path):
      os.makedirs(path)
    if datetime.now() < self.start_date:
      d = self.start_date - datetime.now()
      print "Capture will start in " + repr(d.days) + " days..."
    while datetime.now() < self.start_date:
      time.sleep(10)
    while datetime.now() > self.start_date and datetime.now() < self.end_date:
      self.capture(path)
    if datetime.now() > self.end_date:
      print "Capture time ended. Shutdown..."
      self.shutdown()

  def captureSlave(self):
    # We suppose all photo cycles won't overlap
    last = False
    while datetime.now() < self.end_date:
      signal_received = GPIO.input(self.signal_input)
      if signal_received == last:
        time.sleep(5)
      elif last == True:
        last = False
      else:
        last = True
        time.sleep(1)
        path = os.getcwd() + "/" + self.mission_name
        if not os.path.exists(path):
          os.makedirs(path)
        if datetime.now() < self.start_date:
          d = self.start_date - datetime.now()
          print "Capture will start in " + repr(d.days) + " days..."
        else:
          self.startCamera()
          for i in range(0, self.photos_per_cycle):
            self.capture(path)
            if datetime.now() > self.end_date:
              break
          self.camera.close()
    print "Capture time ended. Shutdown..."
    self.shutdown()


  def capture(self, path):
    GPIO.output(self.led_output, 1)
    time.sleep(self.led_time_on)
    ini_aux = datetime.now()
    image_time = time.strftime("%Y%m%d-%H%M%S")
    self.camera.capture(path + '/img-' + image_time + '.jpg')
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
