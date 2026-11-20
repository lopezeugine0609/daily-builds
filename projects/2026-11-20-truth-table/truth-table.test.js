'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const tt = require('./truth-table.js');

const val = (src, env) => tt.evaluate(tt.parse(src), env);

test('operator aliases evaluate the same', () => {
  for (const [a, b] of [[1, 1], [1, 0], [0, 1], [0, 0]]) {
    const env = { a: !!a, b: !!b };
    assert.equal(val('a & b', env), val('a and b', env));
    assert.equal(val('a && b', env), val('a * b', env));
    assert.equal(val('a | b', env), val('a OR b', env));
    assert.equal(val('a -> b', env), !env.a || env.b);
    assert.equal(val('a <-> b', env), env.a === env.b);
    assert.equal(val('a ^ b', env), env.a !== env.b);
    assert.equal(val('!a', env), val('not a', env));
  }
});

test('precedence: not > and > xor > or > imp > iff', () => {
  const ast = tt.parse('a | b & c');
  assert.equal(ast.op, 'or');
  assert.equal(ast.b.op, 'and');
  assert.equal(tt.parse('!a & b').op, 'and');
  assert.equal(tt.parse('a -> b <-> c').op, 'iff');
  assert.equal(tt.parse('a ^ b | c').op, 'or');
});

test('implication is right-associative', () => {
  const ast = tt.parse('a -> b -> c');
  assert.equal(ast.op, 'imp');
  assert.equal(ast.a.op, 'var');
  assert.equal(ast.b.op, 'imp');
  // a=1,b=0,c=0: right-assoc gives 1 -> (0 -> 0) = 1; left-assoc would give 0.
  assert.equal(val('a -> b -> c', { a: true, b: false, c: false }), true);
});

test('constants', () => {
  assert.equal(val('1 & true', {}), true);
  assert.equal(val('0 | false', {}), false);
});

test('parse errors', () => {
  assert.throws(() => tt.parse(''), /empty/);
  assert.throws(() => tt.parse('(a & b'), /missing '\)'/);
  assert.throws(() => tt.parse('a & '), /end of expression/);
  assert.throws(() => tt.parse('a b'), /unexpected token/);
  assert.throws(() => tt.parse('a $ b'), /unexpected character/);
});

test('truth table order and variables', () => {
  const t = tt.truthTable(tt.parse('b & a'));
  assert.deepEqual(t.vars, ['a', 'b']);
  assert.deepEqual(t.rows.map(r => r.value), [false, false, false, true]);
  assert.deepEqual(t.rows[2].env, { a: true, b: false });
});

test('classify', () => {
  const cls = s => tt.classify(tt.truthTable(tt.parse(s)).rows);
  assert.equal(cls('p | !p'), 'tautology');
  assert.equal(cls('p & !p'), 'contradiction');
  assert.equal(cls('p -> q'), 'contingent');
  assert.equal(cls('((p -> q) & (q -> r)) -> (p -> r)'), 'tautology');
});

test('equivalence: De Morgan holds, wrong version gives counterexample', () => {
  assert.equal(tt.equivalent(tt.parse('!(a & b)'), tt.parse('!a | !b')).equivalent, true);
  const r = tt.equivalent(tt.parse('!(a & b)'), tt.parse('!a & !b'));
  assert.equal(r.equivalent, false);
  assert.deepEqual(r.counterexample, { a: false, b: true });
  assert.equal(r.left, true);
  assert.equal(r.right, false);
});

test('prime implicants of classic example', () => {
  // f(a,b,c,d) = m(4,8,10,11,12,15): verified by hand, 5 prime implicants.
  const primes = tt.primeImplicants([4, 8, 10, 11, 12, 15], 4);
  assert.deepEqual(primes, ['-100', '1-00', '1-11', '10-0', '101-']);
});

test('minimize gives a minimal equivalent SOP', () => {
  const cases = [
    ['a & b | a & !b', 'a'],
    ['a | !a', '1'],
    ['a & !a', '0'],
    ['a ^ b', '(a & !b) | (!a & b)'],
    ['(a & b) | (a & c) | (b & c)', '(a & b) | (a & c) | (b & c)'],
  ];
  for (const [src, want] of cases) {
    const ast = tt.parse(src);
    const t = tt.truthTable(ast);
    const ms = t.rows.filter(r => r.value).map(r => r.index);
    const got = tt.sop(tt.minimize(ms, t.vars.length), t.vars);
    assert.equal(got, want, src);
  }
});

test('minimized form is equivalent for random functions', () => {
  let seed = 12345;
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  const vars = ['a', 'b', 'c', 'd'];
  for (let k = 0; k < 40; k++) {
    const ms = [];
    for (let i = 0; i < 16; i++) if (rnd() < 0.5) ms.push(i);
    const expr = tt.sop(tt.minimize(ms, 4), vars);
    // Force all four vars so row indices line up.
    const ast = tt.parse(`(${expr}) | (a & !a & b & c & d)`);
    const got = tt.truthTable(ast, vars).rows.filter(r => r.value).map(r => r.index);
    assert.deepEqual(got, ms, `minterms ${ms} -> ${expr}`);
  }
});

test('main exit codes', () => {
  const log = console.log, err = console.error;
  console.log = () => {}; console.error = () => {};
  try {
    assert.equal(tt.main(['node', 'x', 'a & b']), 0);
    assert.equal(tt.main(['node', 'x', 'a & b', '--equiv', 'b & a']), 0);
    assert.equal(tt.main(['node', 'x', 'a & b', '--equiv', 'a | b']), 1);
    assert.equal(tt.main(['node', 'x', 'a &']), 2);
    assert.equal(tt.main(['node', 'x']), 2);
  } finally { console.log = log; console.error = err; }
});
