#!/usr/bin/env python
"""Canonical Huffman coding: compress/decompress files and inspect code tables.

File format (.huf):
    magic      4 bytes  b"HUF1"
    length     8 bytes  big-endian original byte count
    nsyms      2 bytes  big-endian number of symbols with a code (0..256)
    table      nsyms * 2 bytes: (symbol, code length)
    payload    canonical-code bitstream, MSB first, zero-padded to a byte
"""
import argparse
import heapq
import struct
import sys
from collections import Counter

MAGIC = b"HUF1"
MAX_LEN = 255  # code lengths are stored in one byte


def code_lengths(freqs):
    """Return {symbol: code length} built from a Huffman tree.

    Each heap entry is (weight, tiebreak, symbols-in-subtree). Merging two
    subtrees pushes every symbol inside them one level deeper, so we only
    track depths, never explicit nodes.
    """
    items = [(w, s, [s]) for s, w in freqs.items() if w > 0]
    if not items:
        return {}
    if len(items) == 1:
        return {items[0][2][0]: 1}  # one symbol still needs a 1-bit code
    heapq.heapify(items)
    depth = {s: 0 for _, s, _ in items}
    tiebreak = 256
    while len(items) > 1:
        w1, _, a = heapq.heappop(items)
        w2, _, b = heapq.heappop(items)
        for s in a + b:
            depth[s] += 1
        heapq.heappush(items, (w1 + w2, tiebreak, a + b))
        tiebreak += 1
    if max(depth.values()) > MAX_LEN:
        raise ValueError("code length exceeds 255 bits")
    return depth


def canonical_codes(lengths):
    """Assign canonical codes: sort by (length, symbol), count upward.

    Canonical codes let the decoder rebuild the exact table from lengths
    alone, so the header never stores the tree.
    """
    codes = {}
    code = 0
    prev_len = 0
    for sym, ln in sorted(lengths.items(), key=lambda kv: (kv[1], kv[0])):
        code <<= ln - prev_len
        codes[sym] = (code, ln)
        code += 1
        prev_len = ln
    return codes


def encode(data):
    data = bytes(data)
    lengths = code_lengths(Counter(data))
    codes = canonical_codes(lengths)
    out = bytearray(MAGIC)
    out += struct.pack(">QH", len(data), len(lengths))
    for sym in sorted(lengths):
        out += bytes((sym, lengths[sym]))
    acc = 0
    nbits = 0
    for byte in data:
        code, ln = codes[byte]
        acc = (acc << ln) | code
        nbits += ln
        while nbits >= 8:
            nbits -= 8
            out.append((acc >> nbits) & 0xFF)
        acc &= (1 << nbits) - 1
    if nbits:
        out.append((acc << (8 - nbits)) & 0xFF)
    return bytes(out)


def decode(blob):
    blob = bytes(blob)
    if len(blob) < 14 or blob[:4] != MAGIC:
        raise ValueError("not a HUF1 stream")
    length, nsyms = struct.unpack(">QH", blob[4:14])
    pos = 14
    if nsyms > 256 or len(blob) < pos + 2 * nsyms:
        raise ValueError("corrupt header")
    lengths = {}
    for i in range(nsyms):
        sym, ln = blob[pos + 2 * i], blob[pos + 2 * i + 1]
        if ln == 0:
            raise ValueError("corrupt header: zero code length")
        lengths[sym] = ln
    pos += 2 * nsyms
    if length and not lengths:
        raise ValueError("corrupt header: no symbols")
    lookup = {(ln, code): sym for sym, (code, ln) in canonical_codes(lengths).items()}
    out = bytearray()
    code = 0
    ln = 0
    for byte in blob[pos:]:
        for shift in range(7, -1, -1):
            if len(out) == length:
                break
            code = (code << 1) | ((byte >> shift) & 1)
            ln += 1
            sym = lookup.get((ln, code))
            if sym is not None:
                out.append(sym)
                code = 0
                ln = 0
            elif ln > MAX_LEN:
                raise ValueError("corrupt payload")
    if len(out) != length:
        raise ValueError("truncated payload")
    return bytes(out)


def table(data):
    """Rows of (symbol, count, code string) sorted by code length then symbol."""
    freqs = Counter(bytes(data))
    codes = canonical_codes(code_lengths(freqs))
    rows = [(s, freqs[s], format(c, "0%db" % ln)) for s, (c, ln) in codes.items()]
    return sorted(rows, key=lambda r: (len(r[2]), r[0]))


def entropy_bits(data):
    import math
    n = len(data)
    if not n:
        return 0.0
    return -sum(c / n * math.log2(c / n) for c in Counter(data).values())


def _show(sym):
    ch = chr(sym)
    return repr(ch) if ch.isprintable() else "0x%02x" % sym


def main(argv=None):
    p = argparse.ArgumentParser(description="Canonical Huffman coder")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("compress", "decompress"):
        sp = sub.add_parser(name)
        sp.add_argument("input")
        sp.add_argument("output")
    sp = sub.add_parser("stats", help="show code table and compression stats")
    sp.add_argument("input")
    sp.add_argument("--top", type=int, default=10, help="rows to show (0 = all)")
    args = p.parse_args(argv)

    try:
        with open(args.input, "rb") as f:
            data = f.read()
        if args.cmd == "compress":
            blob = encode(data)
            with open(args.output, "wb") as f:
                f.write(blob)
            ratio = len(blob) / len(data) * 100 if data else 0
            print("%d -> %d bytes (%.1f%%)" % (len(data), len(blob), ratio))
        elif args.cmd == "decompress":
            raw = decode(data)
            with open(args.output, "wb") as f:
                f.write(raw)
            print("%d -> %d bytes" % (len(data), len(raw)))
        else:
            rows = table(data)
            total_bits = sum(c * len(code) for _, c, code in rows)
            avg = total_bits / len(data) if data else 0
            print("bytes: %d  symbols: %d" % (len(data), len(rows)))
            print("entropy: %.3f bits/byte  huffman: %.3f bits/byte" % (entropy_bits(data), avg))
            print("encoded size: %d bytes (payload) + %d header" % ((total_bits + 7) // 8, 14 + 2 * len(rows)))
            shown = rows if args.top == 0 else rows[: args.top]
            for sym, count, code in shown:
                print("  %-6s %6d  %s" % (_show(sym), count, code))
            if len(shown) < len(rows):
                print("  ... %d more" % (len(rows) - len(shown)))
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
