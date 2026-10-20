import os
import random
import tempfile
import unittest

import huffman


class TestHuffman(unittest.TestCase):
    def roundtrip(self, data):
        self.assertEqual(huffman.decode(huffman.encode(data)), data)

    def test_empty(self):
        self.roundtrip(b"")

    def test_single_symbol(self):
        self.roundtrip(b"a")
        self.roundtrip(b"aaaaaaaaaaaaa")

    def test_text(self):
        self.roundtrip(b"abracadabra")
        self.roundtrip(b"the quick brown fox jumps over the lazy dog" * 50)

    def test_all_bytes_random(self):
        rng = random.Random(42)
        self.roundtrip(bytes(range(256)))
        self.roundtrip(bytes(rng.randrange(256) for _ in range(5000)))

    def test_skewed_compresses(self):
        data = b"a" * 1000 + b"b" * 10 + b"c"
        self.assertLess(len(huffman.encode(data)), len(data) // 5)

    def test_prefix_free_and_kraft(self):
        lengths = huffman.code_lengths({1: 45, 2: 13, 3: 12, 4: 16, 5: 9, 6: 5})
        codes = huffman.canonical_codes(lengths)
        strs = [format(c, "0%db" % ln) for c, ln in codes.values()]
        for a in strs:
            for b in strs:
                if a != b:
                    self.assertFalse(b.startswith(a))
        self.assertEqual(sum(2 ** -ln for ln in lengths.values()), 1)

    def test_classic_lengths(self):
        # CLRS example: f:5 e:9 c:12 b:13 d:16 a:45
        lengths = huffman.code_lengths(dict(zip(b"abcdef", [45, 13, 12, 16, 9, 5])))
        self.assertEqual(lengths[ord("a")], 1)
        self.assertEqual(sorted(lengths.values()), [1, 3, 3, 3, 4, 4])

    def test_canonical_order(self):
        codes = huffman.canonical_codes({65: 2, 66: 1, 67: 3, 68: 3})
        self.assertEqual(codes[66], (0b0, 1))
        self.assertEqual(codes[65], (0b10, 2))
        self.assertEqual(codes[67], (0b110, 3))
        self.assertEqual(codes[68], (0b111, 3))

    def test_bad_magic(self):
        with self.assertRaises(ValueError):
            huffman.decode(b"NOPE" + bytes(20))

    def test_truncated(self):
        blob = huffman.encode(b"hello world, hello huffman")
        with self.assertRaises(ValueError):
            huffman.decode(blob[:-3])

    def test_entropy_bound(self):
        data = b"mississippi river"
        rows = huffman.table(data)
        avg = sum(c * len(code) for _, c, code in rows) / len(data)
        h = huffman.entropy_bits(data)
        self.assertGreaterEqual(avg + 1e-9, h)
        self.assertLess(avg, h + 1)

    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            src, huf, out = (os.path.join(d, n) for n in ("in.txt", "in.huf", "out.txt"))
            with open(src, "wb") as f:
                f.write(b"banana bandana " * 100)
            self.assertEqual(huffman.main(["compress", src, huf]), 0)
            self.assertEqual(huffman.main(["decompress", huf, out]), 0)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"banana bandana " * 100)
            self.assertEqual(huffman.main(["decompress", src, out]), 1)


if __name__ == "__main__":
    unittest.main()
