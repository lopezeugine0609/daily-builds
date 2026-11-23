# hexdump

xxd-style hex dumper in Node.js (standard library only) with a **reverse mode** that turns a dump back into bytes.

- Classic `offset: hex  ascii` dump with configurable bytes per line (`-c`) and grouping (`-g`)
- Skip/length windows (`-s`, `-l`) that keep real file offsets in the output
- Squeeze identical consecutive lines into `*` (`-a`)
- Plain hex (`-p`) and C array include (`-i`) output
- Reverse (`-r`): dump -> binary, honors offsets and expands `*` lines; `-r -p` decodes plain hex
- Exit codes: `0` ok, `1` input/parse error, `2` usage error

## Usage

```
node hexdump.js [options] [file|-]
```

Reads stdin when no file (or `-`) is given.

```
$ printf 'Hello, world!\n' > hello.txt
$ node hexdump.js hello.txt
00000000: 4865 6c6c 6f2c 2077 6f72 6c64 210a       Hello, world!.

$ node hexdump.js -i hello.txt
unsigned char hello_txt[] = {
  0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x2c, 0x20, 0x77, 0x6f, 0x72, 0x6c, 0x64,
  0x21, 0x0a
};
unsigned int hello_txt_len = 14;

$ node hexdump.js -p hello.txt
48656c6c6f2c20776f726c64210a

$ node hexdump.js -s 7 -l 5 -u hello.txt
00000007: 776F 726C 64                             world

$ node hexdump.js hello.txt | node hexdump.js -r
Hello, world!
```

Squeezing repeated lines (40 zero bytes followed by `END`):

```
$ node hexdump.js -a z.bin
00000000: 0000 0000 0000 0000 0000 0000 0000 0000  ................
*
00000020: 0000 0000 0000 0000 454e 44              ........END
```

Bad options exit with code 2:

```
$ node hexdump.js -x
hexdump: unknown option -x
usage: hexdump.js [options] [file|-]
...
```

### Patch a binary by hand

```
node hexdump.js app.bin > app.hex   # edit hex bytes in app.hex
node hexdump.js -r app.hex > app.patched.bin
```

Reverse mode reads only the hex column; the ASCII column is ignored, so editing hex alone is enough.

## Library

```js
const { dump, plain, cArray, reverse } = require('./hexdump.js');
dump(Buffer.from('hi'), { cols: 8, group: 1, upper: true }); // ['00000000: 68 69                    hi']
reverse(dump(buf).join('\n')).equals(buf);                   // true
```

## Tests

```
node --test
```

Real result: `tests 14`, `pass 14`, `fail 0`.
