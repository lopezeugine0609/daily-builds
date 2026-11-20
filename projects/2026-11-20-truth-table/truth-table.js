#!/usr/bin/env node
'use strict';
// truth-table: boolean expression parser, truth tables, classification,
// equivalence checking and Quine-McCluskey minimization. No dependencies.

const OPS = {
  '!': 'not', '~': 'not', not: 'not',
  '&': 'and', '&&': 'and', and: 'and', '*': 'and',
  '|': 'or', '||': 'or', or: 'or', '+': 'or',
  '^': 'xor', xor: 'xor',
  '->': 'imp', '=>': 'imp', implies: 'imp',
  '<->': 'iff', '<=>': 'iff', iff: 'iff', '==': 'iff',
};

function tokenize(src) {
  const toks = [];
  const re = /\s*(<->|<=>|->|=>|&&|\|\||==|[!~&|^*+()]|[A-Za-z_][A-Za-z0-9_]*|[01])/y;
  let i = 0;
  while (i < src.length) {
    if (/^\s*$/.test(src.slice(i))) break;
    re.lastIndex = i;
    const m = re.exec(src);
    if (!m) throw new SyntaxError(`unexpected character at ${i}: '${src.slice(i).trim()[0]}'`);
    const t = m[1];
    const low = t.toLowerCase();
    if (OPS[low] && /^[a-z]+$/.test(low) || OPS[t]) toks.push({ type: 'op', op: OPS[low] || OPS[t], pos: i });
    else if (t === '(' || t === ')') toks.push({ type: t, pos: i });
    else if (t === '0' || t === '1' || low === 'true' || low === 'false')
      toks.push({ type: 'const', value: t === '1' || low === 'true', pos: i });
    else toks.push({ type: 'var', name: t, pos: i });
    i = re.lastIndex;
  }
  return toks;
}

// Precedence climbing. Lowest to highest: iff, imp (right-assoc), or, xor, and, not.
const BIN = [['iff'], ['imp'], ['or'], ['xor'], ['and']];

function parse(src) {
  const toks = tokenize(src);
  let p = 0;
  const peek = () => toks[p];
  const isOp = (t, op) => t && t.type === 'op' && t.op === op;

  function level(n) {
    if (n === BIN.length) return unary();
    const op = BIN[n][0];
    let left = level(n + 1);
    if (op === 'imp') {
      if (isOp(peek(), 'imp')) { p++; return { op, a: left, b: level(n) }; }
      return left;
    }
    while (isOp(peek(), op)) { p++; left = { op, a: left, b: level(n + 1) }; }
    return left;
  }
  function unary() {
    const t = peek();
    if (!t) throw new SyntaxError('unexpected end of expression');
    if (isOp(t, 'not')) { p++; return { op: 'not', a: unary() }; }
    if (t.type === '(') {
      p++;
      const e = level(0);
      if (!peek() || peek().type !== ')') throw new SyntaxError(`missing ')' for '(' at ${t.pos}`);
      p++;
      return e;
    }
    if (t.type === 'var') { p++; return { op: 'var', name: t.name }; }
    if (t.type === 'const') { p++; return { op: 'const', value: t.value }; }
    throw new SyntaxError(`unexpected token at ${t.pos}`);
  }
  if (!toks.length) throw new SyntaxError('empty expression');
  const ast = level(0);
  if (p < toks.length) throw new SyntaxError(`unexpected token at ${toks[p].pos}`);
  return ast;
}

function variables(ast, out = new Set()) {
  if (ast.op === 'var') out.add(ast.name);
  if (ast.a) variables(ast.a, out);
  if (ast.b) variables(ast.b, out);
  return out;
}

function evaluate(ast, env) {
  switch (ast.op) {
    case 'var': return !!env[ast.name];
    case 'const': return ast.value;
    case 'not': return !evaluate(ast.a, env);
    case 'and': return evaluate(ast.a, env) && evaluate(ast.b, env);
    case 'or': return evaluate(ast.a, env) || evaluate(ast.b, env);
    case 'xor': return evaluate(ast.a, env) !== evaluate(ast.b, env);
    case 'imp': return !evaluate(ast.a, env) || evaluate(ast.b, env);
    case 'iff': return evaluate(ast.a, env) === evaluate(ast.b, env);
  }
  throw new Error('bad node ' + ast.op);
}

// Rows in binary counting order; first variable is the most significant bit.
function truthTable(ast, vars) {
  vars = vars || [...variables(ast)].sort();
  const rows = [];
  const n = vars.length;
  for (let i = 0; i < 1 << n; i++) {
    const env = {};
    vars.forEach((v, k) => { env[v] = !!((i >> (n - 1 - k)) & 1); });
    rows.push({ index: i, env, value: evaluate(ast, env) });
  }
  return { vars, rows };
}

function classify(rows) {
  const t = rows.filter(r => r.value).length;
  if (t === rows.length) return 'tautology';
  if (t === 0) return 'contradiction';
  return 'contingent';
}

function equivalent(a, b) {
  const vars = [...new Set([...variables(a), ...variables(b)])].sort();
  const ta = truthTable(a, vars), tb = truthTable(b, vars);
  for (let i = 0; i < ta.rows.length; i++) {
    if (ta.rows[i].value !== tb.rows[i].value)
      return { equivalent: false, vars, counterexample: ta.rows[i].env, left: ta.rows[i].value, right: tb.rows[i].value };
  }
  return { equivalent: true, vars };
}

// Quine-McCluskey. Implicants are strings over {0,1,-}, MSB first.
function primeImplicants(minterms, n) {
  let current = new Set(minterms.map(m => m.toString(2).padStart(n, '0')));
  const primes = new Set();
  while (current.size) {
    const list = [...current];
    const used = new Set();
    const next = new Set();
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        let diff = -1, count = 0;
        for (let k = 0; k < n; k++) if (list[i][k] !== list[j][k]) { diff = k; count++; }
        if (count === 1 && list[i][diff] !== '-' && list[j][diff] !== '-') {
          next.add(list[i].slice(0, diff) + '-' + list[i].slice(diff + 1));
          used.add(list[i]); used.add(list[j]);
        }
      }
    }
    for (const t of list) if (!used.has(t)) primes.add(t);
    current = next;
  }
  return [...primes].sort();
}

const covers = (imp, m, n) => {
  const bits = m.toString(2).padStart(n, '0');
  for (let k = 0; k < n; k++) if (imp[k] !== '-' && imp[k] !== bits[k]) return false;
  return true;
};

// Essential prime implicants first, then exact minimum cover by iterative
// deepening over the remaining primes (fine for the small sizes a CLI sees).
function minimize(minterms, n) {
  if (!minterms.length) return [];
  if (minterms.length === 1 << n) return ['-'.repeat(n)];
  const primes = primeImplicants(minterms, n);
  const chosen = new Set();
  for (const m of minterms) {
    const c = primes.filter(p => covers(p, m, n));
    if (c.length === 1) chosen.add(c[0]);
  }
  const left = minterms.filter(m => ![...chosen].some(p => covers(p, m, n)));
  const rest = primes.filter(p => !chosen.has(p));
  const lits = p => [...p].filter(c => c !== '-').length;
  let best = null;
  for (let size = 0; size <= rest.length && !best; size++) {
    (function pick(start, acc) {
      if (acc.length === size) {
        if (left.every(m => acc.some(p => covers(p, m, n)))) {
          const cost = acc.reduce((s, p) => s + lits(p), 0);
          if (!best || cost < best.cost) best = { acc: [...acc], cost };
        }
        return;
      }
      for (let i = start; i < rest.length; i++) { acc.push(rest[i]); pick(i + 1, acc); acc.pop(); }
    })(0, []);
  }
  // Order terms so positive literals of earlier variables come first.
  const key = p => p.replace(/[10-]/g, c => ({ 1: '0', 0: '1', '-': '2' })[c]);
  return [...chosen, ...best.acc].sort((x, y) => (key(x) < key(y) ? -1 : 1));
}

function implicantToString(imp, vars) {
  const parts = [];
  for (let k = 0; k < vars.length; k++) {
    if (imp[k] === '1') parts.push(vars[k]);
    else if (imp[k] === '0') parts.push('!' + vars[k]);
  }
  return parts.length ? parts.join(' & ') : '1';
}

function sop(implicants, vars) {
  if (!implicants.length) return '0';
  const terms = implicants.map(i => implicantToString(i, vars));
  if (terms.length === 1) return terms[0];
  return terms.map(t => (t.includes('&') ? `(${t})` : t)).join(' | ');
}

function formatTable({ vars, rows }, label) {
  const heads = [...vars, label];
  const widths = heads.map(h => Math.max(1, h.length));
  const line = cells => cells.map((c, i) => String(c).padStart(widths[i])).join(' | ');
  const out = [line(heads), widths.map(w => '-'.repeat(w)).join('-+-')];
  for (const r of rows) out.push(line([...vars.map(v => (r.env[v] ? 1 : 0)), r.value ? 1 : 0]));
  return out.join('\n');
}

function main(argv) {
  const args = argv.slice(2);
  const flags = new Set(args.filter(a => a.startsWith('--') && a !== '--equiv'));
  const eqIdx = args.indexOf('--equiv');
  const positional = args.filter((a, i) => !a.startsWith('--') && !(eqIdx >= 0 && i === eqIdx + 1));
  if (flags.has('--help') || !positional.length) {
    console.log('usage: truth-table.js "<expr>" [--minimize] [--equiv "<expr2>"] [--quiet] [--json]\n' +
      'operators: ! ~ not | & && and * | ^ xor | | || or + | -> => | <-> <=> ==   constants: 0 1 true false');
    return positional.length || flags.has('--help') ? 0 : 2;
  }
  let ast, other;
  try {
    ast = parse(positional[0]);
    if (eqIdx >= 0) {
      if (eqIdx + 1 >= args.length) throw new SyntaxError('--equiv needs an expression');
      other = parse(args[eqIdx + 1]);
    }
  } catch (e) {
    console.error('parse error: ' + e.message);
    return 2;
  }
  const json = flags.has('--json');
  const table = truthTable(ast);
  const result = { expression: positional[0], vars: table.vars, class: classify(table.rows),
    minterms: table.rows.filter(r => r.value).map(r => r.index) };
  if (flags.has('--minimize')) result.minimized = sop(minimize(result.minterms, table.vars.length), table.vars);
  if (other) result.equiv = equivalent(ast, other);
  if (json) {
    if (!flags.has('--quiet')) result.rows = table.rows.map(r => ({ ...r.env, value: r.value }));
    console.log(JSON.stringify(result, null, 2));
  } else {
    if (!flags.has('--quiet')) console.log(formatTable(table, 'out') + '\n');
    console.log(`class: ${result.class}`);
    console.log(`minterms: ${result.minterms.length ? 'm(' + result.minterms.join(',') + ')' : 'none'}`);
    if (result.minimized !== undefined) console.log(`minimized: ${result.minimized}`);
    if (result.equiv) {
      const e = result.equiv;
      if (e.equivalent) console.log('equivalent: yes');
      else console.log('equivalent: no, counterexample ' +
        e.vars.map(v => `${v}=${e.counterexample[v] ? 1 : 0}`).join(' ') + ` gives ${+e.left} vs ${+e.right}`);
    }
  }
  return other && !result.equiv.equivalent ? 1 : 0;
}

module.exports = { tokenize, parse, variables, evaluate, truthTable, classify, equivalent,
  primeImplicants, minimize, sop, formatTable, main };

if (require.main === module) process.exitCode = main(process.argv);
