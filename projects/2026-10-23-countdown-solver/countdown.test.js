'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { solve, apply, combine, leaf, stepsOf, parseArgs, main } = require('./countdown.js');

// Evaluate an infix expression made of integers, + - * / and parentheses
// (independent check of the solver's printed expression).
function evaluate(expr) {
  const toks = expr.match(/\d+|[-+*/()]/g);
  let i = 0;
  const primary = () => {
    const t = toks[i++];
    if (t === '(') { const v = sum(); i++; return v; }
    return Number(t);
  };
  const prod = () => {
    let v = primary();
    while (toks[i] === '*' || toks[i] === '/') v = toks[i++] === '*' ? v * primary() : v / primary();
    return v;
  };
  const sum = () => {
    let v = prod();
    while (toks[i] === '+' || toks[i] === '-') v = toks[i++] === '+' ? v + prod() : v - prod();
    return v;
  };
  return sum();
}

function usedNumbers(expr) {
  return expr.match(/\d+/g).map(Number).sort((a, b) => a - b);
}

function isSubMultiset(sub, all) {
  const pool = [...all];
  return sub.every((n) => { const k = pool.indexOf(n); if (k < 0) return false; pool.splice(k, 1); return true; });
}

test('apply enforces positive-integer rules and pruning', () => {
  assert.equal(apply('+', 3, 4), 7);
  assert.equal(apply('-', 9, 4), 5);
  assert.equal(apply('-', 4, 4), null); // zero
  assert.equal(apply('-', 8, 4), null); // result equals b: redundant
  assert.equal(apply('*', 7, 1), null); // x * 1 wastes a number
  assert.equal(apply('/', 9, 2), null); // fractional
  assert.equal(apply('/', 12, 3), 4);
  assert.equal(apply('/', 9, 3), null); // result equals b: redundant
});

test('classic 952 puzzle is solved exactly and the expression checks out', () => {
  const nums = [25, 50, 75, 100, 3, 6];
  const r = solve(nums, 952);
  assert.equal(r.diff, 0);
  assert.equal(r.value, 952);
  assert.equal(evaluate(r.expression), 952);
  assert.ok(isSubMultiset(usedNumbers(r.expression), nums));
  assert.equal(r.steps.length, 5);
});

test('every step yields a positive integer and chains to the result', () => {
  const r = solve([1, 3, 7, 10, 25, 50], 765);
  assert.equal(r.diff, 0);
  for (const s of r.steps) {
    assert.ok(Number.isInteger(s.result) && s.result > 0);
    assert.equal(apply(s.op, s.a, s.b), s.result);
  }
  assert.equal(r.steps.at(-1).result, 765);
});

test('prefers the fewest operations', () => {
  const r = solve([2, 3, 50, 7, 9, 1], 100);
  assert.equal(r.expression, '50 * 2');
  assert.equal(r.steps.length, 1);
});

test('target already present needs no operations', () => {
  const r = solve([5, 10, 25], 25);
  assert.equal(r.diff, 0);
  assert.equal(r.expression, null);
  assert.deepEqual(r.steps, []);
});

test('unreachable target returns the closest value', () => {
  const r = solve([1, 2, 3], 1000);
  assert.equal(r.value, 9);
  assert.equal(r.diff, 991);
  assert.equal(evaluate(r.expression), 9);
});

test('duplicate input values are each used at most once', () => {
  const r = solve([4, 4], 16);
  assert.equal(r.expression, '4 * 4');
  const r2 = solve([4, 4], 64);
  assert.equal(r2.value, 16); // cannot reuse a 4
});

test('--all returns distinct, valid solutions, shortest first', () => {
  const nums = [1, 2, 3, 4, 5, 6];
  const r = solve(nums, 100, { all: true });
  assert.ok(r.solutions.length > 10);
  assert.equal(new Set(r.solutions).size, r.solutions.length);
  for (const s of r.solutions) {
    assert.equal(evaluate(s), 100, s);
    assert.ok(isSubMultiset(usedNumbers(s), nums), s);
  }
  const opCount = (s) => s.match(/[-+*/]/g).length;
  for (let i = 1; i < r.solutions.length; i++) {
    assert.ok(opCount(r.solutions[i - 1]) <= opCount(r.solutions[i]));
  }
});

test('canonical key merges commutative/associative rearrangements', () => {
  const [a, b, c] = [5, 4, 6].map(leaf);
  const one = leaf(1);
  const x = combine('*', combine('*', a, b, 20), combine('-', c, one, 5), 100);
  const y = combine('*', combine('*', combine('-', c, one, 5), b, 20), a, 100);
  assert.notEqual(x.s, y.s);
  assert.equal(x.key, y.key);
  const z = combine('*', combine('+', a, b, 9), c, 54);
  assert.notEqual(z.key, combine('+', a, combine('*', b, c, 24), 29).key);
});

test('stepsOf lists operations in evaluation order', () => {
  const n = combine('-', combine('*', leaf(10), leaf(10), 100), leaf(1), 99);
  assert.deepEqual(stepsOf(n), [
    { a: 10, op: '*', b: 10, result: 100 },
    { a: 100, op: '-', b: 1, result: 99 },
  ]);
});

test('input validation', () => {
  assert.throws(() => solve([], 10), /at least one/);
  assert.throws(() => solve([1, 0], 10), /positive integer/);
  assert.throws(() => solve([1, 2], 1.5), /positive integer/);
  assert.throws(() => solve([1, 2, 3, 4, 5, 6, 7, 8], 10), /at most 7/);
});

test('parseArgs: trailing target or -t flag', () => {
  assert.deepEqual(parseArgs(['1', '2', '3']).nums, [1, 2]);
  assert.equal(parseArgs(['1', '2', '3']).target, 3);
  const p = parseArgs(['--all', '-t', '50', '10', '5', '--limit', '3']);
  assert.equal(p.target, 50);
  assert.deepEqual(p.nums, [10, 5]);
  assert.equal(p.opts.all, true);
  assert.equal(p.opts.limit, 3);
});

test('main exit codes and output', () => {
  const lines = [];
  const log = (s) => lines.push(s);
  assert.equal(main(['25', '50', '75', '100', '3', '6', '952'], log), 0);
  assert.equal(lines[0], 'exact: 952');
  lines.length = 0;
  assert.equal(main(['1', '2', '3', '1000'], log), 1);
  assert.equal(lines[0], 'closest: 9 (off by 991)');
  const errs = [];
  assert.equal(main(['1', '-5', '10'], log, (s) => errs.push(s)), 2);
  assert.match(errs[0], /positive integer/);
  lines.length = 0;
  assert.equal(main(['--json', '2', '3', '6'], log), 0);
  const j = JSON.parse(lines.join('\n'));
  assert.equal(j.expression, '3 * 2');
  assert.equal(j.target, 6);
});
