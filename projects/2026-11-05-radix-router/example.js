const { RadixRouter } = require('./index.js');

const router = new RadixRouter();

router.add('GET', '/', { desc: 'Home page' });
router.add('GET', '/users/:id', { desc: 'User profile' });
router.add('POST', '/users/:id/settings', { desc: 'Update settings' });
router.add('GET', '/static/*filepath', { desc: 'Static asset server' });

console.log('Registered Routes:');
console.log(router.listRoutes());

console.log('\nLookups:');
console.log("GET / ->", router.lookup('GET', '/'));
console.log("GET /users/99 ->", router.lookup('GET', '/users/99'));
console.log("POST /users/alice/settings ->", router.lookup('POST', '/users/alice/settings'));
console.log("GET /static/images/logo.png ->", router.lookup('GET', '/static/images/logo.png'));
console.log("GET /unknown ->", router.lookup('GET', '/unknown'));
