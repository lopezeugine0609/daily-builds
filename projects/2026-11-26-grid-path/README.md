# grid-path

Shortest paths on ASCII grid maps with **BFS**, **Dijkstra** and **A\***. Weighted terrain, optional 8-way moves, map rendering of the path, JSON output, exit codes. Python standard library only.

## Map format

| Char | Meaning |
|------|---------|
| `S` / `G` | start / goal (exactly one each) |
| `#` | wall |
| `.` | open, cost 1 |
| `1`-`9` | terrain, cost = digit |
| `~` | water, cost 5 |

Entering a cell costs that cell's cost. Ragged rows are padded with walls.
With `--diag`, diagonal steps cost `cost * sqrt(2)` and cannot cut a corner past a wall.

## How the algorithms differ

- **BFS**: fewest *steps*. Ignores terrain cost. Fine for unweighted mazes.
- **Dijkstra**: lowest *cost*. Expands nodes in order of distance from start.
- **A\***: lowest *cost*, like Dijkstra, but orders the frontier by `g + h`.
  `h` is Manhattan distance (4-way) or octile distance (8-way). Both are
  admissible because the minimum cell cost is 1, so A\* stays optimal.
  Ties on `f` are broken by smaller `h`, which cuts expansions on open maps.

## Usage

```
python grid_path.py MAP [-a {bfs,dijkstra,astar,all}] [-d] [--json] [-q]
```

`MAP` is a file or `-` for stdin. Exit codes: `0` path found, `1` no path, `2` bad map or file.

Compare all three on `maze.txt` (has a short route through two `9` cells and a longer cheap route):

```
$ python grid_path.py maze.txt --algo all
bfs: steps=25 cost=33 expanded=58
S..........#....
*#########.#.##.
*#*******#.#..#.
*#*#####*#.##.#.
***#...#*9....#.
####.#.#*######.
.....#..*******G

dijkstra: steps=31 cost=31 expanded=68
S**********#****
.#########*#*##*
.#.......#*#**#*
.#.#####.#*##*#*
...#...#.9****#*
####.#.#.######*
.....#...9.....G

astar: steps=31 cost=31 expanded=53
S**********#****
.#########*#*##*
.#.......#*#**#*
.#.#####.#*##*#*
...#...#.9****#*
####.#.#.######*
.....#...9.....G
```

BFS takes fewer steps but pays 33. Dijkstra and A\* find the cost-31 route; A\* expands 53 nodes vs 68.

Diagonal moves:

```
$ printf 'S.....\n..##..\n..#...\n.....G\n' | python grid_path.py - -d
astar: steps=7 cost=7.4142 expanded=11
S****.
..##.*
..#..*
.....G
```

No path:

```
$ printf 'S#G\n' | python grid_path.py -
astar: no path (expanded=1)
$ echo $?
1
```

`--json` prints `algorithm`, `diagonal`, `found`, `steps`, `cost`, `expanded`, `path` (list of `[row, col]`) and `render`.

## Tests

```
python -m unittest
```

```
Ran 15 tests in 0.022s

OK
```
