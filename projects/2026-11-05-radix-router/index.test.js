const test = require('node:test');
const assert = require('node:assert');
const { RadixRouter } = require('./index.js');

test('RadixRouter - static routes', () => {
    const router = new RadixRouter();
    router.add('GET', '/', 'home');
    router.add('GET', '/about', 'about');
    router.add('GET', '/users/profile', 'profile');
    router.add('POST', '/users/profile', 'update-profile');

    assert.deepStrictEqual(router.lookup('GET', '/'), { handler: 'home', params: {} });
    assert.deepStrictEqual(router.lookup('GET', '/about'), { handler: 'about', params: {} });
    assert.deepStrictEqual(router.lookup('GET', '/users/profile'), { handler: 'profile', params: {} });
    assert.deepStrictEqual(router.lookup('POST', '/users/profile'), { handler: 'update-profile', params: {} });
    assert.strictEqual(router.lookup('GET', '/users'), null);
    assert.strictEqual(router.lookup('PUT', '/'), null);
});

test('RadixRouter - parametric routes', () => {
    const router = new RadixRouter();
    router.add('GET', '/users/:id', 'user-detail');
    router.add('GET', '/users/:id/posts/:postId', 'user-post');

    assert.deepStrictEqual(router.lookup('GET', '/users/42'), { handler: 'user-detail', params: { id: '42' } });
    assert.deepStrictEqual(router.lookup('GET', '/users/alice/posts/101'), {
        handler: 'user-post',
        params: { id: 'alice', postId: '101' }
    });
    assert.strictEqual(router.lookup('GET', '/users/42/extra'), null);
});

test('RadixRouter - wildcard routes', () => {
    const router = new RadixRouter();
    router.add('GET', '/static/*filepath', 'static-file');

    assert.deepStrictEqual(router.lookup('GET', '/static/css/main.css'), {
        handler: 'static-file',
        params: { filepath: '/css/main.css' }
    });
    assert.deepStrictEqual(router.lookup('GET', '/static/images/avatar.png'), {
        handler: 'static-file',
        params: { filepath: '/images/avatar.png' }
    });
});

test('RadixRouter - route listing', () => {
    const router = new RadixRouter();
    router.add('GET', '/', 'home');
    router.add('GET', '/users/:id', 'user');

    const routes = router.listRoutes();
    assert.strictEqual(routes.length, 2);
    assert.ok(routes.some(r => r.path === '/' && r.method === 'GET'));
    assert.ok(routes.some(r => r.path === '/users/:id' && r.method === 'GET'));
});

test('RadixRouter - conflicts and validation', () => {
    const router = new RadixRouter();
    router.add('GET', '/test', 'h1');
    assert.throws(() => {
        router.add('GET', '/test', 'h2');
    }, /Conflict/);

    assert.throws(() => {
        router.add('GET', 'invalid-path', 'h3');
    }, /Path must start with/);
});
