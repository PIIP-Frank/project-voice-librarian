/*
 * Project Voice Librarian — firmware for Arduino Nano 33 BLE Sense Rev2 (ABX00070)
 *
 * Streams 16 kHz mono int16 PCM from the on-board PDM microphone over USB serial
 * on demand. The host (Python) drives capture by sending an ASCII command;
 * the board responds with a framed binary payload.
 *
 * Commands (ASCII, terminated by '\n'):
 *   R<seconds>     Record <seconds> of audio (1..30) and stream it back.
 *   PING           Identity probe — replies "PONG VoiceLibrarian".
 *
 * Wire format for an R reply:
 *   0xAA 0x55                    start marker (2 bytes)
 *   <len: uint32 little-endian>  payload byte count = seconds * 16000 * 2
 *   <int16 LE samples...>        raw PCM
 *   0x55 0xAA                    end marker (2 bytes)
 *
 * Errors are reported as "ERR <reason>\n" before any binary frame.
 *
 * Requires the "Arduino Mbed OS Nano Boards" core (provides PDM.h).
 */

#include <PDM.h>

static const uint16_t SAMPLE_RATE = 16000;
static const uint8_t  CHANNELS    = 1;
static const uint16_t PDM_GAIN    = 30;

// PDM ISR copies samples here. Sized for ~2 callbacks of headroom.
static const size_t   PDM_BUF_SHORTS = 1024;
static short          pdmBuffer[PDM_BUF_SHORTS];
static volatile int   pdmSamplesReady = 0;

void onPDMdata() {
  int bytes = PDM.available();
  if (bytes <= 0) return;
  if (bytes > (int)sizeof(pdmBuffer)) bytes = sizeof(pdmBuffer);
  PDM.read(pdmBuffer, bytes);
  pdmSamplesReady = bytes / 2;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { /* wait for USB CDC host */ }

  PDM.onReceive(onPDMdata);
  PDM.setGain(PDM_GAIN);
  if (!PDM.begin(CHANNELS, SAMPLE_RATE)) {
    Serial.println("ERR PDM_begin_failed");
    while (1) { delay(1000); }
  }

  Serial.println("READY");
}

void loop() {
  if (Serial.available() <= 0) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  if (line.charAt(0) == 'R') {
    long seconds = line.substring(1).toInt();
    if (seconds <= 0 || seconds > 30) {
      Serial.println("ERR bad_duration");
      return;
    }
    record((uint32_t)seconds);
  } else if (line == "PING") {
    Serial.println("PONG VoiceLibrarian");
  } else {
    Serial.println("ERR unknown_cmd");
  }
}

void record(uint32_t seconds) {
  uint32_t totalSamples = seconds * (uint32_t)SAMPLE_RATE;
  uint32_t totalBytes   = totalSamples * 2;

  // Discard any stale buffer so the first samples are fresh.
  pdmSamplesReady = 0;

  // Header
  Serial.write((uint8_t)0xAA);
  Serial.write((uint8_t)0x55);
  Serial.write((const uint8_t*)&totalBytes, 4);

  uint32_t sent = 0;
  while (sent < totalSamples) {
    if (pdmSamplesReady > 0) {
      int n = pdmSamplesReady;
      uint32_t remaining = totalSamples - sent;
      if ((uint32_t)n > remaining) n = (int)remaining;
      Serial.write((const uint8_t*)pdmBuffer, (size_t)n * 2);
      sent += n;
      pdmSamplesReady = 0;
    }
  }

  // Footer
  Serial.write((uint8_t)0x55);
  Serial.write((uint8_t)0xAA);
  Serial.flush();
}
