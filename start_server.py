#!/usr/bin/env python3
"""
Network Configuration Evaluation Tool - Lab Launcher
=====================================================
Double-click this file to start the tool. No Command Prompt required.

Designed for school lab computers where cmd.exe may be restricted:
this launcher runs through python.exe, checks its own dependencies,
picks a free port, and opens the browser for you.

  python start_server.py            Ask, then start
  python start_server.py --local    This computer only
  python start_server.py --lan      Share with other lab computers
  python start_server.py --check    Run diagnostics and exit
  python start_server.py --port N   Use a specific port
"""
import argparse
import os
import socket
import sys
import webbrowser

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 8000
PORT_SEARCH_LIMIT = 20

# Package name on PyPI -> module name to import
REQUIRED = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "jinja2": "jinja2",
    "python-multipart": "multipart",
}


def banner(text):
    print("\n" + "=" * 62)
    print("  " + text)
    print("=" * 62)


def pause_if_double_clicked():
    """Keep the window open so the reader can see the message."""
    if sys.stdin and sys.stdin.isatty():
        try:
            input("\nPress Enter to close...")
        except (EOFError, KeyboardInterrupt):
            pass


def find_missing_packages():
    import importlib.util
    missing = []
    for pypi_name, module_name in REQUIRED.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(pypi_name)
    return missing


def install_packages(packages):
    """Install into the user site-packages, which does not need admin rights."""
    import subprocess
    wheels_dir = os.path.join(PROJECT_ROOT, "vendor", "wheels")
    cmd = [sys.executable, "-m", "pip", "install", "--user"]
    if os.path.isdir(wheels_dir) and os.listdir(wheels_dir):
        print("  Installing from bundled offline wheels (" + wheels_dir + ")")
        cmd += ["--no-index", "--find-links", wheels_dir]
    else:
        print("  Installing from the internet (pip)")
    cmd += packages
    print("  Running: " + " ".join(cmd) + "\n")
    return subprocess.call(cmd) == 0


def ensure_dependencies(auto_yes=False):
    missing = find_missing_packages()
    if not missing:
        return True
    banner("Missing required packages")
    for pkg in missing:
        print("    - " + pkg)
    print("\n  These install into your own user folder and do NOT need")
    print("  administrator rights.")
    if not auto_yes:
        if not (sys.stdin and sys.stdin.isatty()):
            print("\n  Cannot prompt. Re-run with --install to install them.")
            return False
        try:
            answer = input("\n  Install them now? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if answer not in ("", "y", "yes"):
            print("  Skipped. The tool cannot start without them.")
            return False
    if not install_packages(missing):
        print("\n  Installation failed.")
        print("  If this computer has no internet access, ask your instructor")
        print("  for the offline 'vendor/wheels' folder and place it in:")
        print("    " + os.path.join(PROJECT_ROOT, "vendor", "wheels"))
        return False
    still_missing = find_missing_packages()
    if still_missing:
        print("\n  Installed, but Python still cannot see: " + ", ".join(still_missing))
        print("  Close this window and run the launcher again.")
        return False
    print("\n  All packages installed.")
    return True


def _port_is_free(port, host="127.0.0.1"):
    """
    True only if nothing is serving on `port`.

    Deliberately does NOT set SO_REUSEADDR. On Windows that option allows a
    bind to a port another process is actively listening on, which would make
    this report an occupied port as free -- and the tool would then start
    somewhere the browser cannot reach it.
    """
    # A successful connection proves something is already listening.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connector:
        connector.settimeout(0.25)
        if connector.connect_ex((host, port)) == 0:
            return False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(preferred=DEFAULT_PORT, host="127.0.0.1"):
    """Return the first free port at or after `preferred`, or None."""
    for port in range(preferred, preferred + PORT_SEARCH_LIMIT):
        if _port_is_free(port, host):
            return port
    return None


def get_lan_ip():
    """Best-effort local network address. Sends no traffic."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.3)
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None


def check_packet_tracer_support():
    """The .pkt/.pka decoder is vendored; report whether it loads."""
    pka_dir = os.path.join(PROJECT_ROOT, "cisco-pka-to-xml")
    if not os.path.isdir(pka_dir):
        return False, "folder 'cisco-pka-to-xml' is missing"
    if pka_dir not in sys.path:
        sys.path.insert(0, pka_dir)
    try:
        import pka2xml  # noqa: F401
        return True, "ready"
    except Exception as exc:
        return False, str(exc)


def run_diagnostics(preferred_port=DEFAULT_PORT):
    banner("Lab Computer Diagnostics")
    ok = True

    print("\n  Python           : " + sys.version.split()[0] + "  (" + sys.executable + ")")
    if sys.version_info < (3, 10):
        print("    ^ TOO OLD. This tool needs Python 3.10 or newer.")
        ok = False

    print("  Project folder   : " + PROJECT_ROOT)

    missing = find_missing_packages()
    if missing:
        print("  Packages         : MISSING -> " + ", ".join(missing))
        ok = False
    else:
        print("  Packages         : all present")

    for folder in ("templates", "static", "src"):
        path = os.path.join(PROJECT_ROOT, folder)
        mark = "found" if os.path.isdir(path) else "MISSING"
        print("  " + folder.ljust(17) + ": " + mark)
        if mark == "MISSING":
            ok = False

    pkt_ok, pkt_detail = check_packet_tracer_support()
    print("  .pkt/.pka upload : " + ("ready" if pkt_ok else "UNAVAILABLE - " + pkt_detail))
    if not pkt_ok:
        print("    ^ Text bundle (.txt/.zip) upload still works.")

    port = find_free_port(preferred_port)
    print("  Free port        : " + (str(port) if port else "NONE in range"))
    if port is None:
        ok = False

    lan_ip = get_lan_ip()
    print("  This computer IP : " + (lan_ip or "could not detect"))

    print("\n" + ("  RESULT: ready to start." if ok else "  RESULT: fix the items marked above."))
    return ok


def main():
    parser = argparse.ArgumentParser(
        add_help=True,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--lan", action="store_true",
                        help="share with other computers on the lab network")
    parser.add_argument("--local", action="store_true",
                        help="this computer only; never ask")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help="preferred port (default %d)" % DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true",
                        help="do not open a browser window")
    parser.add_argument("--check", action="store_true",
                        help="run diagnostics and exit")
    parser.add_argument("--install", action="store_true",
                        help="install missing packages without asking")
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)

    if args.check:
        ok = run_diagnostics(args.port)
        pause_if_double_clicked()
        sys.exit(0 if ok else 1)

    banner("Network Configuration Evaluation & Topology Discovery Tool")

    if sys.version_info < (3, 10):
        print("\n  Python " + sys.version.split()[0] + " is too old. Version 3.10 or newer is required.")
        pause_if_double_clicked()
        sys.exit(1)

    if not ensure_dependencies(auto_yes=args.install):
        pause_if_double_clicked()
        sys.exit(1)

    if args.lan and args.local:
        print("\n  Use either --lan or --local, not both.")
        sys.exit(1)

    share_lan = args.lan
    if not share_lan and not args.local and sys.stdin and sys.stdin.isatty():
        print("\n  How should this run?")
        print("    [1] This computer only            (default)")
        print("    [2] Share with the lab network    (students open it in a browser)")
        try:
            choice = input("\n  Choice [1/2]: ").strip()
            share_lan = choice == "2"
        except (EOFError, KeyboardInterrupt):
            print("\n  Cancelled.")
            sys.exit(0)

    bind_host = "0.0.0.0" if share_lan else "127.0.0.1"
    port = find_free_port(args.port, host="127.0.0.1")
    if port is None:
        print("\n  No free port between %d and %d." % (args.port, args.port + PORT_SEARCH_LIMIT))
        print("  Close other running servers and try again.")
        pause_if_double_clicked()
        sys.exit(1)
    if port != args.port:
        print("\n  Port %d is in use. Using port %d instead." % (args.port, port))

    local_url = "http://127.0.0.1:%d/" % port

    pkt_ok, pkt_detail = check_packet_tracer_support()
    if not pkt_ok:
        print("\n  NOTE: .pkt/.pka upload is unavailable (" + pkt_detail + ").")
        print("        Text bundle (.txt/.zip) upload still works.")

    banner("Server starting")
    print("\n  On this computer : " + local_url)
    if share_lan:
        lan_ip = get_lan_ip()
        if lan_ip:
            print("  For the lab      : http://%s:%d/" % (lan_ip, port))
            print("\n  Students: type that second address into any browser.")
        else:
            print("  For the lab      : could not detect this computer's network address.")
        print("\n  If Windows asks to allow network access, choose ALLOW.")
        print("  That prompt needs an administrator ONCE, on this computer only.")
        print("  Student computers need nothing installed.")
    print("\n  Keep this window open while the tool is in use.")
    print("  Close this window, or press Ctrl+C, to stop the server.\n")

    if not args.no_browser:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    try:
        import uvicorn
        uvicorn.run("src.app:app", host=bind_host, port=port, log_level="warning")
    except KeyboardInterrupt:
        print("\n  Server stopped.")
    except Exception as exc:
        print("\n  The server stopped with an error:\n    " + str(exc))
        pause_if_double_clicked()
        sys.exit(1)


if __name__ == "__main__":
    main()
