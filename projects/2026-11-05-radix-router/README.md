# Radix Tree HTTP Router

Zero-dependency JavaScript router supporting static, parametric (`:param`), and wildcard (`*wild`) path segments using a radix tree algorithm.

## Features

- **High-Performance Radix Tree**: Compact node prefix splitting and efficient traversal.
- **Parametric Routes**: Capture path parameters like `/users/:id`.
- **Wildcard Routes**: Match remaining path suffixes like `/static/*filepath`.
- **Method Routing**: Map multiple HTTP methods per path.
- **Route Introspection**: List all registered routes with `router.listRoutes()`.

## Usage Example

```javascript
const { RadixRouter } = require('./index.js');

const router = new RadixRouter();
router.add('GET', '/', { desc: 'Home' });
router.add('GET', '/users/:id', { desc: 'User Profile' });

console.log(router.lookup('GET', '/users/42'));
// Output: { handler: { desc: 'User Profile' }, params: { id: '42' } }
```

### Real Execution Output

```
$ node example.js
Registered Routes:
[
  { method: 'GET', path: '/', handler: { desc: 'Home page' } },
  {
    method: 'GET',
    path: '/users/:id',
    handler: { desc: 'User profile' }
  },
  {
    method: 'POST',
    path: '/users/:id/settings',
    handler: { desc: 'Update settings' }
  },
  {
    method: 'GET',
    path: '/static/*filepath',
    handler: { desc: 'Static asset server' }
  }
]

Lookups:
GET / -> { handler: { desc: 'Home page' }, params: {} }
GET /users/99 -> { handler: { desc: 'User profile' }, params: { id: '99' } }
POST /users/alice/settings -> { handler: { desc: 'Update settings' }, params: { id: 'alice' } }
GET /static/images/logo.png -> {
  handler: { desc: 'Static asset server' },
  params: { filepath: '/images/logo.png' }
}
GET /unknown -> null
```

## Running Tests

```bash
node --test
```

```
✔ RadixRouter - static routes (1.5347ms)
✔ RadixRouter - parametric routes (0.2464ms)
✔ RadixRouter - wildcard routes (0.1672ms)
✔ RadixRouter - route listing (0.9289ms)
✔ RadixRouter - conflicts and validation (0.3894ms)
ℹ tests 5
ℹ suites 0
ℹ pass 5
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 96.7568
```
