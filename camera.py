#!/usr/bin/env python
import yaml
from datetime import datetime
import time
import picamera
import os

class GliderCamera:
  def __init__(self):
    print "[GliderCamera]"
    self.mission_name = "test"
    self.init_date = datetime.now()
    self.end_date = self.init_date
    self.freq = 10
    self.readConfig("config.yaml")
    self.capture()

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

  def shutdown(self):
    #TODO: change shutdown to power off
    command = "/usr/bin/sudo /sbin/shutdown -k now"
    import subprocess
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output = process.communicate()[0]
    print output

  def capture(self):
    self.camera = picamera.PiCamera()
    '''self.camera.start_preview()'''
    time.sleep(1)
    path = os.getcwd() + "/" + self.mission_name
    if not os.path.exists(path):
      os.makedirs(path)
    if datetime.now() < self.init_date:
      d = self.init_date - t
      print "Capture will start in " + repr(d.days) + " days..."
    while datetime.now() < self.init_date:
      time.sleep(10)
    while datetime.now() > self.init_date and datetime.now() < self.end_date:
      image_time = time.strftime("%Y%m%d-%H%M%S")
      self.camera.capture(path + '/img-' + image_time + '.jpg')
      print("Saved img-" + image_time + ".jpg")
      time.sleep(self.freq)
    if datetime.now() > self.end_date:
      print "Capture time ended. Shutdown..."
      self.shutdown()

if __name__ == "__main__":
  try:
    GliderCamera()
  except KeyboardInterrupt:
    print(" Stopping camera...")

