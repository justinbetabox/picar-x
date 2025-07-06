#!/usr/bin/env python3

import os
import sys
import subprocess
import shutil

def print_info(msg): print(f"\033[0;36m{msg}\033[0m")
def print_warn(msg): print(f"\033[0;33m{msg}\033[0m")
def print_err(msg): print(f"\033[0;31m{msg}\033[0m")
def print_success(msg): print(f"\033[0;32m{msg}\033[0m")

def run_command(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = p.stdout.read().decode()
    return p.wait(), output.strip()

def confirm(q):
    try:
        return input(f"{q} [y/N]: ").lower() in ("y", "yes")
    except EOFError:
        return False

def setup_audio_bookworm():
    config = "/boot/firmware/config.txt"
    overlays = ["dtoverlay=hifiberry-dac", "dtoverlay=i2s-mmap"]
    need_reboot = False

    # Backup once
    if not os.path.exists(config + ".bak"):
        shutil.copy(config, config + ".bak")
        print_info(f"Backed up {config} to {config}.bak")

    # Add overlays if missing
    with open(config, "r") as f:
        lines = f.read().splitlines()
    for overlay in overlays:
        if overlay not in lines:
            with open(config, "a") as f2:
                f2.write(f"\n{overlay}\n")
            print_success(f"Added {overlay} to {config}")
            need_reboot = True
        else:
            print_info(f"{overlay} already present.")

    # Install alsa-utils
    print_info("Installing alsa-utils...")
    run_command("apt-get install alsa-utils -y")

    # Write aplay systemd service
    aplay_service = """[Unit]
Description=Invoke aplay from /dev/zero at system start.

[Service]
ExecStart=/usr/bin/aplay -D default -t raw -r 44100 -c 2 -f S16_LE /dev/zero

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/aplay.service", "w") as f:
        f.write(aplay_service)
    run_command("systemctl daemon-reload")
    run_command("systemctl disable aplay")
    print_info("Created aplay systemd service (disabled by default).")
    if confirm("Activate '/dev/zero' playback in background? [RECOMMENDED]"):
        run_command("systemctl enable aplay")
        need_reboot = True
        print_success("Enabled aplay.service at boot.")

    # Write /usr/local/bin/auto_sound_card
    auto_sound_card_script = """#!/bin/bash

ASOUND_CONF=/etc/asound.conf
AUDIO_CARD_NAME="sndrpihifiberry"

card_num=$(sudo aplay -l |grep $AUDIO_CARD_NAME |awk '{print $2}'|tr -d ':')
echo "card_num=$card_num"
if [ -n "$card_num" ]; then
    cat > $ASOUND_CONF << EOF
pcm.speakerbonnet {
    type hw card $card_num
}

pcm.dmixer {
    type dmix
    ipc_key 1024
    ipc_perm 0666
    slave {
        pcm "speakerbonnet"
        period_time 0
        period_size 1024
        buffer_size 8192
        rate 44100
        channels 2
    }
}

ctl.dmixer {
    type hw card $card_num
}

pcm.softvol {
    type softvol
    slave.pcm "dmixer"
    control.name "PCM"
    control.card $card_num
}

ctl.softvol {
    type hw card $card_num
}

pcm.!default {
    type             plug
    slave.pcm       "softvol"
}
EOF
    echo "systemctl restart aplay.service"
    sudo systemctl restart aplay.service

    if [ -n $1 ] && [ $1 -gt 0 ]; then
        echo "set volume to $1"
        amixer -c $card_num sset PCM $1%
    fi

fi

exit 0
"""
    with open("/usr/local/bin/auto_sound_card", "w") as f:
        f.write(auto_sound_card_script)
    os.chmod("/usr/local/bin/auto_sound_card", 0o755)

    # Run auto_sound_card script once
    run_command("/usr/local/bin/auto_sound_card 100")

    # Write and enable auto_sound_card systemd service
    auto_sound_card_service = """[Unit]
Description=Auto config als sound card num at system start.
Wants=aplay.service

[Service]
ExecStart=/usr/local/bin/auto_sound_card

[Install]
WantedBy=multi-user.target
"""
    with open("/etc/systemd/system/auto_sound_card.service", "w") as f:
        f.write(auto_sound_card_service)
    run_command("systemctl daemon-reload")
    run_command("systemctl enable auto_sound_card")
    print_success("Configured auto_sound_card for boot.")

    # Prompt for speaker test
    if confirm("Do you wish to test your system now?"):
        print_info("Testing speakers...")
        run_command("speaker-test -l5 -c2 -t wav")
    print_success("I2S audio setup complete!")

    if need_reboot and confirm("A reboot is required to apply changes. Reboot now?"):
        run_command("sync")
        run_command("reboot")
        sys.exit(0)

def main():
    if os.geteuid() != 0:
        print_err("Script must be run as root! Try 'sudo python3 install.py'")
        sys.exit(1)

    print_info("Installing picar-x (Bookworm only)...")
    status, _ = run_command("pip3 help install | grep break-system-packages")
    pip_extra = "--break-system-packages" if status == 0 else ""
    status, output = run_command(f"python3 -m pip install . {pip_extra}")
    if status == 0:
        print_success("picar-x installed successfully!")
    else:
        print_err("pip install failed:")
        print_err(output)
        sys.exit(1)

    print_info("For full camera/I2C/SPI access, add your user to 'video', 'i2c', and 'spi' groups if needed.")

    # Audio setup
    if confirm("Configure I2S amplifier (audio) now?"):
        setup_audio_bookworm()

    print_success("All done! Please reboot your Pi before using picar-x with audio.")

if __name__ == "__main__":
    main()
