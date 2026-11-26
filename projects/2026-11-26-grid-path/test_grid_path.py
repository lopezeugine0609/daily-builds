import contextlib
import io
import json
import math
import os
import tempfile
import unittest

import grid_path as gp

OPEN = "S...\n....\n...G\n"
SWAMP = (
    "S9999G\n"
    ".####.\n"
    "......\n"
)
WALLED = "S#G\n"


class GridTests(unittest.TestCase):
    def test_parse_start_goal(self):
        g = gp.Grid(OPEN)
        self.assertEqual((g.start, g.goal, g.w, g.h), ((0, 0), (2, 3), 4, 3))

    def test_ragged_rows_padded_with_walls(self):
        g = gp.Grid("S..\n.\n..G")
        self.assertFalse(g.passable((1, 1)))

    def test_missing_or_duplicate_markers(self):
        with self.assertRaises(gp.GridError):
            gp.Grid("....G")
        with self.assertRaises(gp.GridError):
            gp.Grid("SS.G")
        with self.assertRaises(gp.GridError):
            gp.Grid("\n\n")

    def test_costs(self):
        g = gp.Grid("S5~.G")
        self.assertEqual([g.cost((0, c)) for c in range(1, 4)], [5, 5, 1])


class SearchTests(unittest.TestCase):
    def test_open_grid_manhattan(self):
        for algo in gp.ALGOS:
            r = gp.solve(OPEN, algo)
            self.assertTrue(r["found"])
            self.assertEqual(r["steps"], 5, algo)

    def test_bfs_ignores_terrain_weighted_do_not(self):
        bfs = gp.solve(SWAMP, "bfs")
        self.assertEqual(bfs["steps"], 5)
        self.assertEqual(bfs["cost"], 37)  # 9*4 + 1
        for algo in ("dijkstra", "astar"):
            r = gp.solve(SWAMP, algo)
            self.assertEqual(r["steps"], 9, algo)
            self.assertEqual(r["cost"], 9, algo)

    def test_astar_expands_no_more_than_dijkstra(self):
        big = "S" + "." * 30 + "\n" + ("." * 31 + "\n") * 20 + "." * 30 + "G\n"
        a = gp.solve(big, "astar")
        d = gp.solve(big, "dijkstra")
        self.assertEqual(a["cost"], d["cost"])
        self.assertLess(a["expanded"], d["expanded"])

    def test_no_path(self):
        for algo in gp.ALGOS:
            r = gp.solve(WALLED, algo)
            self.assertFalse(r["found"])
            self.assertIsNone(r["cost"])

    def test_diagonal(self):
        r = gp.solve(OPEN, "astar", diag=True)
        self.assertEqual(r["steps"], 3)
        self.assertAlmostEqual(r["cost"], round(2 * math.sqrt(2) + 1, 4))

    def test_no_corner_cutting(self):
        m = "S#\n#G\n"
        self.assertFalse(gp.solve(m, "astar", diag=True)["found"])

    def test_path_is_contiguous_and_avoids_walls(self):
        maze = (
            "S.#.....\n"
            ".##.###.\n"
            "....#...\n"
            "###.#.#.\n"
            "......#G\n"
        )
        g = gp.Grid(maze)
        for algo in gp.ALGOS:
            r = gp.solve(maze, algo)
            path = [tuple(p) for p in r["path"]]
            self.assertEqual(path[0], g.start)
            self.assertEqual(path[-1], g.goal)
            for a, b in zip(path, path[1:]):
                self.assertEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1)
                self.assertTrue(g.passable(b))
        self.assertEqual(gp.solve(maze, "astar")["cost"], gp.solve(maze, "dijkstra")["cost"])

    def test_render_marks_path(self):
        out = gp.solve("S..G", "astar")["render"]
        self.assertEqual(out, "S**G")


class CliTests(unittest.TestCase):
    def run_cli(self, text, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write(text)
        try:
            buf, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                code = gp.main([f.name, *args])
            return code, buf.getvalue(), err.getvalue()
        finally:
            os.unlink(f.name)

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(OPEN)[0], 0)
        self.assertEqual(self.run_cli(WALLED)[0], 1)
        self.assertEqual(self.run_cli("...")[0], 2)

    def test_json_all(self):
        code, out, _ = self.run_cli(SWAMP, "--algo", "all", "--json")
        data = json.loads(out)
        self.assertEqual([d["algorithm"] for d in data], ["bfs", "dijkstra", "astar"])
        self.assertEqual(code, 0)

    def test_missing_file(self):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            self.assertEqual(gp.main(["/no/such/file.txt"]), 2)
        self.assertIn("error:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
