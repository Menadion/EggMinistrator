# hardware/

Physical build reference for the inspection station.

- `wiring-diagram.png` — ESP32-CAM, candling illumination (transillumination LEDs), load cell +
  HX711 amplifier, and the lit enclosure. (Committed — see the `!hardware/**/*.png` exception in
  `.gitignore`.)
- `bill-of-materials.md` — parts + costs. Remember the components that entered scope late:
  transillumination LEDs, light-sealing for the candling chamber, the load cell, and the HX711
  amplifier.

> The BOM here should match the hardware cost table in the capstone paper — keep them in sync.
