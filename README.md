# multicast_test.py

A lightweight, cross-platform multicast traffic tester for routed networks.
Send and receive UDP multicast packets with automatic loss detection, latency
measurement, and sequence verification. Useful for testing PIM, multicast
routing, and network connectivity.

**Platforms:** Linux · macOS · Windows
**Requirements:** Python 3.8+ (stdlib only on Linux and macOS; see
[Windows note](#windows-curses-support) for optional dependency)

---

## Features

- **Structured packet format** — JSON payload with sequence numbers, timestamps, and source IDs
- **Per-source tracking** — receiver independently tracks multiple simultaneous senders
- **Loss detection** — identifies gaps, duplicates, and out-of-order packets
- **Latency measurement** — one-way delay (requires NTP/PTP clock sync)
- **Persistent terminal UI** — live banner stays fixed at the top of the terminal while output scrolls beneath it (via `curses`)
- **Persistent output on exit** — full session log is reprinted to the terminal scrollback after the script stops
- **Cross-platform** — native interface enumeration on Linux, macOS, and Windows
- **Tunnel interface support** — correctly handles GRE, IPIP, SIT, VXLAN, and other virtual interfaces on Linux (e.g. `gre0`, `tun0`)
- **Interactive interface selection** — choose network adapter from a live list, or specify with `-i`
- **Multicast scope info** — displays group classification (link-local, admin-scoped, etc.) and Layer-2 MAC
- **Clean, concise output** — minimal verbosity, easy to verify

---

## Installation

No installation required on Linux or macOS. Just ensure Python 3.8+ is available:

```bash
python3 --version
```

Clone or download the script from GitHub:

```bash
git clone https://github.com/kncisco/Multicast-Tester.git
cd Multicast-Tester
python3 multicast_test.py --help
```

### Windows curses Support

On Windows, `curses` is not part of the standard library. Without it the
script works correctly but uses plain scrolling output instead of the
persistent banner UI.

To enable the full terminal UI on Windows, install the optional dependency:

```bash
pip install -r requirements.txt
```

The `requirements.txt` uses a platform marker so this is safe to run on
Linux and macOS too — nothing will be installed on those platforms.

```text
# requirements.txt
windows-curses; sys_platform == "win32"
```

| Platform | curses source | Install needed |
|---|---|---|
| Linux | stdlib | No |
| macOS | stdlib | No |
| Windows + pip install | `windows-curses` wheel | Yes, one command |
| Windows without install | plain fallback | No — works as-is |

---

## Quick Start

### Interactive mode (choose interface when prompted)

**Terminal 1 — Start a sender:**

```bash
python3 multicast_test.py source -g 239.1.1.1 -p 5000
```

When prompted, select the interface to send from.

**Terminal 2 — Start a receiver:**

```bash
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000
```

When prompted, select the interface to listen on.

### Direct mode (specify interface explicitly)

```bash
# Sender
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0

# Receiver
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0
```

**Stop either sender or receiver with Ctrl+C.**

---

## Usage

### Source (Sender)

```
python3 multicast_test.py source -g GROUP -p PORT [-i IFACE] [OPTIONS]
```

**Required arguments:**
- `-g, --group ADDR` — Multicast group address (e.g. `239.1.1.1`)
- `-p, --port PORT` — UDP destination port (e.g. `5000`)

**Optional arguments:**
- `-i, --interface IFACE` — Interface name (e.g. `eth0`, `en0`, `gre0`, `Ethernet`). If omitted, you are prompted to choose from a list.
- `--ttl N` — IP TTL for multicast packets (default: `16`). Increase to cross more routers.
- `--interval SEC` — Seconds between packets (default: `1.0`)
- `--message TEXT` — Custom label embedded in every packet (default: `"Multicast test"`)

**Examples:**

```bash
# Send to 239.1.1.1:5000 via eth0, one packet per second, TTL 32
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --ttl 32

# Send every 0.5 seconds with a custom label
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --interval 0.5 --message "site-A"

# Send via a GRE tunnel interface
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i gre0

# Interactive interface selection
python3 multicast_test.py source -g 239.1.1.1 -p 5000
```

### Receiver (Listener)

```
python3 multicast_test.py receiver -g GROUP -p PORT [-i IFACE]
```

**Required arguments:**
- `-g, --group ADDR` — Multicast group address (must match sender)
- `-p, --port PORT` — UDP destination port (must match sender)

**Optional arguments:**
- `-i, --interface IFACE` — Interface to listen on. If omitted, you are prompted to choose from a list.

**Examples:**

```bash
# Listen on eth0 for traffic on 239.1.1.1:5000
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0

# Listen via a GRE tunnel interface
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i gre0

# Interactive interface selection
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000
```

---

## Terminal UI

### Persistent Banner

On Linux and macOS (and on Windows with `windows-curses` installed), the
script uses a `curses`-based split-screen layout:

- The **banner** is fixed at the top of the terminal for the duration of the run. It shows the interface, group, scope, TTL, and L2 MAC at a glance without being pushed off screen by scrolling output.
- Packet output **scrolls** in the region below the banner.
- The banner **redraws automatically** if the terminal is resized.

### Persistent Output After Exit

When you press **Ctrl+C**, the `curses` UI closes and the complete session
output — banner, column headers, every packet line, and the final summary —
is **reprinted to the normal terminal buffer**. This means the full run
history is available in your terminal scrollback after the script exits.

### Plain Fallback

On Windows without `windows-curses`, or in any environment where `curses`
is unavailable, the script automatically falls back to plain scrolling
output. No features are lost other than the persistent banner.

---

## Output Examples

### Source — Live (curses UI)

```
====================================================================
  SOURCE
  iface  : eth0 (10.0.1.5)  id=a1b2c3d4...
  group  : 239.1.1.1:5000  ttl=16  every 1.0s
  scope  : Administratively scoped (site-local)
  type   : User-defined
  L2 MAC : 01:00:5e:01:01:01
  msg    : 'Multicast test'
--------------------------------------------------------------------
     SEQ           TIMESTAMP  BYTES
--------------------------------------------------------------------
       1  2026-03-11 10:00:01    104   <- scrolls here
       2  2026-03-11 10:00:02    104
       3  2026-03-11 10:00:03    104
```

### Source — After Exit (reprinted to scrollback)

```
====================================================================
  SOURCE
  iface  : eth0 (10.0.1.5)  id=a1b2c3d4...
  group  : 239.1.1.1:5000  ttl=16  every 1.0s
  scope  : Administratively scoped (site-local)
  type   : User-defined
  L2 MAC : 01:00:5e:01:01:01
  msg    : 'Multicast test'
--------------------------------------------------------------------
     SEQ           TIMESTAMP  BYTES
--------------------------------------------------------------------
       1  2026-03-11 10:00:01    104
       2  2026-03-11 10:00:02    104
       3  2026-03-11 10:00:03    104

  Done — 3 packet(s) sent.
====================================================================
```

### Receiver — Live (curses UI)

```
====================================================================
  RECEIVER
  iface  : eth0 (10.0.2.5)
  group  : 239.1.1.1:5000
  scope  : Administratively scoped (site-local)
  type   : User-defined
  L2 MAC : 01:00:5e:01:01:01
--------------------------------------------------------------------
  #RX          SOURCE        ID       SEQ   LAT(ms)  STATUS
--------------------------------------------------------------------

  ++ NEW SOURCE  10.0.1.5  id=a1b2c3d4...  msg='Multicast test'

      1       10.0.1.5  a1b2c3d4       1      0.81  ok
      2       10.0.1.5  a1b2c3d4       2      0.79  ok
      3       10.0.1.5  a1b2c3d4       3      0.83  ok
      4       10.0.1.5  a1b2c3d4       5      0.91  GAP(1)
      5       10.0.1.5  a1b2c3d4       6      0.77  ok
      6       10.0.1.5  a1b2c3d4       6      0.80  DUP
      7       10.0.1.5  a1b2c3d4       5      0.78  OOO
```

**Packet status codes:**

| Code | Meaning |
|---|---|
| `ok` | Sequence number is exactly last + 1 |
| `GAP(N)` | N packets estimated lost (sequence jumped) |
| `DUP` | Duplicate sequence number received |
| `OOO` | Out-of-order (sequence went backwards) |
| `NON-MCAST` | UDP traffic on the port but not from this script |

### Receiver Session Summary (on Ctrl+C)

```
====================================================
  SUMMARY   rx=120  bad=0  sources=1
  group=239.1.1.1:5000  scope=Administratively scoped (site-local)
  type=User-defined  L2 MAC=01:00:5e:01:01:01
----------------------------------------------------
  [1] 10.0.1.5  id=a1b2c3d4...  msg='Multicast test'
      seq 1-120  rx=119  lost=1 (0.8%)  dup=0  ooo=0
      lat  avg=0.81ms  min=0.74ms  max=1.12ms
====================================================
  * Latency valid only with synchronised clocks (NTP/PTP)
====================================================
```

---

## Understanding the Output

### Multicast Group Information

The script automatically displays:

- **Scope** — Where the traffic is valid:

| Range | Scope |
|---|---|
| `224.0.0.0/24` | Link-local — not forwarded by routers |
| `224.0.1.0/24` | Internetwork control |
| `232.0.0.0/8` | Source-specific multicast (SSM, RFC 4607) |
| `233.0.0.0/8` | GLOP — assigned per AS number |
| `239.0.0.0/8` | Administratively scoped — site-local (common for testing) |
| Everything else | Global |

- **Type** — Identifies well-known protocols: `All-hosts`, `All-routers`,
  `OSPF`, `EIGRP`, `PIM`, `RIPv2`, `NTP`, `Cisco RP announce/discovery`,
  etc. Custom groups show `User-defined`.

- **L2 MAC** — Layer-2 multicast MAC address (RFC 1112):
  Format `01:00:5e:xx:xx:xx`. Useful for switch CAM table lookups and
  packet captures.

### Per-Source Statistics

When the receiver stops (Ctrl+C):

| Field | Description |
|---|---|
| `seq` | Range of sequence numbers seen (first–last) |
| `rx` | Total packets received from this source |
| `lost` | Estimated packets lost (inferred from sequence gaps) |
| `loss %` | Packet loss percentage |
| `dup` | Duplicate packets (same sequence number received twice) |
| `ooo` | Out-of-order events (sequence went backwards) |
| `lat avg/min/max` | One-way latency in ms (requires clock sync) |

---

## Interface Selection

### Automatic Interface Detection

When you omit the `-i` flag, the script scans your system for interfaces
with IPv4 addresses and prompts you to choose:

```
Available interfaces with IPv4 addresses:

  1. eth0                   192.168.1.100
  2. eth1                   10.0.0.50
  3. gre0                   172.16.0.1
  4. wlan0                  192.168.2.15
  5. lo                     127.0.0.1          [loopback]

Select interface (1-5): 3
  Selected: gre0 (172.16.0.1)
```

Loopback interfaces are listed last and marked `[loopback]`.

### Tunnel and Virtual Interfaces (Linux)

On Linux, tunnel and virtual interfaces are fully supported in both
interactive and direct mode. The following interface types are correctly
enumerated and resolved:

| Interface type | Example name |
|---|---|
| GRE tunnel | `gre0`, `gre1` |
| GRE tap | `gretap0` |
| IPIP tunnel | `tunl0` |
| SIT tunnel | `sit0` |
| TUN/TAP | `tun0` |
| VXLAN | `vxlan0` |
| IPVLAN | `ipvlan0` |

These interfaces appear in `ip addr show` output with a `name@parent`
suffix (e.g. `gre0@NONE`, `gre1@eth0`). The script strips this suffix
automatically so the interface name displayed and used is always the
clean form.

### Platform-Specific Interface Names

- **Linux** — `eth0`, `ens3`, `wlan0`, `gre0`, `tun0`, etc. (check with `ip link show`)
- **macOS** — `en0`, `en1`, `utun0`, `lo0`, etc. (check with `ifconfig`)
- **Windows** — `Ethernet`, `Wi-Fi`, `Ethernet 2`, etc. (check with `ipconfig`)

---

## Common Use Cases

### Testing Multicast Routing in a Lab

```bash
# On host A (sender):
python3 multicast_test.py source -g 239.10.20.30 -p 5555 -i eth0 --ttl 32

# On host B (receiver):
python3 multicast_test.py receiver -g 239.10.20.30 -p 5555 -i eth0
```

If the receiver does not see packets, check:
1. PIM is enabled on the multicast router
2. TTL is high enough to cross the hop count
3. Both hosts are on the correct subnets
4. IGMP is working (check `netstat -g` on receiver)

### Testing via a GRE Tunnel

```bash
# Sender — transmit over a GRE tunnel
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i gre0 --ttl 32

# Receiver — listen on the far end of the tunnel
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i gre0
```

### Measuring Latency Between Hosts

Requires NTP or PTP clock synchronisation between nodes:

```bash
# Sender (high packet rate for better statistics):
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --interval 0.1

# Receiver:
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0
```

After 30+ packets, press Ctrl+C to see average/min/max one-way delay in
the session summary.

### Testing Multiple Concurrent Sources

```bash
# Terminal 1 (source A):
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --message "source-A"

# Terminal 2 (source B):
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth1 --message "source-B"

# Terminal 3 (receiver — tracks both sources independently):
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0
```

---

## Troubleshooting

### No packets received

**Check 1: Is multicast routing enabled?**

```bash
# Linux
cat /proc/sys/net/ipv4/ip_forward
cat /proc/sys/net/ipv4/conf/all/mc_forwarding

# macOS
netstat -i | grep -i mcast
```

**Check 2: Is PIM enabled on routers in the path?**

```
show ip pim interface
show ip mroute
```

**Check 3: Is IGMP working on the receiver?**

```bash
# Linux
netstat -g | grep 239.1.1.1

# macOS
netstat -g | grep 239
```

**Check 4: Is TTL high enough?**
Increase `--ttl` to at least the number of routers between source and receiver.

**Check 5: Are group and port identical on both sides?**
Source and receiver must use the same `-g` and `-p` values.

### Tunnel interface not listed in interactive mode (Linux)

If a GRE or other tunnel interface does not appear in the interactive list,
confirm it has an IPv4 address assigned:

```bash
ip addr show gre0
```

If the interface shows `state DOWN` or has no `inet` line, it will not be
listed. Bring the interface up and assign an address before running the script.

### Interface name shows `@NONE` or similar

This should not occur in the current version. If it does, specify the
interface directly with `-i`:

```bash
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i gre0
```

### Windows: "Address already in use"

If you see `OSError: [Errno 10048]`, wait 60 seconds (TIME_WAIT expiry)
or use a different port with `-p`.

### macOS: Permission denied on raw sockets

Some macOS configurations require elevated privileges for multicast:

```bash
sudo python3 multicast_test.py source -g 239.1.1.1 -p 5000
```

### Terminal UI not appearing (curses)

The persistent banner UI requires a real TTY. It will not appear when:
- Output is redirected to a file or pipe
- The terminal does not support ANSI/curses
- On Windows without `windows-curses` installed

In all these cases the script falls back to plain scrolling output automatically.

---

## Technical Details

### Packet Format

Every multicast packet is a UTF-8 JSON object:

```json
{
  "magic": "MCAST",
  "ver": 1,
  "sid": "a1b2c3d4-e5f6-47a8-b9c0-d1e2f3a4b5c6",
  "src": "10.0.1.5",
  "seq": 42,
  "t": 1741564800.123456,
  "msg": "Multicast test"
}
```

| Field | Description |
|---|---|
| `magic` | Protocol guard — non-MCAST packets are silently discarded |
| `ver` | Protocol version (currently `1`) |
| `sid` | Stable UUID for the source instance |
| `src` | Source IP address (from outbound interface) |
| `seq` | Monotonically increasing packet counter (1-based) |
| `t` | Unix epoch timestamp (float, sub-millisecond precision) |
| `msg` | User-supplied annotation string |

### Multicast MAC Address (RFC 1112)

The Layer-2 multicast MAC is derived from the multicast IP:

```
01:00:5e:[IP[1] & 0x7f]:[IP[2]]:[IP[3]]
```

Example: `239.1.1.1` → `01:00:5e:01:01:01`

Note: Only the low 23 bits of the multicast group are encoded — multiple
group addresses can map to the same MAC.

### Loss Detection Algorithm

Per-source gap detection:
- If `seq[N] - seq[N-1] > 1` → `gap - 1` packets estimated lost
- If `seq[N] == seq[N-1]` → duplicate counted
- If `seq[N] < seq[N-1]` → out-of-order counted

Loss percentage:
```
loss_pct = lost / (received + lost) * 100
```

### Terminal UI Architecture

The curses UI uses two non-overlapping windows:

- **`banner_win`** — fixed region at rows `0` through `BANNER_TOTAL_HEIGHT`. Redrawn on every terminal resize event.
- **`scroll_win`** — scrolling region from `BANNER_TOTAL_HEIGHT` to the bottom of the terminal. `scrollok(True)` allows unlimited output.

Every line written to `scroll_win` is simultaneously appended to an
in-memory `log` list. When `curses.wrapper()` returns, `_reprint_log()`
prints the complete log to stdout so it persists in the terminal scrollback.

---

## Requirements

- **Python:** 3.8 or later
- **OS:** Linux, macOS, or Windows
- **Network:** Functional UDP/multicast support on kernel and NIC
- **Packages:** None on Linux/macOS (stdlib only). `windows-curses` optional on Windows — see [Windows curses Support](#windows-curses-support).

---

## License

MIT License — Feel free to use, modify, and distribute.

---

## Contributing

Found a bug or have a feature request? Open an issue or pull request on
GitHub at [kncisco/Multicast-Tester](https://github.com/kncisco/Multicast-Tester).

Tested on:
- Ubuntu 20.04, 22.04 LTS
- CentOS/RHEL 8, 9
- macOS 12.x, 13.x, 14.x
- Windows 10, 11

---

## FAQ

**Q: Can I use this on a non-routed (local segment) network?**

A: Yes. Use a link-local group such as `224.0.0.100` and set `--ttl 1`
to prevent packets leaving the subnet.

**Q: Do clocks need to be in sync for latency measurement?**

A: No, but offsets distort results. NTP typically keeps clocks within
±10 ms. Use latency figures as relative jitter indicators if clocks are
not synchronised.

**Q: Can I run source and receiver on the same host?**

A: Yes. On Linux you may need to enable multicast loopback:

```bash
sudo sysctl -w net.ipv4.conf.all.mc_forwarding=1
```

**Q: What happens if the receiver misses the first few packets?**

A: The receiver begins tracking from the first packet it sees, so
pre-join loss is not counted. Allow the sender to run for several seconds
before drawing conclusions from the statistics.

**Q: Why does interactive mode list my GRE tunnel correctly but the banner shows `ANY` for the IP?**

A: This was a bug where the `@NONE` parent suffix in Linux tunnel interface
names was not being stripped before the IP lookup. It is fixed in the
current version. If you still see this, specify the interface explicitly
with `-i gre0`.

**Q: Is this tool suitable for production use?**

A: No — it is designed for testing and troubleshooting multicast routing.
For production applications, use a proper message queue or streaming platform.

---

## See Also

- [RFC 1112](https://tools.ietf.org/html/rfc1112) — Host Extensions for IP Multicasting
- [RFC 4601](https://tools.ietf.org/html/rfc4601) — Protocol Independent Multicast (PIM)
- [kncisco/Multicast-Tester](https://github.com/kncisco/Multicast-Tester) — Project repository
- `iperf3` — For general UDP throughput testing
- `mtools` — Multicast utilities for Linux