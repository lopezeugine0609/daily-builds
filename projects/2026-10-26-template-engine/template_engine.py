import sys
import json
import os
import argparse

class TemplateEngine:
    """Zero-dependency lightweight template engine supporting variables, loops, conditionals, and filters."""
    
    @staticmethod
    def resolve_path(context, path):
        parts = path.split('.')
        curr = context
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            elif isinstance(curr, list) and part.isdigit() and int(part) < len(curr):
                curr = curr[int(part)]
            else:
                return None
        return curr

    @staticmethod
    def apply_filter(value, filter_name):
        if filter_name == 'upper':
            return str(value).upper() if value is not None else ''
        elif filter_name == 'lower':
            return str(value).lower() if value is not None else ''
        elif filter_name == 'json':
            return json.dumps(value)
        elif filter_name == 'length':
            return len(value) if hasattr(value, '__len__') else 0
        elif filter_name == 'title':
            return str(value).title() if value is not None else ''
        return value

    @classmethod
    def evaluate_expression(cls, expr, context):
        expr = expr.strip()
        if '|' in expr:
            parts = [p.strip() for p in expr.split('|')]
            val = cls.resolve_path(context, parts[0])
            for f in parts[1:]:
                val = cls.apply_filter(val, f)
            return val
        return cls.resolve_path(context, expr)

    @classmethod
    def render(cls, template_str, context):
        lines = template_str.splitlines(keepends=True)
        output_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Conditionals: {{#if condition}}
            if stripped.startswith('{{#if ') and stripped.endswith('}}'):
                cond_expr = stripped[6:-2].strip()
                cond_val = cls.evaluate_expression(cond_expr, context)
                
                block_lines = []
                else_lines = []
                in_else = False
                depth = 1
                i += 1
                
                while i < len(lines):
                    curr_stripped = lines[i].strip()
                    if curr_stripped.startswith('{{#if ') and curr_stripped.endswith('}}') or curr_stripped.startswith('{{#each ') and curr_stripped.endswith('}}'):
                        depth += 1
                        if in_else:
                            else_lines.append(lines[i])
                        else:
                            block_lines.append(lines[i])
                    elif curr_stripped == '{{/if}}' or curr_stripped == '{{/each}}':
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                        else:
                            if in_else:
                                else_lines.append(lines[i])
                            else:
                                block_lines.append(lines[i])
                    elif curr_stripped == '{{else}}' and depth == 1:
                        in_else = True
                    else:
                        if in_else:
                            else_lines.append(lines[i])
                        else:
                            block_lines.append(lines[i])
                    i += 1
                
                target_lines = block_lines if cond_val else else_lines
                output_lines.append(cls.render(''.join(target_lines), context))
                
            # Loops: {{#each list_expr}} ... {{/each}}
            elif stripped.startswith('{{#each ') and stripped.endswith('}}'):
                list_expr = stripped[8:-2].strip()
                items = cls.evaluate_expression(list_expr, context)
                
                block_lines = []
                depth = 1
                i += 1
                
                while i < len(lines):
                    curr_stripped = lines[i].strip()
                    if curr_stripped.startswith('{{#each ') and curr_stripped.endswith('}}') or curr_stripped.startswith('{{#if ') and curr_stripped.endswith('}}'):
                        depth += 1
                        block_lines.append(lines[i])
                    elif curr_stripped == '{{/each}}' or curr_stripped == '{{/if}}':
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                        else:
                            block_lines.append(lines[i])
                    else:
                        block_lines.append(lines[i])
                    i += 1
                
                block_str = ''.join(block_lines)
                if isinstance(items, list):
                    for item in items:
                        item_context = dict(context)
                        if isinstance(item, dict):
                            item_context.update(item)
                        item_context['this'] = item
                        output_lines.append(cls.render(block_str, item_context))
            else:
                rendered_line = line
                start_idx = 0
                while True:
                    start = rendered_line.find('{{', start_idx)
                    if start == -1:
                        break
                    end = rendered_line.find('}}', start)
                    if end == -1:
                        break
                    expr = rendered_line[start+2:end].strip()
                    val = cls.evaluate_expression(expr, context)
                    if val is None:
                        val = ''
                    rendered_line = rendered_line[:start] + str(val) + rendered_line[end+2:]
                    start_idx = start + len(str(val))
                output_lines.append(rendered_line)
                i += 1
                
        return ''.join(output_lines)

def main():
    parser = argparse.ArgumentParser(description="Zero-dependency lightweight template engine.")
    parser.add_argument('template', nargs='?', help='Path to template file')
    parser.add_argument('--context', '-c', help='Path to JSON context file')
    parser.add_argument('--eval', '-e', help='Inline template string')
    parser.add_argument('--json-ctx', '-j', help='Inline JSON context string')
    args = parser.parse_args()

    context = {}
    if args.context:
        with open(args.context, 'r', encoding='utf-8') as f:
            context = json.load(f)
    elif args.json_ctx:
        context = json.loads(args.json_ctx)

    template_str = ""
    if args.template:
        with open(args.template, 'r', encoding='utf-8') as f:
            template_str = f.read()
    elif args.eval:
        template_str = args.eval
    else:
        template_str = sys.stdin.read()

    result = TemplateEngine.render(template_str, context)
    sys.stdout.write(result)

if __name__ == '__main__':
    main()
