# PiCar-X

A modern Python library for controlling the PiCar-X robotic car on Raspberry Pi OS Bookworm.

---

## Features

- Easy Python APIs for driving, steering, and sensors
- Designed for SunFounder/Betabox PiCar-X hardware
- Full support for Bookworm (64-bit) on Raspberry Pi 4B/5
- Optional: automated I2S amplifier (audio) setup during installation

---

## Requirements

- **Hardware:** Raspberry Pi 4B or 5, PiCar-X kit
- **OS:** Raspberry Pi OS Bookworm (64-bit)
- **Python:** 3.7 or newer

---

## Installation

**1. Clone this repository:**
```sh
git clone https://github.com/justinbetabox/picar-x.git
cd picar-x
```

**2. Run the installer:**
```sh
sudo python3 install.py
```
- Installs all required Python dependencies from `pyproject.toml`
- Optionally configures I2S audio amp support
- Backs up and edits `/boot/firmware/config.txt` as needed

**3. Reboot your Pi:**
```sh
sudo reboot
```

---

## Quick Test

After reboot, try this in Python:

```python
from picarx import Picarx

car = Picarx()
car.forward(30)
car.stop()
```

---

## I2S Audio Setup

During installation, you'll be prompted to configure I2S amplifier support:
- Edits `/boot/firmware/config.txt`
- Installs `alsa-utils`
- Adds required systemd services
- Optionally tests your speakers

You can always re-run the install script to re-configure audio.

---

## Troubleshooting

- **Not working?** Double-check you are running Raspberry Pi OS Bookworm (64-bit, Desktop image).
- For hardware access, your user may need to be in the `video`, `i2c`, and `spi` groups.
- Check `/boot/firmware/config.txt` for overlay lines after audio setup.

---

## Issues & Contributions

- [Open an Issue](https://github.com/justinbetabox/picar-x/issues) for bugs or questions
- PRs welcome!

---

## License

GNU GPLv3 (see [LICENSE](LICENSE))
