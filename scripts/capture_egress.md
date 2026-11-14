# pcap Capture for Zero-Egress Claim Verification

**TODO_HUMAN** — This file documents the procedure to capture and verify that the
Voice Agent Studio system makes zero external network egress during inference.

## Purpose

The paper claims zero data egress during local inference mode. This must be
verified with a packet capture on the inference host.

## Required Tools

- `tcpdump` (Linux/macOS) or `Wireshark` / `tshark` (Windows)
- Network interface with promiscuous mode access

## Procedure

```bash
# Linux / macOS
sudo tcpdump -i eth0 -w capture.pcap not arp and not broadcast \
  "host <INFERENCE_HOST_IP> and not (dst net 127.0.0.0/8)"

# Run inference for N turns
python scripts/bench_v2v_acoustic.py --mode stream --turns 300

# Stop capture; analyse
tshark -r capture.pcap -Y "ip.dst != 127.0.0.1 and ip.dst != <INFERENCE_HOST_IP>" \
  -T fields -e ip.dst | sort -u
```

## Expected Result

No external IP addresses should appear in the filtered capture output during
local inference mode (all traffic should be loopback or LAN-internal only).

## TODO_HUMAN

1. Run on actual inference hardware (see `research/configuration.yaml`).
2. Record the capture as evidence (upload pcap hash to Zenodo).
3. Update `results/PENDING_MEASUREMENTS.md` item 6 when done.
