# cron-next

Parse a standard 5-field cron expression and print when it will run next.
Handy for sanity-checking a crontab line before you deploy it. Standard library only.

## Supported syntax

`minute hour day-of-month month day-of-week`

- `*`, numbers, ranges `a-b`, lists `a,b,c`, steps `*/n`, `a-b/n`, `a/n`
- Month names `jan`–`dec`, weekday names `sun`–`sat`; `7` also means Sunday
- Macros: `@yearly` `@annually` `@monthly` `@weekly` `@daily` `@midnight` `@hourly`
- Vixie-cron day rule: if both day-of-month and day-of-week are restricted,
  a day matches when **either** one matches (`0 0 1 * mon` = the 1st *and* every Monday)

## Usage

```
python cron_next.py EXPR [-n COUNT] [--from "YYYY-MM-DD HH:MM"]
```

Real output:

```
$ python cron_next.py "*/15 9-17 * * mon-fri" -n 4 --from "2026-10-09 17:20"
2026-10-09 17:30  Fri
2026-10-09 17:45  Fri
2026-10-12 09:00  Mon
2026-10-12 09:15  Mon

$ python cron_next.py "0 12 29 2 *" -n 2 --from "2026-10-06 00:00"
2028-02-29 12:00  Tue
2032-02-29 12:00  Sun

$ python cron_next.py "0 25 * * *"
error: hour: 25 out of range 0-23
```

Invalid expressions exit with code 2. Schedules that can never run (e.g. `0 0 31 2 *`)
report an error after searching 30 years ahead.

As a library:

```python
from datetime import datetime
from cron_next import Cron
Cron("@hourly").next_after(datetime(2026, 1, 1, 10, 30))  # -> 2026-01-01 11:00
```

## Tests

```
python -m unittest -v
```

17 tests, all passing.
