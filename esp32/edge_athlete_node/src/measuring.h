// measuring.h — the BNO085 on the bar, and deciding what counts as a rep.
//
// Why it's on its own: this is the part that will change most as it's tuned on a real
// bar (spec 14 Phase 6), and none of it needs to know about Wi-Fi or schools. When a
// rep ends it hands the numbers to messages.cpp to send.
#pragma once

#include <Arduino.h>

void startImu();             // without a BNO085 it says so and the rest carries on
void readImu(uint32_t now);  // call every loop: reads whatever the BNO085 has sent

bool repInProgress();        // the bar is moving in a rep right now
bool motionSensorFound();    // the BNO085 answered at start
float barSpeed();            // its speed so far in this rep, m/s (0 when not in one)
void printMovement();        // one line of the live numbers, for USB `watch`
