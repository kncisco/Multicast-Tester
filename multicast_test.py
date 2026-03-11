#!/usr/bin/env python3
"""
multicast_test.py — Multicast traffic tester for routed networks.
Portable across Linux, macOS, and Windows (Python 3.8+, stdlib only).

Usage
-----
  Source:
    python3 multicast_test.py source   -g 239.1.1.1 -p 5000 -i eth0
                                       [--ttl 16] [--interval 1.0] [--message "hello"]
  Receiver:
    python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0
"""

import argparse
import ipaddress
import json
import platform
import signal
import socket
import struct
import sys
import time
import uuid

# ─────────────────────────────────────────────────────────────────────────────
# Protocol
# ─────────────────────────────────────────────────────────────────────────────

MAGIC   = "MCAST"
VERSION = 1


def build_payload(seq: int, sid: str, src_ip: str, msg: str) -> bytes:
    return json.dumps({
        "magic": MAGIC, "ver": VERSION,
        "sid": sid, "src": src_ip,
        "seq": seq, "t": time.time(), "msg": msg,
    }, separators=(",", ":")).encode()


def parse_payload(data: bytes):
    try:
        p = json.loads(data.decode())
        if p.get("magic") == MAGIC and all(k in p for k in ("sid", "seq", "t")):
            return p
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Cross-platform interface IP lookup
# ─────────────────────────────────────────────────────────────────────────────

def get_iface_ip(iface: str) -> str:
    """
    Return the IPv4 address of *iface* on Linux, macOS, or Windows.
    Falls back to '' (INADDR_ANY) if it cannot be determined.
    """
    os_name = platform.system()

    # ── Linux: ioctl SIOCGIFADDR ──────────────────────────────────────────────
    if os_name == "Linux":
        try:
            import fcntl
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            raw = fcntl.ioctl(s.fileno(), 0x8915,
                              struct.pack("256s", iface[:15].encode()))
            s.close()
            return socket.inet_ntoa(raw[20:24])
        except Exception:
            pass

    # ── macOS / Windows: enumerate via socket.getaddrinfo + if-name match ─────
    # socket.if_nametoindex is available on both platforms; we use it only to
    # confirm the interface exists, then scan getaddrinfo results.
    try:
        socket.if_nametoindex(iface)          # raises OSError if unknown
    except (AttributeError, OSError):
        pass  # if_nametoindex absent (old Windows) – fall through to scan

    # Walk every AF_INET address on this host and try to match the iface name.
    # On Windows we match against the adapter description / friendly name via
    # the pure-stdlib socket.getaddrinfo; on macOS/Linux the iface name is
    # directly available via if_nameindex().
    if os_name in ("Darwin", "Linux"):
        try:
            import subprocess
            # 'ifconfig <iface>' is available on both macOS and Linux
            out = subprocess.check_output(
                ["ifconfig", iface], stderr=subprocess.DEVNULL, text=True
            )
            for token in out.split():
                try:
                    ip = ipaddress.IPv4Address(token)
                    if not ip.is_loopback:
                        return str(ip)
                except ValueError:
                    pass
        except Exception:
            pass

    if os_name == "Windows":
        try:
            import subprocess
            out = subprocess.check_output(
                ["ipconfig"], stderr=subprocess.DEVNULL, text=True
            )
            # Find the adapter block that contains the iface name, then grab IP
            in_block = False
            for line in out.splitlines():
                if iface.lower() in line.lower():
                    in_block = True
                if in_block and "IPv4" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        candidate = parts[-1].strip().rstrip("(Preferred)").strip()
                        try:
                            ipaddress.IPv4Address(candidate)
                            return candidate
                        except ValueError:
                            pass
        except Exception:
            pass

    return ""   # caller will use INADDR_ANY


# ─────────────────────────────────────────────────────────────────────────────
# Interface enumeration (cross-platform)
# ─────────────────────────────────────────────────────────────────────────────

def enumerate_interfaces() -> list:
    """
    Return a list of dicts describing each interface with an IPv4 address:
      iface  — interface name (str)
      ip     — IPv4 address (str)
      is_lo  — whether it's a loopback interface (bool)
    
    Sorted with loopback last.
    """
    os_name = platform.system()
    ifaces  = []

    if os_name == "Linux":
        try:
            import subprocess
            out = subprocess.check_output(
                ["ip", "addr", "show"], stderr=subprocess.DEVNULL, text=True
            )
            current_iface = None
            for line in out.splitlines():
                # "1: lo: <LOOPBACK,UP,...>"
                if line and line[0].isdigit():
                    parts = line.split(":")
                    if len(parts) >= 2:
                        current_iface = parts[1].strip()
                # "    inet 127.0.0.1/8 scope host lo"
                elif "inet " in line and current_iface:
                    tokens = line.split()
                    if len(tokens) >= 2:
                        addr_cidr = tokens[1]
                        ip = addr_cidr.split("/")[0]
                        try:
                            ipaddress.IPv4Address(ip)
                            is_lo = ipaddress.IPv4Address(ip).is_loopback
                            ifaces.append({"iface": current_iface, "ip": ip, "is_lo": is_lo})
                        except ValueError:
                            pass
        except Exception:
            pass

    elif os_name == "Darwin":  # macOS
        try:
            import subprocess
            out = subprocess.check_output(
                ["ifconfig"], stderr=subprocess.DEVNULL, text=True
            )
            current_iface = None
            for line in out.splitlines():
                # "en0: flags=8863<UP,BROADCAST,RUNNING,SIMPLEX,MULTICAST> mtu 1500"
                if line and not line[0].isspace():
                    current_iface = line.split(":")[0].strip()
                # "\tinet 192.168.1.100 netmask 0xffffff00 broadcast 192.168.1.255"
                elif "\tinet " in line and current_iface:
                    tokens = line.split()
                    if len(tokens) >= 2:
                        ip = tokens[1]
                        try:
                            ipaddress.IPv4Address(ip)
                            is_lo = ipaddress.IPv4Address(ip).is_loopback
                            ifaces.append({"iface": current_iface, "ip": ip, "is_lo": is_lo})
                        except ValueError:
                            pass
        except Exception:
            pass

    elif os_name == "Windows":
        try:
            import subprocess
            out = subprocess.check_output(
                ["ipconfig"], stderr=subprocess.DEVNULL, text=True
            )
            current_iface = None
            for line in out.splitlines():
                # "Ethernet adapter Ethernet:" or "Wireless LAN adapter Wi-Fi:"
                if "adapter" in line.lower() and ":" in line:
                    current_iface = line.split(":")[0].replace("adapter", "").strip()
                # "   IPv4 Address. . . . . . . . : 192.168.1.100"
                elif "IPv4" in line and ":" in line and current_iface:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        ip = parts[-1].strip().rstrip("(Preferred)").strip()
                        try:
                            ipaddress.IPv4Address(ip)
                            is_lo = ipaddress.IPv4Address(ip).is_loopback
                            ifaces.append({"iface": current_iface, "ip": ip, "is_lo": is_lo})
                        except ValueError:
                            pass
        except Exception:
            pass

    # Sort: non-loopback first, then loopback, then by iface name
    ifaces.sort(key=lambda x: (x["is_lo"], x["iface"]))
    return ifaces


def prompt_interface() -> str:
    """
    Enumerate interfaces and prompt the user to choose one.
    Returns the interface name (str).
    """
    ifaces = enumerate_interfaces()

    if not ifaces:
        print("ERROR: No interfaces with IPv4 addresses found.")
        sys.exit(1)

    print("\nAvailable interfaces with IPv4 addresses:\n")
    for i, iface_info in enumerate(ifaces, 1):
        marker = " [loopback]" if iface_info["is_lo"] else ""
        print(f"  {i}. {iface_info['iface']:20}  {iface_info['ip']:15}{marker}")

    print()
    while True:
        try:
            choice = input(f"Select interface (1-{len(ifaces)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(ifaces):
                selected = ifaces[idx]["iface"]
                selected_ip = ifaces[idx]["ip"]
                print(f"  Selected: {selected} ({selected_ip})\n")
                return selected
            else:
                print(f"  Please enter a number between 1 and {len(ifaces)}.")
        except ValueError:
            print(f"  Please enter a valid number.")


# ─────────────────────────────────────────────────────────────────────────────
# Argument helpers
# ─────────────────────────────────────────────────────────────────────────────

def valid_mcast(addr: str) -> str:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{addr}' is not a valid IP address.")
    if not ip.is_multicast:
        raise argparse.ArgumentTypeError(
            f"'{addr}' is not a multicast address (224.x.x.x – 239.x.x.x).")
    return addr


# ─────────────────────────────────────────────────────────────────────────────
# Multicast group information
# ─────────────────────────────────────────────────────────────────────────────

def mcast_info(group: str) -> dict:
    """
    Return a dict describing the multicast group address:
      scope  — human-readable scope name
      type   — well-known protocol name (if applicable) or 'User-defined'
      mac    — corresponding Layer-2 multicast MAC address (01:00:5e:xx:xx:xx)
    """
    ip  = ipaddress.IPv4Address(group)
    oct = [int(o) for o in group.split(".")]

    # ── Scope ─────────────────────────────────────────────────────────────────
    if ip in ipaddress.IPv4Network("224.0.0.0/24"):
        scope = "Link-local (not routed)"
    elif ip in ipaddress.IPv4Network("224.0.1.0/24"):
        scope = "Internetwork control"
    elif ip in ipaddress.IPv4Network("232.0.0.0/8"):
        scope = "Source-specific (SSM)"
    elif ip in ipaddress.IPv4Network("233.0.0.0/8"):
        scope = "GLOP (AS-based)"
    elif ip in ipaddress.IPv4Network("239.0.0.0/8"):
        scope = "Administratively scoped (site-local)"
    else:
        scope = "Global"

    # ── Well-known group names ────────────────────────────────────────────────
    WELL_KNOWN = {
        "224.0.0.1":   "All-hosts",
        "224.0.0.2":   "All-routers",
        "224.0.0.4":   "DVMRP routers",
        "224.0.0.5":   "OSPF all-routers",
        "224.0.0.6":   "OSPF DR/BDR",
        "224.0.0.9":   "RIPv2 routers",
        "224.0.0.10":  "EIGRP routers",
        "224.0.0.13":  "PIM routers",
        "224.0.0.22":  "IGMPv3",
        "224.0.1.1":   "NTP",
        "224.0.1.39":  "Cisco RP announce",
        "224.0.1.40":  "Cisco RP discovery",
        "232.0.0.0/8": "SSM range",
        "239.0.0.0/8": "Admin-scoped range",
    }
    grp_type = WELL_KNOWN.get(group, "User-defined")

    # ── Layer-2 MAC (RFC 1112): 01:00:5e + low 23 bits of group address ───────
    mac = f"01:00:5e:{oct[1] & 0x7f:02x}:{oct[2]:02x}:{oct[3]:02x}"

    return {"scope": scope, "type": grp_type, "mac": mac}


# ─────────────────────────────────────────────────────────────────────────────
# Source
# ─────────────────────────────────────────────────────────────────────────────

def run_source(args):
    sid      = str(uuid.uuid4())
    local_ip = get_iface_ip(args.interface) or "0.0.0.0"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, args.ttl)
    if local_ip != "0.0.0.0":
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF,
                        socket.inet_aton(local_ip))

    gi = mcast_info(args.group)
    W  = 62
    print("=" * W)
    print(f"  SOURCE")
    print(f"  iface  : {args.interface} ({local_ip})  id={sid[:8]}...")
    print(f"  group  : {args.group}:{args.port}  ttl={args.ttl}  every {args.interval}s")
    print(f"  scope  : {gi['scope']}")
    print(f"  type   : {gi['type']}")
    print(f"  L2 MAC : {gi['mac']}")
    print(f"  msg    : '{args.message}'")
    print("-" * W)
    print(f"  {'SEQ':>6}  {'TIMESTAMP':>19}  {'B':>5}")
    print("-" * W)

    seq, running = 0, True

    def _stop(s, f): nonlocal running; running = False
    signal.signal(signal.SIGINT,  _stop)
    signal.signal(signal.SIGTERM, _stop)

    while running:
        seq += 1
        data = build_payload(seq, sid, local_ip, args.message)
        sock.sendto(data, (args.group, args.port))
        print(f"  {seq:>6}  {time.strftime('%Y-%m-%d %H:%M:%S'):>19}  {len(data):>5}")
        time.sleep(args.interval)

    sock.close()
    print("-" * W)
    print(f"  Done — {seq} packet(s) sent.")
    print("=" * W)


# ─────────────────────────────────────────────────────────────────────────────
# Per-source statistics
# ─────────────────────────────────────────────────────────────────────────────

class SourceStats:
    def __init__(self, sid, src_ip, msg):
        self.sid       = sid
        self.src_ip    = src_ip
        self.msg       = msg
        self.first_seq = None
        self.last_seq  = None
        self.rx        = 0
        self.lost      = 0    # estimated from gaps
        self.dup       = 0
        self.ooo       = 0
        self.lats      = []   # one-way delay samples (seconds)

    def update(self, seq, tx_time):
        lat = time.time() - tx_time
        self.rx += 1
        self.lats.append(lat)
        flag = ""
        if self.last_seq is None:
            self.first_seq = seq
        else:
            gap = seq - self.last_seq
            if gap == 0:
                self.dup += 1;  flag = "DUP"
            elif gap < 0:
                self.ooo += 1;  flag = "OOO"
            elif gap > 1:
                self.lost += gap - 1
                flag = f"GAP({gap-1})"
        self.last_seq = max(seq, self.last_seq or seq)
        return lat, flag

    def summary(self):
        total = self.rx + self.lost
        lats  = self.lats
        return {
            "src_ip":   self.src_ip,
            "sid8":     self.sid[:8],
            "msg":      self.msg,
            "seq":      f"{self.first_seq}-{self.last_seq}",
            "rx":       self.rx,
            "lost":     self.lost,
            "loss_pct": self.lost / total * 100 if total else 0.0,
            "dup":      self.dup,
            "ooo":      self.ooo,
            "lat_avg":  sum(lats) / len(lats) * 1000 if lats else 0.0,
            "lat_min":  min(lats) * 1000 if lats else 0.0,
            "lat_max":  max(lats) * 1000 if lats else 0.0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Receiver
# ─────────────────────────────────────────────────────────────────────────────

def run_receiver(args):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # SO_REUSEPORT: Linux/macOS only — skip silently on Windows
    if hasattr(socket, "SO_REUSEPORT"):
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass

    sock.bind(("", args.port))

    gi       = mcast_info(args.group)
    local_ip = get_iface_ip(args.interface)
    mreq = struct.pack("4s4s",
                       socket.inet_aton(args.group),
                       socket.inet_aton(local_ip) if local_ip else b"\x00\x00\x00\x00")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(1.0)

    W = 68
    print("=" * W)
    print(f"  RECEIVER")
    print(f"  iface  : {args.interface} ({local_ip or 'ANY'})")
    print(f"  group  : {args.group}:{args.port}")
    print(f"  scope  : {gi['scope']}")
    print(f"  type   : {gi['type']}")
    print(f"  L2 MAC : {gi['mac']}")
    print("-" * W)
    print(f"  {'#RX':>5}  {'SOURCE':>15}  {'ID':>8}  {'SEQ':>6}  {'LAT(ms)':>8}  STATUS")
    print("-" * W)

    sources = {}
    total_rx, total_bad = 0, 0
    running = True

    def _stop(s, f): nonlocal running; running = False
    signal.signal(signal.SIGINT,  _stop)
    signal.signal(signal.SIGTERM, _stop)

    while running:
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue
        except OSError:
            break

        total_rx += 1
        pkt = parse_payload(data)

        if pkt is None:
            total_bad += 1
            print(f"  {total_rx:>5}  {addr[0]:>15}  {'?':>8}  {'?':>6}  {'?':>8}  NON-MCAST")
            continue

        sid    = pkt["sid"]
        src_ip = pkt.get("src", addr[0])
        sid8   = sid[:8]

        if sid not in sources:
            sources[sid] = SourceStats(sid, src_ip, pkt.get("msg", ""))
            print(f"\n  ++ NEW SOURCE  {src_ip}  id={sid8}...  msg='{pkt.get('msg','')}'\n")

        lat, flag = sources[sid].update(pkt["seq"], pkt["t"])
        status    = flag if flag else "ok"
        print(f"  {total_rx:>5}  {src_ip:>15}  {sid8:>8}  "
              f"{pkt['seq']:>6}  {lat*1000:>8.2f}  {status}")

    sock.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    W2 = 52
    print("\n" + "=" * W2)
    print(f"  SUMMARY   rx={total_rx}  bad={total_bad}  sources={len(sources)}")
    print(f"  group={args.group}:{args.port}  scope={gi['scope']}")
    print(f"  type={gi['type']}  L2 MAC={gi['mac']}")
    print("-" * W2)
    for i, st in enumerate(sources.values(), 1):
        s = st.summary()
        print(f"  [{i}] {s['src_ip']}  id={s['sid8']}...  msg='{s['msg']}'")
        print(f"      seq {s['seq']}  rx={s['rx']}  "
              f"lost={s['lost']} ({s['loss_pct']:.1f}%)  "
              f"dup={s['dup']}  ooo={s['ooo']}")
        print(f"      lat  avg={s['lat_avg']:.2f}ms  "
              f"min={s['lat_min']:.2f}ms  max={s['lat_max']:.2f}ms")
        if i < len(sources):
            print()
    print("=" * W2)
    print("  * Latency valid only with synchronised clocks (NTP/PTP)")
    print("=" * W2)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        prog="multicast_test.py",
        description="Multicast traffic tester — Linux / macOS / Windows.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Omit -i to choose from available interfaces interactively:
  python3 multicast_test.py source   -g 239.1.1.1 -p 5000
  python3 multicast_test.py receiver -g 239.1.1.1 -p 5000

  # Or specify interface directly:
  python3 multicast_test.py source   -g 239.1.1.1 -p 5000 -i eth0 --ttl 32
  python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0

Notes:
  TTL must be >= the number of routers between source and receiver.
  Multiple simultaneous sources are each tracked independently.
  Latency figures require NTP/PTP clock sync between nodes.
""")

    sub    = p.add_subparsers(dest="mode", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("-g", "--group",     required=True, type=valid_mcast,
                        metavar="ADDR", help="Multicast group (e.g. 239.1.1.1)")
    shared.add_argument("-p", "--port",      required=True, type=int,
                        metavar="PORT", help="UDP port (e.g. 5000)")
    shared.add_argument("-i", "--interface", required=False, default=None,
                        metavar="IFACE", help="Interface name (optional; prompted if omitted)")

    src = sub.add_parser("source",   parents=[shared], help="Send multicast packets")
    src.add_argument("--ttl",      type=int,   default=16,               metavar="N",
                     help="IP TTL (default 16)")
    src.add_argument("--interval", type=float, default=1.0,              metavar="SEC",
                     help="Seconds between packets (default 1.0)")
    src.add_argument("--message",  type=str,   default="Multicast test", metavar="TEXT",
                     help="Label embedded in every packet")

    sub.add_parser("receiver", parents=[shared], help="Receive and verify packets")
    return p


def main():
    args = build_parser().parse_args()
    # Prompt for interface if not provided
    if args.interface is None:
        args.interface = prompt_interface()
    if args.mode == "source":
        run_source(args)
    else:
        run_receiver(args)


if __name__ == "__main__":
    main()
