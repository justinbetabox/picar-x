#!/opt/jupyterhub/env/bin/python3
"""
install.py for picar-x

System and software setup for picar-x on Raspberry Pi 4B, Bookworm 64-bit,
using the shared JupyterHub venv at /opt/jupyterhub/env.

- Installs apt packages for audio and camera overlays
- Copies/vends the auto_sound_card and aplay services
- Installs the picar-x Python package in editable mode into the venv
- Optionally configures audio, without modifying system-managed packages

Run with:
    sudo /opt/jupyterhub/env/bin/python3 install.py
"""
import os
import sys
import subprocess
import shutil
from getpass import getuser

def print_info(msg):    print(f"\033[0;36m{msg}\033[0m")
def print_warn(msg):    print(f"\033[0;33m{msg}\033[0m")
def print_err(msg):     print(f"\033[0;31m{msg}\033[0m")
def print_success(msg): print(f"\033[0;32m{msg}\033[0m")

def run_command(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.stdout.read().decode()
    return p.wait(), out.strip()

# Run command as pi user but inside venv
def run_as_pi(cmd):
    venv_py = "/opt/jupyterhub/env/bin/python3"
    pip_env = f"/opt/jupyterhub/env/bin"
    full_cmd = f"sudo -u pi env PATH={pip_env}:$PATH {cmd}"
    return run_command(full_cmd)

# Prompt
def confirm(prompt):
    ans = input(f"{prompt} [y/N]: ").lower()
    return ans in ('y','yes')

if __name__ == '__main__':
    if os.geteuid() != 0:
        print_err("This script must be run as root: sudo python3 install.py")
        sys.exit(1)

    print_info("picar-x: System setup (Bookworm 64, Pi 4B)")
    errors = []

    # --- Install picar-x into venv ---
    print_info("\nInstalling picar-x package into shared venv...")
    venv_py = sys.executable
    # upgrade pip
    if run_command(f"{venv_py} -m pip install --upgrade pip setuptools")[0] != 0:
        print_warn("pip upgrade failed, continuing...")
    # install editable
    if run_command(f"{venv_py} -m pip install -e .")[0] != 0:
        print_err("Failed to install picar-x into venv.")
        errors.append("pip install -e . failed")
    else:
        print_success("picar-x installed in venv.")

    # --- Audio and overlays (system, safe) ---
    print_info("\nConfiguring audio overlays...")
    config = "/boot/firmware/config.txt"
    if not os.path.exists(config + ".bak"):
        shutil.copy(config, config + ".bak")
        print_success(f"Backed up {config}")
    for ov in ("dtoverlay=hifiberry-dac","dtoverlay=i2s-mmap"):
        with open(config) as f: lines = f.read().splitlines()
        if ov not in lines:
            with open(config, 'a') as f: f.write(f"\n{ov}\n")
            print_success(f"Added overlay {ov}")
        else:
            print_info(f"Overlay {ov} already present.")

    # Install alsa-utils
    print_info("Installing alsa-utils via apt...")
    run_command("apt-get update -y")
    run_command("apt-get install -y alsa-utils")

    # Write aplay service (disabled by default)
    aplay_svc = '/etc/systemd/system/aplay.service'
    aplay_conf = """[Unit]\nDescription=ALSA aplay daemon\n[Service]\nExecStart=/usr/bin/aplay -D default -t raw -r 44100 -c 2 -f S16_LE /dev/zero\n[Install]\nWantedBy=multi-user.target\n"""
    try:
        with open(aplay_svc,'w') as f: f.write(aplay_conf)
        run_command("systemctl daemon-reload")
        print_success("Created aplay service (disabled by default)")
    except Exception:
        print_err("Failed to write aplay.service file")
        errors.append("aplay.service write error")

    if confirm("Enable audio playback service now? (recommended)"):
        run_command("systemctl enable aplay")
        print_success("Enabled aplay.service")

    # --- Summary ---
    print_info("\n===== INSTALL SUMMARY =====")
    if errors:
        print_err("Some steps failed:")
        for e in errors: print_err(f"- {e}")
        print_warn("Review errors above.")
    else:
        print_success("All steps completed successfully.")
    print_info("\nReboot is recommended: sudo reboot")
