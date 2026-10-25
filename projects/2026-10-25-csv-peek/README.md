# csv-peek

Preview a CSV file as an aligned table and profile every column, all in one command. It uses only the Python standard library.

- Sniffs the delimiter (`,` `;` tab `|`), or you can force one with `-d`.
- Infers a type for each column: `int`, `float`, `bool`, `date` (ISO), `string`, or `empty`. A column with both ints and floats becomes `float`. Any other mix becomes `string`.
- Treats `""`, `NA`, `N/A`, `null`, `none`, `nan` and `-` as nulls.
- Reports null count, distinct count, min/max (numeric, date, or lexical), mean for numeric columns, and the most common value.
- Right-aligns numeric columns, clips long cells with `…`, and pads ragged rows (extra columns become `col3`, and so on).
- Rejects `1_000`, `inf` and `nan` as numbers, although Python's `int()`/`float()` accept them.

## Usage

```
python csv_peek.py FILE|- [-n ROWS] [-d DELIM] [-w WIDTH] [--no-stats] [--json]
```

```
$ python csv_peek.py sample.csv -n 3 -w 12
6 rows x 6 columns, delimiter ','

order_id | customer  | amount  | paid | ordered_on | note
---------+-----------+---------+------+------------+-------------
    1001 | Ana Reyes | 1250.50 | yes  | 2026-10-01 | rush, gift …
    1002 | Ben Cruz  |      89 | no   | 2026-10-02 |
    1003 | Ana Reyes |  430.25 | yes  | 2026-10-03 | repeat buyer
... 3 more rows

column     | type   | nulls | distinct | min            | max         | mean    | top
-----------+--------+-------+----------+----------------+-------------+---------+---------------------
order_id   | int    | 0     | 6        | 1001           | 1006        | 1003.5  | 1001 (x1)
customer   | string | 0     | 4        | Ana Reyes      | Dina Lim    |         | Ana Reyes (x2)
amount     | float  | 1     | 5        | 15.0           | 2999.99     | 956.948 | 1250.50 (x1)
paid       | bool   | 0     | 2        |                |             |         | yes (x4)
ordered_on | date   | 0     | 6        | 2026-10-01     | 2026-10-09  |         | 2026-10-01 (x1)
note       | string | 2     | 4        | awaiting quote | sample pack |         | rush, gift wrap (x1)
```

Read from stdin with a sniffed delimiter:

```
$ printf 'a;b\n1;x\n2;y\n' | python csv_peek.py - --no-stats
2 rows x 2 columns, delimiter ';'

a | b
--+--
1 | x
2 | y
```

`--json` prints `{"rows", "columns", "delimiter", "profile": [...]}`. Each profile entry has `column`, `type`, `nulls`, `distinct`, `min`, `max`, `mean`, `top` and `top_count`. Fields that do not apply are left out.

Exit codes: `0` ok, `1` empty input, `2` file cannot be read.

## Tests

```
$ python -m unittest
...........
----------------------------------------------------------------------
Ran 11 tests in 0.017s

OK
```
