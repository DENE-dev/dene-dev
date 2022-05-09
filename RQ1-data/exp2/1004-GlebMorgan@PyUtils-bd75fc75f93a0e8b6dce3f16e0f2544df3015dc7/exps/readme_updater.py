import re
import sys
from contextlib import contextmanager
from importlib import import_module
from inspect import signature, cleandoc
from pathlib import Path
from types import FunctionType, ModuleType, MethodType
from typing import Union


@contextmanager
def path_modifier(path: Union[str, Path]):
    sys.path.insert(0, str(path))
    yield
    try:
        del sys.path[sys.path.index(path)]
    except ValueError:
        pass


def iscode(line):
    return line.startswith('>>>') or line.startswith('...')


def cleanup_md(docs):
    lines = docs.split('\n')
    result = []
    codeblock = None

    for n, line in enumerate(lines):
        if not line.strip():
            continue

        # Convert the first line to title
        if not result:
            line = '####' + ' ' + line

        # Insert codeblock start
        if not codeblock and iscode(line):
            result.append('')
            result.append('```python')
            codeblock = True

        # Insert codeblock end
        elif codeblock and not iscode(line) and not line.startswith(' '):
            codeblock = False
            result.append('```')

        # Add line seps
        if result and not codeblock and not line.startswith(' '):
            result.append('')

        # Replace dot markers with dashes
        line = line.replace('•', '-')

        # Convert indents to 2 spaces
        line = line.strip() if codeblock else line.replace(' '*4, ' '*2)

        result.append(line)

    if codeblock:
        result.append('```')
    return '\n'.join(result)


def iter_members(obj):
    for name in obj.__dict__:
        item = getattr(obj, name)
        if name.startswith('__') and name.endswith('__'):
            continue
        if not isinstance(item, (FunctionType, MethodType)):
            continue
        yield name, item


def gen_class_doc(cls):
    doc = cls.__doc__
    title = f"### `{cls.__name__}`\n"
    if doc:
        return title + '\n' + cleanup_md(cleandoc(doc))
    else:
        return title


def gen_func_doc(func, env, owner: type = None):
    # Eval string annotations to have them neat & clean in signature
    for name, ann in func.__annotations__.items():
        if isinstance(ann, str):
            func.__annotations__[name] = eval(ann, env)

    # Acquire string representation of `func` signature
    sign = func.__name__ + str(signature(func))

    # Append class name if necessary
    if owner:
        sign = f'{owner.__name__}.{sign}'

    # DickTape: fix qualname in return annotation of imported class
    sign = re.sub(r"(?<=->\s)(\w+)\.(\w+)", r"\2", sign)

    # Get docstring
    doc = func.__doc__
    doc = cleanup_md(cleandoc(doc)) if doc else ''

    return f"#### `{sign}`\n\n{doc}"


def gen_doc(readme: str, module: ModuleType):
    sep = '\n\n---\n\n'
    result = []
    for name in module.__all__:
        item = getattr(module, name)
        if isinstance(item, FunctionType):
            result.append(gen_func_doc(item, module.__dict__))
        elif isinstance(item, type):
            result.append(gen_class_doc(item))
            for attr, method in iter_members(item):
                result.append(gen_func_doc(method, module.__dict__, owner=item))
        else:
            result.append(readme_find(readme, name))
    return sep.join(result)


def readme_find(text: str, item: str):
    section_start = text.find('## Documentation')
    start = text.find(f'#### `{item}`', section_start)
    end = text.find('---', start)
    return text[start:end].rstrip()


def gen_contents(doc: str):
    entry_pattern = re.compile(r'#{3,4} `([\w.]+).*`\n\n#{5} (.+)', flags=re.MULTILINE)
    result = []
    prev = ''
    indent = ' '*2
    for name, title in re.findall(entry_pattern, doc):
        if name.startswith(prev + '.'):
            name = name.lstrip(prev) + '()'
            indent = ' '*2
        else:
            prev = name
            indent = ''
        description = title[0].lower() + title[1:]
        result.append(f'{indent}- **`{name}`** – {description}')
    return '\n'.join(result)


def update_readme(project: str, module_name: str):
    with path_modifier(r'D:\GLEB\Python\PyUtils'):
        module = import_module(module_name)
    readme_file = Path(project) / 'README.md'
    readme = readme_file.read_text(encoding='utf8')

    doc = gen_doc(readme, module)
    contents = gen_contents(doc)

    contents_section_idx = readme.find('## Package contents')

    updated_readme = ('\n'*3).join((
            readme[:contents_section_idx].rstrip(),
            '## Package contents' + '\n'*2 + contents,
            '## Documentation' + '\n'*2 + doc
    ))

    readme_file.write_text(updated_readme, encoding='utf8')


if __name__ == '__main__':

    if len(sys.argv) < 3:
        raise RuntimeError("project path and module name should be specified")

    path = sys.argv[1]
    module = sys.argv[2]

    update_readme(path, module)