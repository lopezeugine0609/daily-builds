/**
 * Radix Tree HTTP Router
 * Zero-dependency JavaScript router supporting static, parametric (:param), and wildcard (*wild) segments.
 */

class Node {
    constructor(prefix = '') {
        this.prefix = prefix;
        this.children = [];
        this.handlers = new Map(); // method -> data
        this.paramChild = null;    // child for :param
        this.wildcardChild = null; // child for *wild
        this.paramName = null;
        this.wildcardName = null;
    }
}

class RadixRouter {
    constructor() {
        this.root = new Node();
    }

    add(method, path, data) {
        if (!path.startsWith('/')) {
            throw new Error('Path must start with /');
        }
        method = method.toUpperCase();
        let curr = this.root;
        let remaining = path;

        while (remaining.length > 0) {
            // Check for wildcard
            const wildIdx = remaining.indexOf('*');
            if (wildIdx !== -1) {
                const staticPart = remaining.slice(0, wildIdx);
                if (staticPart.length > 0) {
                    curr = this._insertStatic(curr, staticPart);
                }
                const wildName = remaining.slice(wildIdx + 1);
                if (!wildName) {
                    throw new Error('Wildcard name cannot be empty');
                }
                if (!curr.wildcardChild) {
                    curr.wildcardChild = new Node();
                    curr.wildcardChild.wildcardName = wildName;
                } else if (curr.wildcardChild.wildcardName !== wildName) {
                    throw new Error(`Conflict: wildcard name mismatch '${curr.wildcardChild.wildcardName}' vs '${wildName}'`);
                }
                curr = curr.wildcardChild;
                break;
            }

            // Check for parameter
            const paramIdx = remaining.indexOf(':');
            if (paramIdx !== -1) {
                // Is there a slash before param? If not, parameter starts immediately
                const staticPart = remaining.slice(0, paramIdx);
                if (staticPart.length > 0) {
                    curr = this._insertStatic(curr, staticPart);
                }
                // Extract param name up to next '/'
                const nextSlash = remaining.indexOf('/', paramIdx);
                const paramEnd = nextSlash === -1 ? remaining.length : nextSlash;
                const paramName = remaining.slice(paramIdx + 1, paramEnd);
                if (!paramName) {
                    throw new Error('Parameter name cannot be empty');
                }

                if (!curr.paramChild) {
                    curr.paramChild = new Node();
                    curr.paramChild.paramName = paramName;
                } else if (curr.paramChild.paramName !== paramName) {
                    throw new Error(`Conflict: parameter name mismatch '${curr.paramChild.paramName}' vs '${paramName}'`);
                }
                curr = curr.paramChild;
                remaining = remaining.slice(paramEnd);
                continue;
            }

            // Pure static
            curr = this._insertStatic(curr, remaining);
            break;
        }

        if (curr.handlers.has(method)) {
            throw new Error(`Conflict: route ${method} ${path} already registered`);
        }
        curr.handlers.set(method, data);
        return this;
    }

    _insertStatic(node, prefix) {
        let curr = node;
        let rem = prefix;

        while (rem.length > 0) {
            // Find longest common prefix among children
            let matchedChild = null;
            let commonLen = 0;

            for (const child of curr.children) {
                const len = this._commonPrefixLen(child.prefix, rem);
                if (len > commonLen) {
                    commonLen = len;
                    matchedChild = child;
                }
            }

            if (!matchedChild) {
                // No common prefix, create new child
                const newNode = new Node(rem);
                curr.children.push(newNode);
                return newNode;
            }

            if (commonLen === matchedChild.prefix.length) {
                // Consume matched prefix and continue down
                rem = rem.slice(commonLen);
                curr = matchedChild;
                if (rem.length === 0) {
                    return curr;
                }
            } else {
                // Split child prefix
                const splitNode = new Node(matchedChild.prefix.slice(0, commonLen));
                splitNode.children = [matchedChild];
                matchedChild.prefix = matchedChild.prefix.slice(commonLen);

                // Replace matchedChild in curr.children with splitNode
                const idx = curr.children.indexOf(matchedChild);
                curr.children[idx] = splitNode;

                rem = rem.slice(commonLen);
                if (rem.length === 0) {
                    return splitNode;
                }

                const newNode = new Node(rem);
                splitNode.children.push(newNode);
                return newNode;
            }
        }
        return curr;
    }

    _commonPrefixLen(a, b) {
        const limit = Math.min(a.length, b.length);
        for (let i = 0; i < limit; i++) {
            if (a[i] !== b[i]) return i;
        }
        return limit;
    }

    lookup(method, path) {
        method = method.toUpperCase();
        const params = {};
        const result = this._search(this.root, path, params);
        if (!result || !result.handlers.has(method)) {
            return null;
        }
        return {
            handler: result.handlers.get(method),
            params
        };
    }

    _search(node, path, params) {
        // 1. Try static children
        for (const child of node.children) {
            if (path.startsWith(child.prefix)) {
                const rest = path.slice(child.prefix.length);
                if (rest.length === 0) {
                    if (child.handlers.size > 0 || child.children.length > 0 || child.paramChild || child.wildcardChild) {
                        // Check if exact match or if param/wildcard can match empty/slash
                        const res = this._exactMatch(child);
                        if (res) return res;
                    }
                }
                const res = this._search(child, rest, params);
                if (res) return res;
            }
        }

        // 2. Try param child if path has segment
        if (node.paramChild) {
            const slashIdx = path.indexOf('/');
            const segment = slashIdx === -1 ? path : path.slice(0, slashIdx);
            if (segment.length > 0) {
                const rest = slashIdx === -1 ? '' : path.slice(slashIdx);
                const oldParamVal = params[node.paramChild.paramName];
                params[node.paramChild.paramName] = segment;

                if (rest.length === 0) {
                    if (node.paramChild.handlers.size > 0 || node.paramChild.children.length > 0 || node.paramChild.paramChild || node.paramChild.wildcardChild) {
                        const res = this._exactMatch(node.paramChild);
                        if (res) return res;
                    }
                }

                const res = this._search(node.paramChild, rest, params);
                if (res) return res;

                if (oldParamVal === undefined) {
                    delete params[node.paramChild.paramName];
                } else {
                    params[node.paramChild.paramName] = oldParamVal;
                }
            }
        }

        // 3. Try wildcard child
        if (node.wildcardChild) {
            params[node.wildcardChild.wildcardName] = path.startsWith('/') ? path : '/' + path;
            return node.wildcardChild;
        }

        // Check if current node matches exact
        if (path === '' && node.handlers.size > 0) {
            return node;
        }

        return null;
    }

    _exactMatch(node) {
        if (node.handlers.size > 0) return node;
        // Check if children have empty match
        for (const child of node.children) {
            if (child.prefix === '' && child.handlers.size > 0) return child;
        }
        if (node.paramChild && node.paramChild.handlers.size > 0 && node.paramChild.paramChild === null && node.paramChild.wildcardChild === null && node.paramChild.children.length === 0) {
            // parameter ending empty?
        }
        return null;
    }

    listRoutes(node = this.root, prefix = '', acc = []) {
        for (const [method, handler] of node.handlers.entries()) {
            acc.push({ method, path: prefix || '/', handler });
        }
        for (const child of node.children) {
            this.listRoutes(child, prefix + child.prefix, acc);
        }
        if (node.paramChild) {
            const sep = prefix.endsWith('/') ? '' : '/';
            this.listRoutes(node.paramChild, prefix + sep + `:${node.paramChild.paramName}`, acc);
        }
        if (node.wildcardChild) {
            const sep = prefix.endsWith('/') ? '' : '/';
            this.listRoutes(node.wildcardChild, prefix + sep + `*${node.wildcardChild.wildcardName}`, acc);
        }
        return acc;
    }
}

module.exports = { RadixRouter };
