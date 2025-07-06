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

def run_as_pi(cmd):
    return run_command(f"sudo -u pi {cmd}")

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
    try:
        with open("/etc/systemd/system/aplay.service", "w") as f:
            f.write(aplay_service)
        run_command("systemctl daemon-reload")
        run_command("systemctl disable aplay")  # Disabled by default
        print_info("Created aplay systemd service (disabled by default).")
    except PermissionError:
        print_err("Permission denied writing aplay.service file! Run as sudo.")

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
    try:
        with open("/usr/local/bin/auto_sound_card", "w") as f:
            f.write(auto_sound_card_script)
        os.chmod("/usr/local/bin/auto_sound_card", 0o755)
    except PermissionError:
        print_err("Permission denied writing auto_sound_card script! Run as sudo.")

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
    try:
        with open("/etc/systemd/system/auto_sound_card.service", "w") as f:
            f.write(auto_sound_card_service)
        run_command("systemctl daemon-reload")
        run_command("systemctl enable auto_sound_card")
        print_success("Configured auto_sound_card for boot.")
    except PermissionError:
        print_err("Permission denied writing auto_sound_card service file! Run as sudo.")

    # Prompt for speaker test
    if confirm("Do you wish to test your system now?"):
        print_info("Testing speakers...")
        run_command("speaker-test -l5 -c2 -t wav")

    print_success("I2S audio setup complete!")

    if need_reboot and confirm("A reboot is required to apply changes. Reboot now?"):
        run_command("sync")
        run_command("reboot")
        sys.exit(0)

def setup_jupyterlab():
    print("\n--- Installing JupyterLab ---")
    run_command("apt-get update -y")
    run_command("apt-get install -y python3-pip")

    # Install for pi user, not root (always with --break-system-packages for Bookworm)
    run_as_pi("python3 -m pip install --user --upgrade --break-system-packages pip")
    run_as_pi("python3 -m pip install --user --break-system-packages jupyterlab")

    # Find path to jupyter-lab for user pi
    jupyter_bin = "/home/pi/.local/bin/jupyter-lab"
    if not os.path.isfile(jupyter_bin):
        jupyter_bin = "/home/pi/.local/bin/jupyter"

    if not os.path.isfile(jupyter_bin):
        print_err("jupyter-lab not found in /home/pi/.local/bin after install!")
        print_err("Check the pip install output above for errors, or try re-installing JupyterLab manually:")
        print_err("    sudo -u pi python3 -m pip install --user --upgrade --break-system-packages jupyterlab")
        return

    # Write config for JupyterLab
    jupyter_config_dir = "/home/pi/.jupyter"
    run_as_pi(f"mkdir -p {jupyter_config_dir}")

    config_text = """
c.ServerApp.ip = '0.0.0.0'
c.ServerApp.open_browser = False
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.root_dir = '/home/pi'
"""
    # Write config as user pi to avoid permission issues
    tmp_config_path = "/tmp/jupyter_lab_config.py"
    with open(tmp_config_path, "w") as f:
        f.write(config_text)
    run_as_pi(f"cp {tmp_config_path} {jupyter_config_dir}/jupyter_lab_config.py")
    os.remove(tmp_config_path)

    # Write the systemd service file (owned by root, but runs as pi)
    service_text = f"""[Unit]
Description=JupyterLab Server

[Service]
Type=simple
PIDFile=/run/jupyter.pid
ExecStart={jupyter_bin} --no-browser --ip=0.0.0.0 --port=8888 --notebook-dir=/home/pi
User=pi
Group=pi
WorkingDirectory=/home/pi
Environment="PATH=/home/pi/.local/bin:/usr/bin:/bin"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
    service_path = "/etc/systemd/system/jupyterlab.service"
    try:
        with open(service_path, "w") as f:
            f.write(service_text)
        run_command("systemctl daemon-reload")
        run_command("systemctl enable jupyterlab")
        run_command("systemctl start jupyterlab")
        print_success("JupyterLab service installed and started.")
    except PermissionError:
        print_err("Permission denied writing jupyterlab service file! Run as sudo.")

def fix_pi_permissions():
    print_info("Fixing permissions for pi user on .local and .jupyter...")
    run_command("chown -R pi:pi /home/pi/.local /home/pi/.jupyter")

def do(msg="", cmd=""):
    print(f" - {msg} ... ", end='', flush=True)
    status, result = run_command(cmd)
    if status == 0 or status is None:
        print("Done")
    else:
        print("\033[1;35mError\033[0m")
        print(f"{msg} error:\nStatus: {status}\nError: {result}")

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

    if confirm("Install and configure JupyterLab accessible over network without password?"):
        setup_jupyterlab()

    if confirm("Configure I2S amplifier (audio) now?"):
        setup_audio_bookworm()

    fix_pi_permissions()
    print_success("All done! Please reboot your Pi before using picar-x with audio and JupyterLab.")

if __name__ == "__main__":
    main()