#!/usr/bin/env node
'use strict';
/**
 * sudoku-solver: solve 9x9 Sudoku puzzles using bitmask candidates,
 * constraint propagation (naked + hidden singles) and MRV backtracking.
 * Also counts solutions (to check uniqueness) and validates grids.
 */

const ALL = 0x1ff; // bits 0..8 => digits 1..9

// Precompute the 27 units and the 20 peers for each cell.
const UNITS = [];
for (let i = 0; i < 9; i++) {
  UNITS.push([...Array(9)].map((_, j) => i * 9 + j)); // row
  UNITS.push([...Array(9)].map((_, j) => j * 9 + i)); // column
  const br = Math.floor(i / 3) * 3, bc = (i % 3) * 3;
  UNITS.push([...Array(9)].map((_, j) => (br + Math.floor(j / 3)) * 9 + bc + (j % 3))); // box
}
const CELL_UNITS = [...Array(81)].map((_, c) => UNITS.filter((u) => u.includes(c)));
const PEERS = [...Array(81)].map((_, c) => {
  const s = new Set();
  for (const u of CELL_UNITS[c]) for (const p of u) if (p !== c) s.add(p);
  return [...s];
});

const popcount = (m) => { let n = 0; while (m) { m &= m - 1; n++; } return n; };
const bitToDigit = (b) => 31 - Math.clz32(b) + 1;

/** Parse 81 chars of digits; '0', '.', '_' mean empty. Whitespace/'|'/'-'/'+' ignored. */
function parse(text) {
  const chars = String(text).replace(/[\s|+\-]/g, '');
  if (chars.length !== 81) throw new Error(`expected 81 cells, got ${chars.length}`);
  return [...chars].map((ch, i) => {
    if (ch === '.' || ch === '0' || ch === '_') return 0;
    if (/[1-9]/.test(ch)) return Number(ch);
    throw new Error(`invalid character '${ch}' at cell ${i}`);
  });
}

/** True if no digit repeats in any row, column or box (empty cells allowed). */
function isValid(grid) {
  for (const u of UNITS) {
    let seen = 0;
    for (const c of u) {
      const v = grid[c];
      if (!v) continue;
      const bit = 1 << (v - 1);
      if (seen & bit) return false;
      seen |= bit;
    }
  }
  return true;
}

/** Remove digit bit from cell c; propagate. Returns false on contradiction. */
function eliminate(cand, c, bit, stats) {
  if (!(cand[c] & bit)) return true;
  cand[c] &= ~bit;
  const m = cand[c];
  if (m === 0) return false;
  // Naked single: one candidate left -> remove it from peers.
  if ((m & (m - 1)) === 0) {
    for (const p of PEERS[c]) if (!eliminate(cand, p, m, stats)) return false;
  }
  // Hidden single: the removed digit has one place left in a unit.
  for (const u of CELL_UNITS[c]) {
    let spot = -1, count = 0;
    for (const x of u) if (cand[x] & bit) { count++; spot = x; if (count > 1) break; }
    if (count === 0) return false;
    if (count === 1 && cand[spot] !== bit) {
      if (!assign(cand, spot, bit, stats)) return false;
    }
  }
  return true;
}

function assign(cand, c, bit, stats) {
  let others = cand[c] & ~bit;
  while (others) {
    const b = others & -others;
    others &= others - 1;
    if (!eliminate(cand, c, b, stats)) return false;
  }
  return true;
}

function initCandidates(grid, stats) {
  if (!isValid(grid)) return null;
  const cand = new Array(81).fill(ALL);
  for (let c = 0; c < 81; c++) {
    if (grid[c] && !assign(cand, c, 1 << (grid[c] - 1), stats)) return null;
  }
  return cand;
}

/** Depth-first search; calls onSolution(cand) for each solution until it returns true. */
function search(cand, stats, onSolution) {
  let best = -1, bestCount = 10;
  for (let c = 0; c < 81; c++) {
    const n = popcount(cand[c]);
    if (n > 1 && n < bestCount) { best = c; bestCount = n; if (n === 2) break; }
  }
  if (best === -1) return onSolution(cand);
  let m = cand[best];
  while (m) {
    const b = m & -m;
    m &= m - 1;
    stats.guesses++;
    const copy = cand.slice();
    if (assign(copy, best, b, stats) && search(copy, stats, onSolution)) return true;
  }
  return false;
}

const toGrid = (cand) => cand.map(bitToDigit);

/** Solve; returns { solution: number[81] | null, guesses }. */
function solve(input) {
  const grid = Array.isArray(input) ? input : parse(input);
  const stats = { guesses: 0 };
  const cand = initCandidates(grid, stats);
  let solution = null;
  if (cand) search(cand, stats, (s) => { solution = toGrid(s); return true; });
  return { solution, guesses: stats.guesses };
}

/** Count solutions, stopping at `limit` (default 2 is enough to test uniqueness). */
function countSolutions(input, limit = 2) {
  const grid = Array.isArray(input) ? input : parse(input);
  const stats = { guesses: 0 };
  const cand = initCandidates(grid, stats);
  if (!cand) return 0;
  let n = 0;
  search(cand, stats, () => ++n >= limit);
  return n;
}

function format(grid) {
  const lines = [];
  for (let r = 0; r < 9; r++) {
    if (r && r % 3 === 0) lines.push('------+-------+------');
    const row = grid.slice(r * 9, r * 9 + 9).map((v) => (v ? String(v) : '.'));
    lines.push(`${row.slice(0, 3).join(' ')} | ${row.slice(3, 6).join(' ')} | ${row.slice(6).join(' ')}`);
  }
  return lines.join('\n');
}

function main(argv) {
  const args = argv.slice(2);
  const flags = new Set(args.filter((a) => a.startsWith('--')));
  const pos = args.filter((a) => !a.startsWith('--'));
  if (flags.has('--help') || (pos.length === 0 && process.stdin.isTTY)) {
    console.log('usage: node sudoku.js [--line] [--count] <81-char puzzle | file | ->');
    return 0;
  }
  const fs = require('fs');
  let text;
  if (pos.length === 0 || pos[0] === '-') text = fs.readFileSync(0, 'utf8');
  else if (fs.existsSync(pos[0])) text = fs.readFileSync(pos[0], 'utf8');
  else text = pos[0];

  const puzzles = [];
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter((l) => l && !l.startsWith('#'));
  // One puzzle per line if every line is 81 chars; otherwise treat whole text as one grid.
  if (lines.length > 1 && lines.every((l) => l.replace(/\s/g, '').length === 81)) puzzles.push(...lines);
  else puzzles.push(lines.join(''));

  let failed = 0;
  for (const p of puzzles) {
    let grid;
    try { grid = parse(p); } catch (e) { console.error(`error: ${e.message}`); failed++; continue; }
    if (flags.has('--count')) {
      const n = countSolutions(grid, 2);
      console.log(n === 0 ? 'no solution' : n === 1 ? 'unique solution' : 'multiple solutions');
      if (n === 0) failed++;
      continue;
    }
    const t0 = process.hrtime.bigint();
    const { solution, guesses } = solve(grid);
    const ms = Number(process.hrtime.bigint() - t0) / 1e6;
    if (!solution) { console.log('no solution'); failed++; continue; }
    if (flags.has('--line')) console.log(solution.join(''));
    else console.log(`${format(solution)}\n(${guesses} guesses, ${ms.toFixed(1)} ms)\n`);
  }
  return failed ? 1 : 0;
}

module.exports = { parse, isValid, solve, countSolutions, format, UNITS, PEERS };

if (require.main === module) process.exitCode = main(process.argv);
