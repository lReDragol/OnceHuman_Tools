import os

def generate_tree(root_dir, prefix='', exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = {'.venv', 'build', 'dist'}
    entries = os.listdir(root_dir)
    entries = [e for e in entries if e not in exclude_dirs]
    entries.sort()
    entries_count = len(entries)
    for index, entry in enumerate(entries):
        full_path = os.path.join(root_dir, entry)
        connector = '└── ' if index == entries_count - 1 else '├── '
        if os.path.isdir(full_path):
            yield prefix + connector + entry + '/'
            extension = '    ' if index == entries_count - 1 else '│   '
            yield from generate_tree(full_path, prefix + extension, exclude_dirs)
        else:
            yield prefix + connector + entry

if __name__ == '__main__':
    root_dir = os.getcwd()
    exclude_dirs = {'.venv', 'build', 'dist', 'calc1', 'fish', 'save'}
    with open('tree.txt', 'w', encoding='utf-8') as f:
        f.write(os.path.basename(root_dir) + '/\n')
        for line in generate_tree(root_dir, exclude_dirs=exclude_dirs):
            f.write(line + '\n')
