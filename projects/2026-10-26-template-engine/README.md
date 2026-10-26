# template-engine

A zero-dependency lightweight JavaScript template engine supporting variable interpolation, dot notation, custom filters, conditionals, and loops.

## Features

- **Variable Interpolation**: `{{ name }}`
- **Dot Notation & Nested Lookups**: `{{ user.profile.name }}`
- **Filters**: `upper`, `lower`, `title`, `length`, `json` via pipe syntax (`{{ title | upper }}`)
- **Conditionals**: `{{#if condition}} ... {{else}} ... {{/if}}`
- **Loops**: `{{#each items}} ... {{this}} ... {{/each}}`

## Usage Examples

### Inline Evaluation
```bash
node projects/2026-10-26-template-engine/template_engine.js -e "Hello {{ name | upper }}! Status: {{#if active}}VIP{{else}}Standard{{/if}}" -j '{"name": "charlie", "active": true}'
```
**Output:**
```
Hello CHARLIE! Status: VIP
```

## Running Tests

```bash
node --test projects/2026-10-26-template-engine/template_engine.test.js
```
