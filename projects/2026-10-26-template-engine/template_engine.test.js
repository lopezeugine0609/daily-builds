import { test } from 'node:test';
import assert from 'node:assert';

// Import actual template engine implementation from template_engine.js
import { TemplateEngine } from './template_engine.js';

test('variable interpolation and filters', () => {
    const tpl = 'Hello, {{ name }}! Welcome to {{ city | upper }}.';
    const ctx = { name: 'Alice', city: 'manila' };
    assert.strictEqual(TemplateEngine.render(tpl, ctx), 'Hello, Alice! Welcome to MANILA.');
});

test('conditionals if/else', () => {
    const tpl = '{{#if active}}Active user{{else}}Inactive user{{/if}}';
    assert.strictEqual(TemplateEngine.render(tpl, { active: true }), 'Active user');
    assert.strictEqual(TemplateEngine.render(tpl, { active: false }), 'Inactive user');
});

test('each loop', () => {
    const tpl = 'Items:\n{{#each items}}- {{ this }}\n{{/each}}';
    const ctx = { items: ['apple', 'banana', 'cherry'] };
    assert.strictEqual(TemplateEngine.render(tpl, ctx), 'Items:\n- apple\n- banana\n- cherry\n');
});

test('each loop with objects', () => {
    const tpl = '{{#each users}}{{ name }} ({{ role }})\n{{/each}}';
    const ctx = { users: [{ name: 'Eve', role: 'Admin' }, { name: 'Dave', role: 'User' }] };
    assert.strictEqual(TemplateEngine.render(tpl, ctx), 'Eve (Admin)\nDave (User)\n');
});
