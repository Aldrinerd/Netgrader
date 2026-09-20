# scripts/pt_collector.py
"""
Cisco Packet Tracer Automated CLI Collector
============================================
Automates typing Cisco show commands into Packet Tracer device CLI tabs
either command-by-command (foolproof step mode) or all-at-once, captures
copied sections from the clipboard, merges output, extracts hostnames,
and creates 1-click ZIP archives for the Topology Discovery web app.
"""
import os
import re
import sys
import time

try:
    import pyautogui
    import pyperclip
except ImportError:
    print("\n[!] Missing required libraries. Please run: pip install pyautogui pyperclip\n")
    sys.exit(1)

# Ensure project root is in sys.path when script is executed directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.pt_collector_core import (
        COMMAND_SETS,
        create_topology_zip,
        extract_device_name,
    )
except ImportError:
    from pt_collector_core import (
        COMMAND_SETS,
        create_topology_zip,
        extract_device_name,
    )

CAPTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "captures")
pyautogui.FAILSAFE = True

def print_banner():
    print("\n" + "=" * 66)
    print("   CISCO PACKET TRACER AUTOMATED TOPOLOGY COLLECTOR")
    print("=" * 66)
    os.makedirs(CAPTURES_DIR, exist_ok=True)
    existing = [f for f in os.listdir(CAPTURES_DIR) if f.endswith(".txt")]
    print(f" Captured Devices: {len(existing)} in {CAPTURES_DIR}")
    if existing:
        print("   -> " + ", ".join(existing))
    print("=" * 66)

def countdown(seconds: int = 4, prompt_text: str = "Focus Packet Tracer CLI window"):
    print(f"\n[!] {prompt_text}:")
    for i in range(seconds, 0, -1):
        print(f"    Starting in {i}...", flush=True)
        time.sleep(1)
    print("    >>> TYPING COMMAND... (Do not touch keyboard/mouse) <<<\n")

def execute_single_command(cmd: str):
    """Types a single command, clears pagination only if needed, and scrolls to top."""
    pyautogui.press("enter")
    time.sleep(0.15)
    print(f"  [+] Typing: {cmd}")
    pyautogui.write(cmd, interval=0.008)
    pyautogui.press("enter")
    time.sleep(0.25)

    # Only pulse spacebar for commands that can actually page
    if "include hostname" in cmd:
        # Single line output - zero spaces needed!
        pass
    elif "include" in cmd or "brief" in cmd:
        # Short outputs - only 2-3 spaces if needed
        for _ in range(3):
            pyautogui.press("space")
            time.sleep(0.03)
    else:
        # Standard show commands (cdp, mac, route) - pulse 15 spaces
        for _ in range(15):
            pyautogui.press("space")
            time.sleep(0.03)

    time.sleep(0.15)
    pyautogui.press("enter")

    # Scroll mouse wheel up to reveal the top of the command output
    try:
        pyautogui.scroll(2500)
    except Exception:
        pass


def wait_for_clipboard(timeout_seconds: int = 45) -> str:
    """Waits for user to copy text into the clipboard and returns it."""
    # Clear clipboard first so we only detect NEW copies
    try:
        pyperclip.copy("")
    except Exception:
        pass

    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        try:
            clip = pyperclip.paste()
            if clip and len(clip.strip()) > 5:
                return clip
        except Exception:
            pass
        time.sleep(0.4)
    return ""

def save_captured_text(text: str):
    dev_name = extract_device_name(text)
    user_name = input(f"\nDevice hostname detected as '{dev_name}'. Press Enter to keep, or type custom name: ").strip()
    if user_name:
        dev_name = user_name

    out_file = os.path.join(CAPTURES_DIR, f"{dev_name}.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(text)

    line_count = len(text.splitlines())
    print(f"\n[✓] SUCCESS: Saved {line_count} lines to {out_file}")

def capture_step_by_step(role: str):
    """Command-by-command collection: types 1 command at a time, waits for copy, and merges."""
    commands = COMMAND_SETS.get(role)
    if not commands:
        print(f"Unknown role: {role}")
        return

    print(f"\n[*] Starting Step-by-Step Capture for {role.upper()} ({len(commands)} commands)")
    print("    In this mode, the tool types ONE command at a time.")
    print("    Click 'Copy' in Packet Tracer after each command to immediately advance.")
    print("-" * 66)

    # Initial countdown to focus the Packet Tracer window
    countdown(3, "Click inside Packet Tracer CLI window now")

    captured_chunks = []
    
    for idx, cmd in enumerate(commands, 1):
        while True:
            print(f"\n>> [{idx}/{len(commands)}] Command: {cmd}")
            execute_single_command(cmd)

            print(f"[✓] Typed '{cmd}' -> Highlight & click 'Copy' in Packet Tracer...")


            chunk = wait_for_clipboard(timeout_seconds=45)
            if chunk:
                # Validation check for show running-config
                if "running-config" in cmd.lower() and not re.search(r"hostname\s+", chunk, re.IGNORECASE):
                    print("\n[!] WARNING: 'hostname' directive was NOT found in the copied text!")
                    print("    The top of 'show running-config' might have been missed.")
                    recopy = input("    Scroll to the very top in Packet Tracer and re-copy? [Y/n]: ").strip().lower()
                    if recopy != "n":
                        print("    Waiting for new copy from the top of the window...")
                        new_chunk = wait_for_clipboard(timeout_seconds=30)
                        if new_chunk:
                            chunk = new_chunk

                # Ensure command header is present
                if cmd.lower() not in chunk.lower():
                    chunk = f"{cmd}\n" + chunk
                captured_chunks.append(chunk.strip())
                print(f"\n  [✓] Captured '{cmd}' ({len(chunk.splitlines())} lines)!")
                break
            else:
                print("\n[!] No copy detected within timeout.")
                retry = input("  [R] Retry this command, [S] Skip this command, [Q] Abort? [R/s/q]: ").strip().lower()
                if retry == "s":
                    print(f"  [-] Skipped '{cmd}'.")
                    break
                elif retry == "q":
                    print("  [-] Aborted.")
                    return

    if not captured_chunks:
        print("\n[-] No output was captured.")
        return

    full_output = "\n\n".join(captured_chunks)
    print("\n" + "=" * 66)
    print(f"[✓] ALL {len(captured_chunks)} COMMANDS CAPTURED SUCCESSFULLY!")
    print("=" * 66)
    save_captured_text(full_output)

def quick_paste_from_clipboard():
    """Immediately reads whatever is currently in the clipboard and saves it as a device."""
    try:
        clip = pyperclip.paste()
    except Exception as e:
        print(f"Error accessing clipboard: {e}")
        return

    if not clip or len(clip.strip()) < 10:
        print("\n[!] Clipboard is currently empty or contains insufficient text.")
        print("    In Packet Tracer, highlight the terminal text and click 'Copy' first.")
        return

    print(f"\n[✓] Found {len(clip.splitlines())} lines in clipboard!")
    save_captured_text(clip)

def bundle_zip():
    out_zip = os.path.join(CAPTURES_DIR, "topology_bundle.zip")
    count = create_topology_zip(CAPTURES_DIR, out_zip)
    if count == 0:
        print("\n[-] No .txt capture files found in captures/ to bundle.")
    else:
        print(f"\n[✓] BUNDLE CREATED: {out_zip} ({count} devices included)")
        print("    You can now upload this ZIP directly to http://127.0.0.1:8000/")

def clear_captures():
    confirm = input("\n[?] Are you sure you want to delete all files in captures/? (y/N): ").strip().lower()
    if confirm == "y":
        for f in os.listdir(CAPTURES_DIR):
            if f.endswith(".txt") or f.endswith(".zip"):
                try:
                    os.remove(os.path.join(CAPTURES_DIR, f))
                except Exception as e:
                    print(f"Error removing {f}: {e}")
        print("[✓] Captures folder cleared.")

def main():
    while True:
        print_banner()
        print("\nSelect an action (Step-by-Step Command Capture):")
        print("  [1] Capture Router (show run -> cdp -> ip int br -> ip route)")
        print("  [2] Capture Switch (show run -> cdp -> ip int br -> vlan br -> int trunk -> mac)")
        print("  [3] Capture Multi-Layer Switch (MLS full combined suite)")
        print("  --------------------------------------------------")
        print("  [P] Quick Save from Clipboard (save text currently in clipboard)")
        print("  [Z] Build ZIP Bundle (captures/topology_bundle.zip)")
        print("  [C] Clear Captured Files")
        print("  [Q] Exit")

        choice = input("\nEnter choice [1-3, P, Z, C, Q]: ").strip().lower()
        if choice == "1":
            capture_step_by_step("router")
        elif choice == "2":
            capture_step_by_step("switch")
        elif choice == "3":
            capture_step_by_step("mls")
        elif choice == "p":
            quick_paste_from_clipboard()
        elif choice == "z":
            bundle_zip()
        elif choice == "c":
            clear_captures()
        elif choice == "q":
            print("\nExiting. Happy analyzing!\n")
            sys.exit(0)
        else:
            print("Invalid selection.")

if __name__ == "__main__":
    main()
