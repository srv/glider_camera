#!/usr/bin/env python
import yaml
from datetime import datetime
import time
import picamera
import os
import RPi.GPIO as GPIO
import Adafruit_MCP9808.MCP9808 as MCP9808

class GliderCamera:
  def __init__(self):
    """ Constructor of GliderCamera class """
    print "[GliderCamera]"
    self.mission_name = "test"
    self.start_date = datetime.now() # datetime.now() returns the current date and time
    self.end_date = self.start_date
    self.period = 10
    self.readConfig("config.yaml", "camera_config.yaml")
    self.startLed()
    self.startSensor()
    if self.mode == "master":
      self.captureMaster()
    elif self.mode == "slave":
      self.captureSlave()


  def __del__(self):
    """ Destructor of GliderCamera class """
    # All the output GPIOs must be turned off (all lights turned off) when stopping the execution (ctrl C)
    GPIO.output(self.led_output, 0) # this function sets to 0V (0) or 3,3V (1) the desired output GPIO pin
    GPIO.output(self.led_state_red, 0)
    GPIO.output(self.led_state_green, 0)

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
    """ Reads and sets the configuration for the LED output """
    GPIO.setmode(GPIO.BCM) # RPi has two modes of numbering GPIO pins
    GPIO.setwarnings(False)
    self.led_output = self.camera_config["led_pin_output"]
    self.signal_input = self.camera_config["signal_pin_input"]
    self.led_state_red = self.camera_config["state_red"]
    self.led_state_green = self.camera_config["state_green"]
    GPIO.setup(self.led_output, GPIO.OUT, initial=GPIO.LOW) #GPIO.LOw sets the initial value to 0 V
    GPIO.setup(self.signal_input, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(self.led_state_red, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(self.led_state_green, GPIO.OUT, initial=GPIO.LOW)
    self.led_time_on = self.camera_config["led_delay_on"]
    self.led_time_off = self.camera_config["led_delay_off"]
    self.time_green_led_out_of_time = self.camera_config["time_green_led_out_of_time"]
    self.time_green_led_waiting_slave = self.camera_config["time_green_led_waiting_slave"]
    self.time_red_led = self.camera_config["time_red_led"]
    self.num_flashes_green_led_out_of_time = self.camera_config["num_flashes_green_led_out_of_time"]
    self.num_flashes_green_led_waiting_slave = self.camera_config["num_flashes_green_led_waiting_slave"]
    self.num_flashes_red_led = self.camera_config["num_flashes_red_led"]
    self.time_between_flashes = self.camera_config["time_between_flashes"]
    self.time_of_each_flash = self.camera_config["time_of_each_flash"]

  def startSensor(self):
    """ Reads and sets the configuration for the temperature sensor """
    self.max_temp = self.camera_config["max_temp"]
    self.min_temp = self.camera_config["min_temp"]
    self.temp_sensor = MCP9808.MCP9808()
    self.temp_sensor.begin()

  def shutdown(self):
    """ Shutdowns the entire system """
    #TO DO: change shutdown to power off
    import subprocess
    subprocess.call(["sudo",  "shutdown",  "-k",  "+10",  '"RPi2 is going down to save battery. If you are planning to work, cancel it using < sudo shutdown -c > and remember to change the end date"'])

  def startCamera(self):
    """ Initializes the camera and its params """
    time.sleep(1)
    # Creates the directory where images will be saved
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
    self.memory_threshold = self.camera_config["memory_threshold"]

  def checkTime(self):
    """ Checks whether the current time fits in the mission timing window or not """
    time_now = datetime.now()
    if time_now < self.start_date:
      d = self.start_date - time_now
      print "Capture will start in " + repr(d.days) + " days..."
      # starts the green led flashing sets, which indicate that it is too soon to start the mission
      number_of_intervals = d.seconds/self.time_green_led_out_of_time
      remaining = d.seconds%self.time_green_led_out_of_time
      for i in range(0, number_of_intervals):
        self.state(0,0,self.led_state_green,self.time_green_led_out_of_time,self.num_flashes_green_led_out_of_time) # performing complete flashing set periods
      self.state(1,remaining,self.led_state_green,self.time_green_led_out_of_time,self.num_flashes_green_led_out_of_time) # performing the last flashing set which has 
      # a very high probability of not being complete (the remaining time to start the mission is less than the time between flashing sets)
    elif time_now > self.end_date:
      print "Capture time ended. Shutdown..."
      self.shutdown()
    return True

  def flash(self, led_pin, num_flashes_led):
    """ Performs num_flashes_led blinks at the led_pin pin """
    for i in range(0, num_flashes_led):
      if i > 0:
        time.sleep(self.time_between_flashes)
      GPIO.output(led_pin, 1)
      time.sleep(self.time_of_each_flash)
      GPIO.output(led_pin, 0)

  def state(self, finish_bool, time_to_finish, led_pin, time_waiting, num_flashes_green_led):
    """ Controls the complete flashing period of the green led when it is out of the timing window """
    ini_aux = datetime.now()
    self.flash(led_pin, num_flashes_green_led)
    fin_aux = datetime.now()
    diff = (fin_aux - ini_aux).total_seconds()
    if finish_bool == 0:
      if time_waiting - diff > 0:
        time.sleep(time_waiting - diff)
    elif finish_bool == 1:
      if time_to_finish - diff > 0:
        time.sleep(time_to_finish - diff)

  def checkMemory(self):
    """ Checks the current memory space left and compares it with the memory threshold """
    import subprocess
    p1 = subprocess.Popen(["sudo", "df"], stdout = subprocess.PIPE)
    p2 = subprocess.Popen(["grep", "rootfs"], stdin = p1.stdout, stdout = subprocess.PIPE)
    p3 = subprocess.Popen(["awk", "{print $4}"], stdin = p2.stdout, stdout = subprocess.PIPE)
    p1.stdout.close()
    p2.stdout.close()
    memory = p3.stdout.readline()
    available = int(memory) - self.memory_threshold
    if available > 0:
      return True 
    else:
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
      current_signal = GPIO.input(self.signal_input) #returns the value of an input GPIO
      if current_signal == previous_signal:
        # Wait
        if not slave_message_shown:
          print "Slave mode: Waiting for rising edge..."
          slave_message_shown = True
        ini_aux = datetime.now()
        self.flash(self.led_state_green, self.num_flashes_green_led_waiting_slave)
        #TO DO how much time can we sleep?
        fin_aux = datetime.now()
        remaining = self.time_green_led_waiting_slave - (fin_aux - ini_aux).total_seconds()
        if remaining > 0:
          time.sleep(remaining)
      elif previous_signal == True:
        # Reset the previous value to be ready for the next rising edge
        previous_signal = False
        slave_message_shown = False
      else:
        # Capture starts
        previous_signal = True
        self.startCamera()
        for i in range(0, self.photos_per_cycle):
          self.capture()
          if datetime.now() > self.end_date:
            break
        self.camera.close()

  def capture(self):
    """ Captures an image whilst lightning the LED """
    ini_aux = datetime.now()
    image_time = time.strftime("%Y%m%d-%H%M%S")
    GPIO.output(self.led_state_red, 0)
    temp = self.temp_sensor.readTempC()
    if temp < self.max_temp and temp > self.min_temp: #checks whether we are within the temperature range or not
      GPIO.output(self.led_output, 1)
      time.sleep(self.led_time_on)
      self.camera.capture(self.path + '/img-' + image_time + '.jpg')
      print("Saved img-" + image_time + ".jpg at " + str(temp) + "C")
    else:
      print image_time + ": Out of temperature boundaries"
    GPIO.output(self.led_output , 0)
    if not self.checkMemory():
      self.flash(self.led_state_red,self.num_flashes_red_led) # a red led flashing set for each attempt of capture indicates that we have surpassed the memory threshold
    fin_aux = datetime.now()
    capture_time = (fin_aux - ini_aux).total_seconds()
    time.sleep(self.led_time_off)
    remaining = self.period - self.led_time_on - self.led_time_off - capture_time
    if remaining > 0:
      time.sleep(remaining)

if __name__ == "__main__":
  try:
   GliderCamera()
  except KeyboardInterrupt:
    print(" Stopping camera...")
