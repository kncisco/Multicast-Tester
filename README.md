# multicast_test.py

A lightweight, cross-platform multicast traffic tester for routed networks. Send and receive UDP multicast packets with automatic loss detection, latency measurement, and sequence verification. Useful for testing PIM, multicast routing, and network connectivity.

**Platforms:** Linux · macOS · Windows  
**Requirements:** Python 3.8+ (stdlib only, no external packages)

---

## Features

- **Structured packet format** — JSON payload with sequence numbers, timestamps, and source IDs
- **Per-source tracking** — receiver independently tracks multiple simultaneous senders
- **Loss detection** — identifies gaps, duplicates, and out-of-order packets
- **Latency measurement** — one-way delay (requires NTP/PTP clock sync)
- **Cross-platform** — native interface enumeration on Linux, macOS, and Windows
- **Interactive interface selection** — choose network adapter from a live list
- **Multicast scope info** — displays group classification (link-local, admin-scoped, etc.) and Layer-2 MAC
- **Clean, concise output** — minimal verbosity, easy to verify

---

## Installation

No installation required. Just ensure Python 3.8+ is available:

```bash
python3 --version
```

Clone or download the script:

```bash
git clone https://github.com/yourusername/multicast_test.git
cd multicast_test
python3 multicast_test.py --help
```

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
- `-i, --interface IFACE` — Interface name (e.g. `eth0`, `en0`, `Ethernet`). If omitted, you're prompted to choose.
- `--ttl N` — IP TTL for multicast packets (default: 16). Increase to cross more routers.
- `--interval SEC` — Seconds between packets (default: 1.0)
- `--message TEXT` — Custom label embedded in every packet (default: "Multicast test")

**Examples:**

```bash
# Send to 239.1.1.1:5000 via eth0, one packet per second, TTL 32
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --ttl 32 --interval 1

# Send every 0.5 seconds with a custom label
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --interval 0.5 --message "site-A"

# Interactive mode
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
- `-i, --interface IFACE` — Interface to listen on. If omitted, you're prompted to choose.

**Examples:**

```bash
# Listen on eth0 for traffic on 239.1.1.1:5000
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0

# Interactive mode
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000
```

**Stop either sender or receiver with Ctrl+C.**

---

## Output Examples

### Source Banner

```
==============================================================
  SOURCE
  iface  : eth0 (10.0.1.5)  id=a1b2c3d4...
  group  : 239.1.1.1:5000  ttl=16  every 1.0s
  scope  : Administratively scoped (site-local)
  type   : User-defined
  L2 MAC : 01:00:5e:01:01:01
  msg    : 'Multicast test'
--------------------------------------------------------------
     SEQ          TIMESTAMP      B
--------------------------------------------------------------
       1  2026-03-10 14:22:01    142
       2  2026-03-10 14:22:02    142
       3  2026-03-10 14:22:03    142
       4  2026-03-10 14:22:04    142
       5  2026-03-10 14:22:05    142
--------------------------------------------------------------
  Done — 5 packet(s) sent.
==============================================================
```

### Receiver Banner and Live Output

```
====================================================================
  RECEIVER
  iface  : eth0 (10.0.2.5)
  group  : 239.1.1.1:5000
  scope  : Administratively scoped (site-local)
  type   : User-defined
  L2 MAC : 01:00:5e:01:01:01
--------------------------------------------------------------------
  #RX          SOURCE        ID       SEQ  LAT(ms)  STATUS
--------------------------------------------------------------------

  ++ NEW SOURCE  10.0.1.5  id=a1b2c3d4...  msg='Multicast test'

      1       10.0.1.5  a1b2c3d4       1     0.81  ok
      2       10.0.1.5  a1b2c3d4       2     0.79  ok
      3       10.0.1.5  a1b2c3d4       3     0.83  ok
      4       10.0.1.5  a1b2c3d4       5     0.91  GAP(1)
      5       10.0.1.5  a1b2c3d4       6     0.77  ok
      6       10.0.1.5  a1b2c3d4       6     0.80  DUP
      7       10.0.1.5  a1b2c3d4       5     0.78  OOO
```

**Packet status codes:**
- `ok` — Sequence number is exactly last + 1
- `GAP(N)` — N packets estimated lost (sequence jumped)
- `DUP` — Duplicate sequence number
- `OOO` — Out-of-order (sequence went backwards)
- `NON-MCAST` — UDP traffic on the port but not from this script

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
  - `Link-local (not routed)` — 224.0.0.0/24 — not forwarded by routers
  - `Internetwork control` — 224.0.1.0/24 — control traffic
  - `Source-specific (SSM)` — 232.0.0.0/8 — RFC 4607
  - `GLOP (AS-based)` — 233.0.0.0/8 — assigned per AS number
  - `Administratively scoped` — 239.0.0.0/8 — site-local (common for testing)
  - `Global` — Everything else

- **Type** — Identifies well-known protocols:
  - `All-hosts`, `All-routers`, `OSPF`, `EIGRP`, `PIM`, `RIPv2`, `NTP`, etc.
  - `User-defined` — custom application

- **L2 MAC** — Layer-2 multicast MAC address (RFC 1112):
  - Format: `01:00:5e:xx:xx:xx`
  - Useful for switch CAM table lookups and packet captures

### Per-Source Statistics

When the receiver stops (Ctrl+C), it prints:

- **seq** — Range of sequence numbers seen (first–last)
- **rx** — Total packets received from this source
- **lost** — Estimated packets lost (inferred from gaps in sequences)
- **loss %** — Packet loss percentage
- **dup** — Duplicate packets (same seq number received twice)
- **ooo** — Out-of-order events (sequence went backwards)
- **lat avg/min/max** — One-way latency in milliseconds (requires clock sync)

---

## Interface Selection

### Automatic Interface Detection

When you omit the `-i` flag, the script scans your system for interfaces with IPv4 addresses and prompts you to choose:

```
Available interfaces with IPv4 addresses:

  1. eth0                   192.168.1.100
  2. eth1                   10.0.0.50
  3. wlan0                  192.168.2.15
  4. lo                     127.0.0.1          [loopback]

Select interface (1-4): 1
  Selected: eth0 (192.168.1.100)
```

Loopback interfaces are marked `[loopback]` so you know to avoid them for routed multicast.

### Platform-Specific Interface Names

- **Linux** — `eth0`, `ens3`, `wlan0`, etc. (check with `ip link show`)
- **macOS** — `en0`, `en1`, `lo0`, etc. (check with `ifconfig`)
- **Windows** — `Ethernet`, `Wi-Fi`, `Ethernet 2`, etc. (check with `ipconfig`)

---

## Common Use Cases

### Testing Multicast Routing in a Lab

```bash
# On router/host A (sender):
python3 multicast_test.py source -g 239.10.20.30 -p 5555 -i eth0 --ttl 32

# On router/host B (receiver):
python3 multicast_test.py receiver -g 239.10.20.30 -p 5555 -i eth0
```

If the receiver doesn't see packets, check:
1. PIM is enabled on the multicast router
2. TTL is high enough to cross the hop count
3. Both hosts are on the correct subnets
4. IGMP is working (check `netstat -g` on receiver)

### Measuring Latency Between Hosts

Requires NTP or PTP clock synchronisation between nodes:

```bash
# Sender (source with low latency):
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --interval 0.1

# Receiver:
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0
```

After 30+ packets, press Ctrl+C to see average/min/max one-way delay.

### Testing Multiple Concurrent Sources

```bash
# Terminal 1 (source A):
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth0 --message "source-A"

# Terminal 2 (source B):
python3 multicast_test.py source -g 239.1.1.1 -p 5000 -i eth1 --message "source-B"

# Terminal 3 (receiver):
python3 multicast_test.py receiver -g 239.1.1.1 -p 5000 -i eth0
```

The receiver will track both sources independently, showing per-source loss and latency.

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

**Check 2: Is PIM enabled?**
```bash
# On routers in the path
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
Increase `--ttl` to match the number of routers between source and receiver.

**Check 5: Are you using the same group and port?**
Source and receiver must use identical `-g` and `-p` values.

### Windows: "Address already in use"

If you get `OSError: [Errno 10048] Only one usage of each socket address is normally permitted`, wait 60 seconds (TIME_WAIT) or use a different port.

### macOS: Permission denied on raw sockets

Some BSD/macOS configurations require elevated privileges for multicast. Try:
```bash
sudo python3 multicast_test.py source -g 239.1.1.1 -p 5000
```

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

- `magic` — Protocol guard; non-MCAST packets are silently discarded
- `ver` — Protocol version (currently 1)
- `sid` — Stable UUID for the source instance
- `src` — Source IP address (from outbound interface)
- `seq` — Monotonically increasing packet counter (1-based)
- `t` — Unix epoch timestamp (float, sub-millisecond precision)
- `msg` — User-supplied annotation string

### Multicast MAC Address (RFC 1112)

The Layer-2 multicast MAC is derived from the multicast IP:

```
01:00:5e:[IP[1] & 0x7f]:[IP[2]]:[IP[3]]
```

Example: 239.1.1.1 → `01:00:5e:01:01:01`

(Note: Only the low 23 bits of the multicast group are encoded; multiple groups can map to the same MAC.)

### Loss Detection Algorithm

Gaps in sequence numbers are detected per-source:
- If `seq[N] - seq[N-1] > 1`, then `gap - 1` packets are estimated lost
- Duplicates (seq[N] == seq[N-1]) are counted separately
- Out-of-order packets (seq[N] < seq[N-1]) are counted separately

The loss percentage is calculated as:
```
loss_pct = lost / (received + lost) * 100
```

---

## Requirements

- **Python:** 3.8 or later
- **OS:** Linux, macOS, or Windows
- **Network:** Functional UDP/multicast support on kernel and NIC
- **Packages:** None (stdlib only)

---

## License

MIT License — Feel free to use, modify, and distribute.

---

## Contributing

Found a bug or have a feature request? Open an issue or pull request on GitHub.

Tested on:
- Ubuntu 20.04, 22.04 LTS
- CentOS/RHEL 8, 9
- macOS 12.x, 13.x
- Windows 10, 11

---

## FAQ

**Q: Can I use this on a non-routed (local segment) network?**

A: Yes, but use a link-local group like `224.0.0.100` or `224.0.1.100` instead of admin-scoped (`239.x.x.x`). Set `--ttl 1` to prevent packets leaving the subnet.

**Q: Do the clocks have to be perfectly in sync for latency measurement?**

A: No, but small offsets (e.g. ±1s) will distort the results. NTP should keep you within ±10ms. Use latency only as a relative measure of jitter if clocks aren't synced.

**Q: Can I run source and receiver on the same host?**

A: Yes, but use different interfaces or bind the receiver to a different multicast group. On Linux, you may need to adjust multicast loopback settings:
```bash
sudo sysctl -w net.ipv4.ip_multicast_loopback=1
```

**Q: What happens if the receiver misses the first few packets?**

A: The receiver starts tracking from the first packet it sees, so early loss won't be counted. Wait for the sender to have sent ~10 packets before stopping the receiver.

**Q: Is this tool suitable for production use?**

A: No — it's designed for testing and troubleshooting multicast routing. For production applications, use a proper message queue or streaming platform.

---

## See Also

- [RFC 1112](https://tools.ietf.org/html/rfc1112) — Host Extensions for IP Multicasting
- [RFC 4601](https://tools.ietf.org/html/rfc4601) — Protocol Independent Multicast (PIM)
- `iperf3` — For general UDP throughput testing
- `mtools` — Multicast utilities for Linux
