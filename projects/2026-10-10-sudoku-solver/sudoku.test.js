'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { parse, isValid, solve, countSolutions, format, UNITS, PEERS } = require('./sudoku');

const EASY = '003020600900305001001806400008102900700000008006708200002609500800203009005010300';
const EASY_SOL = '483921657967345821251876493548132976729564138136798245372689514814253769695417382';
const HARD = '8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..';
const HARD_SOL = '812753649943682175675491283154237896369845721287169534521974368438526917796318452';

const solvedOK = (puzzle, sol) => {
  for (let i = 0; i < 81; i++) if (puzzle[i] && puzzle[i] !== sol[i]) return false;
  return isValid(sol) && sol.every((v) => v >= 1 && v <= 9);
};

test('units and peers are built correctly', () => {
  assert.equal(UNITS.length, 27);
  for (const u of UNITS) assert.equal(new Set(u).size, 9);
  for (const p of PEERS) assert.equal(p.length, 20);
});

test('parse accepts dots, zeros and pretty grids', () => {
  assert.deepEqual(parse(EASY), parse(EASY.replace(/0/g, '.')));
  const pretty = format(parse(EASY));
  assert.deepEqual(parse(pretty), parse(EASY));
});

test('parse rejects bad input', () => {
  assert.throws(() => parse('123'), /expected 81 cells/);
  assert.throws(() => parse('x'.repeat(81)), /invalid character 'x'/);
});

test('isValid detects duplicates', () => {
  assert.equal(isValid(parse(EASY)), true);
  const bad = parse(EASY);
  bad[0] = 3; // row 0 already has a 3 at index 2
  assert.equal(isValid(bad), false);
});

test('solves an easy puzzle by propagation alone', () => {
  const { solution, guesses } = solve(EASY);
  assert.equal(solution.join(''), EASY_SOL);
  assert.equal(guesses, 0);
});

test('solves a hard puzzle that needs search', () => {
  const { solution, guesses } = solve(HARD);
  assert.equal(solution.join(''), HARD_SOL);
  assert.ok(guesses > 0);
  assert.ok(solvedOK(parse(HARD), solution));
});

test('solves an empty grid', () => {
  const { solution } = solve('.'.repeat(81));
  assert.ok(solvedOK(new Array(81).fill(0), solution));
});

test('returns null for contradictory puzzles', () => {
  const dup = '11' + '.'.repeat(79);
  assert.equal(solve(dup).solution, null);
  // Valid-looking givens but cell 0 has no candidate: row has 1-8, column has 9.
  const blocked = '.12345678' + '9' + '.'.repeat(71);
  assert.equal(solve(blocked).solution, null);
  assert.equal(countSolutions(blocked), 0);
});

test('countSolutions distinguishes unique and multiple', () => {
  assert.equal(countSolutions(HARD), 1);
  assert.equal(countSolutions('.'.repeat(81)), 2);
  assert.equal(countSolutions('.'.repeat(81), 5), 5);
});
