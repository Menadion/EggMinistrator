/*
  ============================================================================
  ✅ ALREADY RUN -- 2026-08-20, on COM3. You do not need to run this again
  unless the board is replaced.

      Chip type:          ESP32-D0WD-V3 (revision v3.1)
      Features:           Wi-Fi, BT, Dual Core + LP Core, 240MHz,
                          Vref calibration in eFuse, Coding Scheme None
      Crystal frequency:  40MHz
      MAC:                1c:69:20:a3:f8:8c

  VERDICT: a CLASSIC ESP32, not an S3. The main sketch's pin map was already
  written for this chip and is safe -- see EggMinistrator_ESP32S3.ino lines
  76 to 101. The warning below about the pin map being unsafe is HISTORICAL
  and was resolved on 2026-08-15.
  ============================================================================
*/

/*
  board-id -- what chip is this actually?

  WHY THIS EXISTS
    The module's can is marked "ESP32-32X", which is a reseller marking and
    not an Espressif part number, so it does not tell us which silicon is
    inside. The pin map in EggMinistrator_ESP32S3.ino was written for an
    ESP32-S3 and is unsafe on a classic ESP32: GPIO6-11 are wired to the
    integrated SPI flash there, and the sketch puts the LCD, the buzzer and
    one LED on 8, 9, 10 and 11.

    Rather than guess from the label, ask the chip.

  IT ALSO PROVES THE TOOLCHAIN
    If this uploads and prints, then the USB driver, the board selection and
    the serial port are all correct. Establish that before adding the load
    cell to the list of things that might be wrong.

  HOW TO RUN IT
    1. Arduino IDE -> Tools -> Board -> "ESP32 Dev Module"
    2. Tools -> Port -> whichever COM port appears when you plug the board in
       (if none appears, you need the CP2102 or CH340 USB driver)
    3. Upload, then Tools -> Serial Monitor at 115200 baud
    4. Press the RESET/EN button on the board if nothing prints

  WHAT TO DO WITH THE ANSWER
    Chip model contains ESP32-D0WD or plain ESP32  -> classic ESP32, use the
                                                      remapped pins
    Chip model says ESP32-S3                       -> the existing pin map is
                                                      already correct
    Chip model says ESP32-C3 or ESP32-S2           -> STOP, different GPIO map
                                                      again, ask before wiring

    PSRAM > 0 means GPIO16 and GPIO17 are in use and must stay free. The
    proposed remap avoids them either way, so this is confirmation, not a
    decision point.
*/

void setup() {
  Serial.begin(115200);
  delay(1500);            // give the USB serial link time to come up

  Serial.println();
  Serial.println("=== EggMinistrator board identification ===");

  Serial.print("Chip model      : ");
  Serial.println(ESP.getChipModel());

  Serial.print("Chip revision   : ");
  Serial.println(ESP.getChipRevision());

  Serial.print("CPU cores       : ");
  Serial.println(ESP.getChipCores());

  Serial.print("CPU freq (MHz)  : ");
  Serial.println(ESP.getCpuFreqMHz());

  Serial.print("Flash size (MB) : ");
  Serial.println(ESP.getFlashChipSize() / (1024.0 * 1024.0));

  Serial.print("PSRAM (bytes)   : ");
  Serial.println(ESP.getPsramSize());
  Serial.println(ESP.getPsramSize() > 0
    ? "  -> PSRAM present. GPIO16 and GPIO17 are taken, keep them free."
    : "  -> No PSRAM. GPIO16 and GPIO17 are usable, though the remap avoids them anyway.");

  Serial.print("Free heap       : ");
  Serial.println(ESP.getFreeHeap());

  Serial.println();
  Serial.println("Report the 'Chip model' line back before wiring anything.");
}

void loop() {
  delay(10000);
}
