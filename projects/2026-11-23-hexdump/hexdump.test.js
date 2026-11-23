'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { dump, plain, cArray, reverse, main } = require('./hexdump.js');

function run(args, stdin = Buffer.alloc(0)) {
  const out = []; const err = [];
  const io = {
    stdout: { write: (s) => out.push(Buffer.from(s)) },
    stderr: { write: (s) => err.push(String(s)) },
    readStdin: () => stdin,
  };
  const code = main(args, io);
  return { code, out: Buffer.concat(out), err: err.join('') };
}

test('dump formats offset, grouped hex, and ascii', () => {
  const lines = dump(Buffer.from('Hello, world!\n'));
  assert.deepEqual(lines, ['00000000: 4865 6c6c 6f2c 2077 6f72 6c64 210a       Hello, world!.']);
});

test('dump pads short last line so ascii column aligns', () => {
  const lines = dump(Buffer.from('abcdefghijklmnopqr'));
  assert.equal(lines.length, 2);
  assert.equal(lines[0].indexOf('abcd'), lines[1].indexOf('qr'));
});

test('group 0, custom cols, uppercase, base offset', () => {
  const lines = dump(Buffer.from([0xde, 0xad, 0xbe, 0xef]), { cols: 4, group: 0, upper: true, offset: 0xff0 });
  assert.deepEqual(lines, ['00000FF0: DEADBEEF  ....']);
});

test('squeeze collapses repeated lines but keeps last', () => {
  const buf = Buffer.alloc(64, 0);
  const lines = dump(buf, { squeeze: true });
  assert.equal(lines[1], '*');
  assert.equal(lines.length, 3);
  assert.ok(lines[2].startsWith('00000030:'));
});

test('invalid cols rejected', () => {
  assert.throws(() => dump(Buffer.from('x'), { cols: 0 }), RangeError);
});

test('plain wraps hex', () => {
  assert.deepEqual(plain(Buffer.from('abcd'), 2), ['6162', '6364']);
});

test('cArray output and identifier sanitizing', () => {
  const lines = cArray(Buffer.from([1, 2, 3]), '1-file.bin', 2);
  assert.deepEqual(lines, [
    'unsigned char _1_file_bin[] = {', '  0x01, 0x02,', '  0x03', '};', 'unsigned int _1_file_bin_len = 3;',
  ]);
});

test('reverse round-trips random data with any layout', () => {
  const buf = Buffer.from(Array.from({ length: 300 }, (_, i) => (i * 37 + 11) & 0xff));
  for (const opts of [{}, { cols: 7, group: 3 }, { group: 0, upper: true }, { cols: 1 }]) {
    assert.ok(reverse(dump(buf, opts).join('\n')).equals(buf), JSON.stringify(opts));
  }
});

test('reverse expands squeezed lines', () => {
  const buf = Buffer.concat([Buffer.alloc(80, 0x41), Buffer.from('end')]);
  const text = dump(buf, { squeeze: true }).join('\n');
  assert.ok(text.includes('*'));
  assert.ok(reverse(text).equals(buf));
});

test('reverse ascii column with double spaces is ignored', () => {
  const buf = Buffer.from('a  b  c  d');
  assert.ok(reverse(dump(buf).join('\n')).equals(buf));
});

test('reverse plain hex and errors', () => {
  assert.equal(reverse('48 69\n0a', { plainHex: true }).toString(), 'Hi\n');
  assert.throws(() => reverse('abc', { plainHex: true }), /odd/);
  assert.throws(() => reverse('zz', { plainHex: true }), /invalid/);
  assert.throws(() => reverse('not a dump'), /line 1/);
});

test('CLI: skip/length window keeps real offsets', () => {
  const r = run(['-s', '0x10', '-l', '4', '-g', '0'], Buffer.from('0123456789abcdefWXYZtail'));
  assert.equal(r.code, 0);
  assert.equal(r.out.toString(), '00000010: 5758595a                          WXYZ\n');
});

test('CLI: file input, -i, -r roundtrip via files', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'hexdump-'));
  const f = path.join(dir, 'x.bin');
  fs.writeFileSync(f, Buffer.from([0, 255, 10]));
  const c = run(['-i', f]);
  assert.match(c.out.toString(), /unsigned char x_bin\[\] = \{\n {2}0x00, 0xff, 0x0a\n\};/);
  const d = run([f]);
  const back = run(['-r'], d.out);
  assert.deepEqual([...back.out], [0, 255, 10]);
  const p = run(['-p', f]);
  assert.equal(p.out.toString(), '00ff0a\n');
  assert.deepEqual([...run(['-r', '-p'], p.out).out], [0, 255, 10]);
  fs.rmSync(dir, { recursive: true });
});

test('CLI: exit codes', () => {
  assert.equal(run(['--bogus']).code, 2);
  assert.equal(run(['-c']).code, 2);
  assert.equal(run(['-s', '-3']).code, 2);
  assert.equal(run(['/no/such/file/here']).code, 1);
  assert.equal(run(['-r'], Buffer.from('garbage')).code, 1);
  assert.equal(run(['-h']).code, 0);
});
