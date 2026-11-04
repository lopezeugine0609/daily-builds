import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

import cache_sim as cs


def hit_rate(trace, capacity, policy):
    return cs.simulate(trace, capacity, policy)["hits"]


class PolicyTests(unittest.TestCase):
    def test_lru_classic(self):
        # cap 2: a(m) b(m) a(h) c(m, evict b) b(m, evict a) a(m)
        self.assertEqual(hit_rate(list("abacba"), 2, "lru"), 1)

    def test_lru_recency_refresh(self):
        # a b a c -> c evicts b (a was refreshed), so a hits again
        self.assertEqual(hit_rate(list("abaca"), 2, "lru"), 2)

    def test_fifo_hits_do_not_refresh(self):
        # cap 2: a b a c -> c evicts a (oldest insert), final a misses
        self.assertEqual(hit_rate(list("abaca"), 2, "fifo"), 1)

    def test_fifo_belady_anomaly_sequence(self):
        # classic Belady anomaly: more frames, fewer hits under FIFO
        seq = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]
        self.assertEqual(hit_rate(seq, 3, "fifo"), 3)
        self.assertEqual(hit_rate(seq, 4, "fifo"), 2)
        # LRU and OPT never show the anomaly on this trace
        self.assertGreaterEqual(hit_rate(seq, 4, "lru"), hit_rate(seq, 3, "lru"))
        self.assertGreaterEqual(hit_rate(seq, 4, "opt"), hit_rate(seq, 3, "opt"))

    def test_lfu_keeps_frequent_key(self):
        # a is hot; scan of one-off keys must not evict it
        trace = list("aaaa") + list("bcde") + list("a")
        self.assertEqual(hit_rate(trace, 2, "lfu") >= 4, True)
        # the final a is a hit under LFU
        self.assertEqual(cs.simulate(trace, 2, "lfu")["hits"], 4)

    def test_lfu_tie_breaks_on_recency(self):
        # cap 2, both freq 1: b is least recent, so c evicts b
        trace = list("abc") + list("a")
        self.assertEqual(cs.simulate(trace, 2, "lfu")["hits"], 0)
        trace = list("abac") + list("b")  # a freq 2, b freq 1 -> c evicts b
        self.assertEqual(cs.simulate(trace, 2, "lfu")["hits"], 1)

    def test_opt_known_value(self):
        # cap 2, Belady evicts the key whose next use is farthest away; hand-traced = 3 hits
        seq = list("abcbdadcba")
        self.assertEqual(hit_rate(seq, 2, "opt"), 3)

    def test_opt_matches_brute_force(self):
        # exhaustive: try every eviction choice, keep the best hit count
        def brute(trace, cap):
            def best(cache, i):
                if i == len(trace):
                    return 0
                key = trace[i]
                if key in cache:
                    return 1 + best(cache, i + 1)
                if len(cache) < cap:
                    return best(cache | {key}, i + 1)
                return max(best((cache - {v}) | {key}, i + 1) for v in cache)
            return best(frozenset(), 0)

        import random
        rng = random.Random(7)
        for _ in range(40):
            trace = [rng.randrange(5) for _ in range(12)]
            for cap in (1, 2, 3):
                self.assertEqual(hit_rate(trace, cap, "opt"), brute(trace, cap), (trace, cap))

    def test_opt_is_upper_bound(self):
        import random
        rng = random.Random(1234)
        for _ in range(30):
            trace = [rng.randrange(8) for _ in range(120)]
            for cap in (1, 2, 3, 5):
                opt = hit_rate(trace, cap, "opt")
                for pol in ("lru", "fifo", "lfu"):
                    self.assertGreaterEqual(opt, hit_rate(trace, cap, pol), (pol, cap))

    def test_capacity_covers_all_keys_all_hit_after_first(self):
        trace = list("abcabcabc")
        for pol in cs.POLICIES:
            self.assertEqual(hit_rate(trace, 3, pol), 6, pol)

    def test_capacity_one(self):
        self.assertEqual(hit_rate(list("aaab"), 1, "lru"), 2)
        self.assertEqual(hit_rate(list("aaab"), 1, "opt"), 2)

    def test_empty_trace(self):
        r = cs.simulate([], 4, "lru")
        self.assertEqual((r["hits"], r["misses"], r["hit_rate"]), (0, 0, 0.0))

    def test_hits_plus_misses_equals_total(self):
        trace = list("abcdeabcde")
        for pol in cs.POLICIES:
            r = cs.simulate(trace, 3, pol)
            self.assertEqual(r["hits"] + r["misses"], len(trace))

    def test_bad_arguments(self):
        with self.assertRaises(ValueError):
            cs.simulate(["a"], 0, "lru")
        with self.assertRaises(ValueError):
            cs.simulate(["a"], 2, "random")


class ParseTests(unittest.TestCase):
    def test_comments_and_blank_lines(self):
        text = "# header\n\na b\n  c  \n# trailing\n"
        self.assertEqual(cs.parse_trace(text), ["a", "b", "c"])

    def test_parse_list(self):
        self.assertEqual(cs.parse_list("1, 2,4", int, "capacity"), [1, 2, 4])
        with self.assertRaises(Exception):
            cs.parse_list("1,x", int, "capacity")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt")
        self.tmp.write("a b a c a b d a\n")
        self.tmp.close()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = cs.main(list(argv))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_table_output(self):
        code, out, _ = self.run_cli(self.tmp.name, "-c", "2", "-p", "lru,opt")
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertEqual(lines[0], "trace: 8 accesses, 4 distinct keys")
        self.assertIn("lru", lines[1])
        self.assertIn("opt", lines[1])
        self.assertEqual(len(lines), 3)

    def test_json_output(self):
        code, out, _ = self.run_cli(self.tmp.name, "-c", "3", "-p", "fifo", "--json")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["accesses"], 8)
        self.assertEqual(data["distinct"], 4)
        self.assertEqual(data["results"][0]["policy"], "fifo")

    def test_stdin(self):
        import sys
        old = sys.stdin
        sys.stdin = io.StringIO("x x x\n")
        try:
            code, out, _ = self.run_cli("-", "-c", "1", "-p", "lru")
        finally:
            sys.stdin = old
        self.assertEqual(code, 0)
        self.assertIn("66.7%", out)

    def test_missing_file(self):
        code, _, err = self.run_cli("does-not-exist.txt")
        self.assertEqual(code, 1)
        self.assertIn("cache-sim:", err)

    def test_bad_policy_exits_2(self):
        code, _, err = self.run_cli(self.tmp.name, "-p", "random")
        self.assertEqual(code, 2)
        self.assertIn("unknown policy", err)

    def test_zero_capacity_exits_2(self):
        code, _, _ = self.run_cli(self.tmp.name, "-c", "0")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
