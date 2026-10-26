import fs from 'node:fs';

class TemplateEngine {
    static resolvePath(context, pathStr) {
        pathStr = pathStr.trim();
        if (pathStr === '') return null;
        if ((pathStr.startsWith('"') && pathStr.endsWith('"')) || (pathStr.startsWith("'") && pathStr.endsWith("'"))) {
            return pathStr.slice(1, -1);
        }
        if (pathStr.toLowerCase() === 'true') return true;
        if (pathStr.toLowerCase() === 'false') return false;
        if (/^\d+$/.test(pathStr)) return parseInt(pathStr, 10);

        const parts = pathStr.split('.');
        let curr = context;
        for (const part of parts) {
            if (curr && typeof curr === 'object' && part in curr) {
                curr = curr[part];
            } else {
                return null;
            }
        }
        return curr;
    }

    static applyFilter(value, filterName) {
        if (filterName === 'upper') {
            return value !== null && value !== undefined ? String(value).toUpperCase() : '';
        } else if (filterName === 'lower') {
            return value !== null && value !== undefined ? String(value).toLowerCase() : '';
        } else if (filterName === 'json') {
            return JSON.stringify(value);
        } else if (filterName === 'length') {
            return Array.isArray(value) || typeof value === 'string' ? value.length : 0;
        } else if (filterName === 'title') {
            return value !== null && value !== undefined ? String(value).replace(/\b\w/g, l => l.toUpperCase()) : '';
        }
        return value;
    }

    static evaluateExpression(expr, context) {
        expr = expr.trim();
        if (expr.includes('|')) {
            const parts = expr.split('|').map(p => p.trim());
            let val = this.resolvePath(context, parts[0]);
            for (let i = 1; i < parts.length; i++) {
                val = this.applyFilter(val, parts[i]);
            }
            return val;
        }
        return this.resolvePath(context, expr);
    }

    static render(templateStr, context) {
        // Handle {{#if cond}} ... {{else}} ... {{/if}}
        const ifRegex = /\{\{\s*#if\s+([^}]+)\s*\}\}([\s\S]*?)(?:\{\{\s*else\s*\}\}([\s\S]*?))?\{\{\s*\/if\s*\}\}/g;
        templateStr = templateStr.replace(ifRegex, (match, cond, trueBlock, falseBlock) => {
            const condVal = this.evaluateExpression(cond, context);
            if (condVal) {
                return this.render(trueBlock, context);
            } else {
                return falseBlock ? this.render(falseBlock, context) : '';
            }
        });

        // Handle {{#each list}} ... {{/each}}
        const eachRegex = /\{\{\s*#each\s+([^}]+)\s*\}\}([\s\S]*?)\{\{\s*\/each\s*\}\}/g;
        templateStr = templateStr.replace(eachRegex, (match, listExpr, block) => {
            const list = this.evaluateExpression(listExpr, context);
            if (Array.isArray(list)) {
                return list.map(item => {
                    const itemContext = Object.assign({}, context, typeof item === 'object' && item !== null ? item : {}, { this: item });
                    return this.render(block, itemContext);
                }).join('');
            }
            return '';
        });

        // Handle variables: {{ expr }}
        templateStr = templateStr.replace(/\{\{\s*([^#\/][^}]*?)\s*\}\}/g, (match, expr) => {
            const val = this.evaluateExpression(expr, context);
            return val !== null && val !== undefined ? val : '';
        });

        return templateStr;
    }
}

export { TemplateEngine };
if (process.argv[1] && process.argv[1].endsWith('template_engine.js')) {
    const args = process.argv.slice(2);
    let templatePath = null;
    let contextPath = null;
    let inlineEval = null;
    let inlineCtx = null;

    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--context' || args[i] === '-c') contextPath = args[++i];
        else if (args[i] === '--eval' || args[i] === '-e') inlineEval = args[++i];
        else if (args[i] === '--json-ctx' || args[i] === '-j') inlineCtx = args[++i];
        else if (!templatePath) templatePath = args[i];
    }

    let context = {};
    if (contextPath) {
        context = JSON.parse(fs.readFileSync(contextPath, 'utf8'));
    } else if (inlineCtx) {
        context = JSON.parse(inlineCtx);
    }

    let templateStr = '';
    if (templatePath) {
        templateStr = fs.readFileSync(templatePath, 'utf8');
    } else if (inlineEval) {
        templateStr = inlineEval;
    } else {
        templateStr = fs.readFileSync(0, 'utf8');
    }

    process.stdout.write(TemplateEngine.render(templateStr, context));
}
