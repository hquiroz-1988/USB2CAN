"""USB2CAN self-test: firmware version, loopback round trip, latency, throughput.

Runs in silent loopback mode: frames loop back inside the CAN controller and
nothing is driven onto the bus, so it is safe with or without a bus attached.

    python tools/selftest.py [--bitrate 1000000] [--count 5000] [--serial ED000200]
                             [--max-rate 3000] [--soak SECONDS] [--soak-dlc 0-8]
                             [--soak-ids mixed|std|ext]

High rates and long soaks can lock the device up (receive stall or complete
hang, both until it is unplugged and replugged). --max-rate 0 sends unpaced.
"""
import argparse
import bisect
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from usb2can import USB2CAN, Frame  # noqa: E402
from usb2can.device import DEFAULT_MAX_TX_RATE  # noqa: E402

STALL_HINT = ("  -> frames are missing: the device's receive path has probably stalled. "
              "Unplug and replug it.")


def key(f):
    return f.id, f.data, f.extended, f.rtr, f.dlc


def bits_per_frame(f):
    """CAN frame length on the wire without stuff bits, plus 3-bit interframe space."""
    return (67 if f.extended else 47) + (0 if f.rtr else 8 * f.dlc)


def numbered_frame(seq, dlc=None, ids="mixed"):
    """Random standard/extended frame whose id carries a sequence number,
    so a lost frame can be told apart from its neighbours."""
    ext = random.random() < 0.5 if ids == "mixed" else ids == "ext"
    n = random.randrange(9) if dlc is None else dlc
    return Frame(seq & (0x1FFFFFFF if ext else 0x7FF), random.randbytes(n), extended=ext)


def align(sent, got):
    """Compare received frames with sent ones (frames within a batch must be unique,
    see numbered_frame). Returns (lost, reordered, garbled):
    lost       indexes of sent frames never received
    reordered  how many received frames are out of sequence (not in the longest in-order run)
    garbled    received frames matching nothing sent, or duplicates"""
    index = {key(f): i for i, f in enumerate(sent)}
    seen, order, garbled = set(), [], 0
    for g in got:
        i = index.get(key(g))
        if i is None or i in seen:
            garbled += 1
        else:
            seen.add(i)
            order.append(i)
    tails = []                      # longest increasing subsequence of arrival order
    for i in order:
        k = bisect.bisect_left(tails, i)
        tails[k:k + 1] = [i]
    lost = [i for i in range(len(sent)) if i not in seen]
    return lost, len(order) - len(tails), garbled


def healthy(dev):
    for i in range(3):
        dev.send(Frame(0x7F0 + i, bytes([i])))
        g = dev.recv(timeout=0.5)
        while g is not None and g.id != 0x7F0 + i:   # stragglers from the last batch
            g = dev.recv(timeout=0.5)
        if g is None:
            return False
    return True


def run_batch(dev, frames, timeout=2.0):
    """Send frames, collect them back. Returns (send_s, total_s, received)."""
    t0 = time.perf_counter()
    for f in frames:
        dev.send(f)
    t_send = time.perf_counter() - t0
    got = []
    while len(got) < len(frames):
        g = dev.recv(timeout=timeout)
        if g is None:
            break
        got.append(g)
    return t_send, time.perf_counter() - t0, got


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bitrate", type=int, default=1_000_000)
    ap.add_argument("--count", type=int, default=5000)
    ap.add_argument("--serial")
    ap.add_argument("--max-rate", type=int, default=DEFAULT_MAX_TX_RATE,
                    help="send pacing in frames/s; 0 = unpaced (can stall the device)")
    ap.add_argument("--soak", type=float, default=0, metavar="SECONDS",
                    help="also run random traffic at the paced rate for this long")
    ap.add_argument("--soak-dlc", type=int, choices=range(9), metavar="0-8",
                    help="soak with this data length only (default: random 0-8); 0 = highest frame rate")
    ap.add_argument("--soak-ids", choices=("mixed", "std", "ext"), default="mixed",
                    help="soak frame types; mixed standard/extended traffic can arrive reordered")
    args = ap.parse_args()

    with USB2CAN(args.serial) as dev:
        fw, hw = dev.version()
        print(f"device {dev.serial}  firmware {fw}  hardware {hw}")
        dev.start(args.bitrate, loopback=True, silent=True, max_tx_rate=args.max_rate or None)
        t = dev.timing
        print(f"channel open at {t.bitrate:.0f} bit/s  (brp={t.brp} tseg1={t.tseg1} "
              f"tseg2={t.tseg2} sjw={t.sjw}, sample point {t.sample_point:.1%}), "
              f"send pacing {f'{args.max_rate} frames/s' if args.max_rate else 'OFF'}")

        # 1. Round trip of edge cases
        cases = [
            Frame(0x000),
            Frame(0x7FF, b"\xff" * 8),
            Frame(0x123, b"\x01\x02\x03"),
            Frame(0x000, extended=True),
            Frame(0x1FFFFFFF, b"\xaa\x55", extended=True),
            Frame(0x18FF50E5, bytes(range(8)), extended=True),
            Frame(0x456, rtr=True, dlc=4),
            Frame(0x1ABCDEF0, rtr=True, dlc=8, extended=True),
        ]
        failures = 0
        for f in cases:
            dev.send(f)
            got = dev.recv(timeout=1.0)
            ok = got is not None and key(got) == key(f)
            failures += not ok
            print(f"  {'ok  ' if ok else 'FAIL'}  sent {f}   got {got}")
        print(f"round trip: {len(cases) - failures}/{len(cases)} frames correct")
        if failures:
            print(STALL_HINT)
            return 1

        # 2. Latency: one frame at a time, send() call to recv() return
        lat = []
        for i in range(500):
            f = Frame(0x100 + i % 0x100, i.to_bytes(2, "big"))
            t0 = time.perf_counter()
            dev.send(f)
            got = dev.recv(timeout=1.0)
            lat.append((time.perf_counter() - t0) * 1e6)
            if got is None or key(got) != key(f):
                print(f"  latency run: frame {i} lost or wrong: {got}")
                failures += 1
                break
        lat.sort()
        print(f"latency (send -> received back, {len(lat)} frames): "
              f"median {statistics.median(lat):.0f} us, p99 {lat[int(len(lat) * 0.99) - 1]:.0f} us, "
              f"max {lat[-1]:.0f} us")

        # 3. Throughput
        for label, make in (
            ("8-byte standard frames", lambda: Frame(random.randrange(0x800), random.randbytes(8))),
            ("0-byte standard frames", lambda: Frame(random.randrange(0x800))),
        ):
            frames = [make() for _ in range(args.count)]
            bus_limit = t.bitrate / statistics.mean(bits_per_frame(f) for f in frames)
            t_send, t_all, got = run_batch(dev, frames)
            bad = sum(key(a) != key(b) for a, b in zip(frames, got))
            print(f"{label}: sent {len(frames)} at {len(frames) / t_send:,.0f}/s, "
                  f"received {len(got)} ({bad} mismatched) at {len(got) / t_all:,.0f}/s; "
                  f"bus limit ~{bus_limit:,.0f}/s")
            if len(got) < len(frames) or bad:
                failures += 1
                print(STALL_HINT)
                break

        # 4. Optional soak: random traffic for a while, checked in batches
        if args.soak and not failures:
            size = "0-8" if args.soak_dlc is None else args.soak_dlc
            kinds = {"mixed": "standard/extended", "std": "standard", "ext": "extended"}[args.soak_ids]
            print(f"soak: {kinds} frames, {size} bytes, for {args.soak:.0f} s ...", flush=True)
            seq = sent = lost = reordered = garbled = 0
            stalled = False
            dev.status_log.clear()
            t_end = time.perf_counter() + args.soak
            t0 = next_report = time.perf_counter()
            while time.perf_counter() < t_end:
                if time.perf_counter() >= next_report:
                    print(f"  {time.perf_counter() - t0:6.1f} s: {sent:,} frames, {lost} lost, "
                          f"{reordered:,} reordered, {garbled} garbled so far", flush=True)
                    next_report += 30
                frames = [numbered_frame(seq + i, args.soak_dlc, args.soak_ids) for i in range(1000)]
                seq += len(frames)
                _, _, got = run_batch(dev, frames, timeout=0.5)
                missing, moved, bad = align(frames, got)
                sent += len(frames)
                lost += len(missing)
                reordered += moved
                garbled += bad
                if missing or bad:
                    where = ", ".join(f"#{i} {frames[i]}" for i in missing[:5])
                    print(f"  {time.perf_counter() - t0:6.1f} s: batch {sent // 1000}: {len(missing)} lost "
                          f"{'(' + where + (' ...' if len(missing) > 5 else '') + ')' if missing else ''}"
                          f"{f', {bad} garbled' if bad else ''}", flush=True)
                if not got and not healthy(dev):
                    stalled = True
                    break
            dt = time.perf_counter() - t0
            print(f"soak: {sent:,} frames in {dt:.0f} s ({sent / dt:,.0f}/s): {lost} lost"
                  f"{f' (1 in {sent // lost:,})' if lost else ''}, {reordered:,} reordered, {garbled} garbled")
            if dev.status_log:
                print(f"  status messages: {[str(s) for s in dev.status_log]}")
            if lost or garbled:
                failures += 1
            if stalled:
                print(STALL_HINT)

        print(f"stats {dev.stats}")
        print(f"bus status {dev.bus_status}")
        dev.stop()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
