#!/usr/bin/env node
'use strict';
/**
 * countdown-solver: solve the "Countdown" numbers game.
 *
 * Rules: combine some of the given positive integers with + - * / to hit a
 * target. Each number may be used at most once, and every intermediate result
 * must be a positive integer (no fractions, no zero, no negatives).
 *
 * Algorithm: exhaustive search over the multiset of available values. Each
 * value is an expression-tree node. At each step pick an unordered pair
 * (a, b), replace it with the node `a op b`, and recurse. Pruning:
 *   - only a >= b is considered, so + and * are tried once per pair and
 *     a - b / a / b never go negative or fractional;
 *   - x * 1 and x / 1 are skipped (they waste a number without changing x);
 *   - a - b === b and a / b === b are skipped (same as just keeping b);
 *   - in best-answer mode, a memo of visited states (sorted value:opcount
 *     pairs) avoids re-exploring states reached in a different order.
 * The best result is closest to the target, ties broken by fewest operations
 * inside that result's own tree (unused side computations do not count).
 */

const OPS = ['+', '-', '*', '/'];
const PREC = { '+': 1, '-': 1, '*': 2, '/': 2 };

function apply(op, a, b) {
  switch (op) {
    case '+': return a + b;
    case '-': return a - b > 0 && a - b !== b ? a - b : null;
    case '*': return b === 1 ? null : a * b;
    case '/': return b !== 1 && a % b === 0 && a / b !== b ? a / b : null;
    default: throw new Error(`bad op ${op}`);
  }
}

function leaf(n) {
  return { v: n, op: null, ops: 0, s: String(n), p: 3, kind: 'num', key: String(n), parts: null };
}

/** Build node `A op B`, with infix text, op count, and a canonical key. */
function combine(op, A, B, v) {
  const p = PREC[op];
  const left = A.p < p ? `(${A.s})` : A.s;
  // right side needs parens on equal precedence for - and /
  const right = B.p < p || (B.p === p && (op === '-' || op === '/')) ? `(${B.s})` : B.s;
  // Canonical key: flatten +/- (and * and /) chains into sorted positive and
  // negative term lists, so "5 * 4 * (6 - 1)" equals "(6 - 1) * 4 * 5".
  const kind = p === 1 ? 'add' : 'mul';
  const terms = (n) => (n.kind === kind ? n.parts : { pos: [n.key], neg: [] });
  const ta = terms(A), tb = terms(B);
  const flip = op === '-' || op === '/';
  const pos = [...ta.pos, ...(flip ? tb.neg : tb.pos)].sort();
  const neg = [...ta.neg, ...(flip ? tb.pos : tb.neg)].sort();
  const [ps, ns] = kind === 'add' ? ['+', '-'] : ['*', '/'];
  const key = `${kind}(${pos.join(ps)}${neg.length ? ns + neg.join(ns) : ''})`;
  return { v, op, a: A, b: B, ops: A.ops + B.ops + 1, s: `${left} ${op} ${right}`, p, kind, key, parts: { pos, neg } };
}

/** Post-order list of operations in a node's tree: [{a, op, b, result}]. */
function stepsOf(node, out = []) {
  if (node.op) {
    stepsOf(node.a, out);
    stepsOf(node.b, out);
    out.push({ a: node.a.v, op: node.op, b: node.b.v, result: node.v });
  }
  return out;
}

/**
 * Solve. Returns { value, diff, expression, steps, explored, solutions? }.
 * expression is null when an input number already is the best value.
 * With opts.all, solutions lists every distinct exact expression, shortest first.
 */
function solve(numbers, target, opts = {}) {
  if (!Array.isArray(numbers) || numbers.length === 0) throw new Error('need at least one number');
  for (const n of [...numbers, target]) {
    if (!Number.isSafeInteger(n) || n <= 0) throw new Error(`not a positive integer: ${n}`);
  }
  if (numbers.length > 7) throw new Error('at most 7 numbers (search is exponential)');
  let best = null;
  const exact = new Map(); // canonical key -> node
  const visited = new Set();
  let explored = 0;

  function consider(node) {
    const diff = Math.abs(node.v - target);
    if (!best || diff < best.diff || (diff === best.diff && node.ops < best.node.ops)) best = { diff, node };
    if (diff === 0 && opts.all && !exact.has(node.key)) exact.set(node.key, node);
  }

  function search(nodes) {
    explored++;
    if (!opts.all) {
      const key = nodes.map((n) => `${n.v}:${n.ops}`).sort().join(',');
      if (visited.has(key)) return;
      visited.add(key);
    }
    for (let i = 0; i < nodes.length; i++) {
      for (let j = 0; j < nodes.length; j++) {
        const A = nodes[i], B = nodes[j];
        if (i === j || A.v < B.v || (A.v === B.v && i > j)) continue;
        const rest = nodes.filter((_, k) => k !== i && k !== j);
        for (const op of OPS) {
          const r = apply(op, A.v, B.v);
          if (r === null || !Number.isSafeInteger(r)) continue;
          const node = combine(op, A, B, r);
          consider(node);
          if (rest.length > 0) search([...rest, node]);
        }
      }
    }
  }

  const leaves = numbers.map(leaf);
  leaves.forEach(consider);
  search(leaves);
  const n = best.node;
  const result = { value: n.v, diff: best.diff, expression: n.op ? n.s : null, steps: stepsOf(n), explored };
  if (opts.all) {
    result.solutions = [...exact.values()]
      .sort((x, y) => x.ops - y.ops || x.s.localeCompare(y.s))
      .map((x) => x.s);
  }
  return result;
}

function parseArgs(argv) {
  const opts = { all: false, json: false, limit: 10 };
  const nums = [];
  let target = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--all') opts.all = true;
    else if (a === '--json') opts.json = true;
    else if (a === '--limit') opts.limit = Number(argv[++i]);
    else if (a === '-t' || a === '--target') target = Number(argv[++i]);
    else if (a === '-h' || a === '--help') opts.help = true;
    else nums.push(Number(a));
  }
  if (target === null && nums.length > 1) target = nums.pop();
  return { opts, nums, target };
}

const USAGE = `usage: node countdown.js [--all] [--limit N] [--json] <n1> <n2> ... -t <target>
       node countdown.js 25 50 75 100 3 6 952      (last number is the target)
exit: 0 exact, 1 closest only, 2 usage error`;

function main(argv, log = console.log, err = console.error) {
  const { opts, nums, target } = parseArgs(argv);
  if (opts.help || target === null) { log(USAGE); return opts.help ? 0 : 2; }
  let res;
  try { res = solve(nums, target, { all: opts.all }); } catch (e) {
    err(`error: ${e.message}`);
    return 2;
  }
  const code = res.diff === 0 ? 0 : 1;
  if (opts.json) {
    log(JSON.stringify({ target, ...res }, null, 2));
    return code;
  }
  log(res.diff === 0 ? `exact: ${target}` : `closest: ${res.value} (off by ${res.diff})`);
  for (const s of res.steps) log(`  ${s.a} ${s.op} ${s.b} = ${s.result}`);
  log(`  => ${res.expression || res.value} = ${res.value}`);
  if (opts.all) {
    const shown = res.solutions.slice(0, opts.limit);
    log(`${res.solutions.length} distinct exact solution(s)` +
      (res.solutions.length > shown.length ? `, showing ${shown.length} shortest:` : ':'));
    for (const s of shown) log(`  ${s}`);
  }
  return code;
}

module.exports = { solve, apply, combine, leaf, stepsOf, parseArgs, main };

if (require.main === module) process.exitCode = main(process.argv.slice(2));
