// usb_console.h — commands typed to the sensor over its USB cable (115200), for
// development; athletes never need them, the setup page does their job.
//
//   claim K7MQ-2XPR   trade a code for this sensor's login (the setup page does this)
//   forget            throw the saved login away
//   setup             open the setup Wi-Fi now, same as holding the button
//   status            what the sensor is doing
//   watch             print the movement 5 times a second (again to stop), for tuning
#pragma once

#include <Arduino.h>

void runUsbConsole(uint32_t now);  // call every loop: reads typed lines, prints `watch`
