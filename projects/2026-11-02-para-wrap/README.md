# para-wrap

Optimal (minimum-raggedness) paragraph wrapper in pure Python.

Greedy wrapping, which `textwrap` and most editors use, puts as many words on each line as will fit. It is fast, but it can leave one short line in the middle of a paragraph. `para-wrap` uses dynamic programming to choose the break points that minimise total **raggedness**:

```
badness(line) = (width - line_length) ** 2   for every line except the last
badness(last) = 0
```

Squaring the slack makes one big gap cost more than several small ones, so the right margin comes out more even. This is the core of Knuth-Plass line breaking (TeX), without hyphenation or stretchable glue.

## Algorithm

`best[i]` = the minimum cost of laying out `words[i:]`. Work backwards from `best[n] = 0`. For each `i`, try every `j` where `words[i:j]` fits on one line:

```
best[i] = min over j of  cost(i, j) + best[j]
```

The inner loop stops when the line overflows. A line holds at most about `width/2` words, so the run time is **O(n · width)**. A word longer than `width` goes on a line by itself.

Classic counter-example, width 6, words `aaa bb cc ddddd`:

| greedy | slack² | optimal | slack² |
|---|---|---|---|
| `aaa bb` | 0 | `aaa` | 9 |
| `cc` | 16 | `bb cc` | 1 |
| `ddddd` | (last) | `ddddd` | (last) |
| **total** | **16** | | **10** |

## Usage

```
python para_wrap.py [file] [-w WIDTH] [-m optimal|greedy]
                    [-a left|right|center|justify] [--compare] [--json]
```

Reads stdin if no file is given. Blank lines separate paragraphs.

### Compare greedy and optimal (real output, `sample.txt`)

```
$ python para_wrap.py sample.txt -w 28 --compare
== greedy (raggedness 100) ==
----------------------------|
Greedy line breaking fills
each line with as many words
as will fit, which is fast
but can leave an awkward
short line in the middle of
a paragraph. Optimal
breaking looks at the whole
paragraph at once.

Dynamic programming makes
this cheap: every suffix of
the paragraph is solved once
and reused.

== optimal (raggedness 76) ==
----------------------------|
Greedy line breaking fills
each line with as many words
as will fit, which is fast
but can leave an awkward
short line in the middle
of a paragraph. Optimal
breaking looks at the whole
paragraph at once.

Dynamic programming makes
this cheap: every suffix of
the paragraph is solved once
and reused.

optimal is 24.0% less ragged
```

### Justify

```
$ python para_wrap.py sample.txt -w 28 -a justify
Greedy  line  breaking fills
each line with as many words
as  will  fit, which is fast
but  can  leave  an  awkward
short  line  in  the  middle
of   a   paragraph.  Optimal
breaking  looks at the whole
paragraph at once.

Dynamic   programming  makes
this  cheap: every suffix of
the paragraph is solved once
and reused.
```

### JSON

```
$ echo "aaa bb cc ddddd" | python para_wrap.py -w 6 --json
{
  "width": 6,
  "method": "optimal",
  "raggedness": 10,
  "text": "aaa\nbb cc\nddddd"
}
```

### As a library

```python
from para_wrap import wrap_text
text, score = wrap_text(open("notes.txt").read(), width=60, mode="justify")
```

## Tests

```
python -m unittest -v
```

There are 13 tests. They cover the classic counter-example and the rule that no line exceeds the width. They check that overlong words go on their own line and that justify, right and center alignment work. The CLI tests cover JSON output and `--compare`. One test checks the DP against a **brute-force search over every possible break set** for many small inputs. Another checks that optimal is never worse than greedy.
