# huffman

Canonical Huffman coder in pure Python (standard library only). It compresses and decompresses files, and it prints the code table next to the Shannon entropy.

## How it works

1. **Count** how often each byte value occurs.
2. **Build the tree** with a min-heap: pop the two lightest subtrees and merge them. Each merge pushes every symbol in both subtrees one level deeper. Only the depths (code lengths) are tracked, not explicit nodes.
3. **Canonicalize.** Sort symbols by `(length, symbol)` and assign codes by counting upward, shifting left when the length grows. The decoder rebuilds identical codes from the lengths alone, so the header stores only `(symbol, length)` pairs (2 bytes each) and never the tree.
4. **Pack** the codes MSB-first into bytes. The original length in the header tells the decoder where to stop, so the zero padding is ignored.

Huffman's average code length `L` always satisfies `H <= L < H + 1`, where `H` is the entropy in bits per byte. The tests check this bound.

Edge cases: an empty input has 0 symbols. An input that uses only one byte value gets a 1-bit code. Bad magic, a corrupt header, or a truncated payload raises `ValueError`, and the CLI exits with code 1.

### File format (`HUF1`)

```
magic   4 B   "HUF1"
length  8 B   original size, big-endian
nsyms   2 B   number of coded symbols
table   2 B * nsyms   (symbol, code length)
payload       bitstream, MSB first, zero-padded
```

## Usage

```
python huffman.py compress   <input> <output>
python huffman.py decompress <input> <output>
python huffman.py stats      <input> [--top N]   # N=0 shows all rows
```

Real output:

```
$ printf 'abracadabra alakazam' > demo.txt
$ python huffman.py stats demo.txt --top 0
bytes: 20  symbols: 10
entropy: 2.695 bits/byte  huffman: 2.750 bits/byte
encoded size: 7 bytes (payload) + 34 header
  'a'         9  0
  'b'         2  1000
  'd'         1  1001
  'k'         1  1010
  'l'         1  1011
  'm'         1  1100
  'r'         2  1101
  'z'         1  1110
  ' '         1  11110
  'c'         1  11111

$ python huffman.py compress huffman.py h.huf
6421 -> 3860 bytes (60.1%)
$ python huffman.py decompress h.huf h.py
3860 -> 6421 bytes
$ cmp huffman.py h.py && echo identical
identical

$ python huffman.py decompress demo.txt x
error: not a HUF1 stream
```

## Tests

```
python -m unittest -v
```

The 12 tests cover: round-trips (empty, single symbol, text, all 256 byte values, random data), prefix-freeness, the Kraft equality, the CLRS textbook example, canonical code order, the entropy bound, corrupt and truncated input, and the CLI.
