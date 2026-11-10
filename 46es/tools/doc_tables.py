"""Generated numbers in model/print_v5/README.md (plan 4-4, second stage).

The part tables of 「주문 1」 and 「주문 2」 keep their hand-written cells (what the part is, orientation, notes), but
the measured cells are written from the records: size X×Y×Z (print_bbox_mm), and for order 2 the volume
(cad_volume_mm3) and the minimum wall (thin-wall scan), plus a "(NN.NN cm³)" note in a description cell.

  python 46es/tools/doc_tables.py          check: exit 1 and list the cells that differ
  python 46es/tools/doc_tables.py --write  rewrite those cells

check_repository.py runs the check, so a regenerated print set with a changed size, volume or wall fails CI until
this is run and the README diff is committed.

Formats: sizes and walls to 2 decimals (sizes drop trailing zeros), volumes 1 decimal from 10 cm³ up, else 2.
A row naming several files (`46es_v5_mount_L/R`) shows one size per file, separated by " / ".
"""
import argparse
import json
import re
import sys

from common import ROOT
from parts_v5 import ORDERS, parts

README = ROOT / 'model/print_v5/README.md'
HEADINGS = {'order1': '주문 1', 'order2': '주문 2'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def size(values):
    return '×'.join(f'{v:.2f}'.rstrip('0').rstrip('.') for v in values)


def volume(mm3):
    cm3 = mm3 / 1000
    return f'{cm3:.1f}' if cm3 >= 10 else f'{cm3:.2f}'


def row_files(cell):
    name = cell.strip().strip('`')
    head, _, alts = name.rpartition('_')
    return [f'{head}_{a}' for a in alts.split('/')] if '/' in alts else [name]


def split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def join_row(cells):
    return '| ' + ' | '.join(cells) + ' |'


def generate(text):
    """`text` with every generated cell rewritten, the (file, column, old, new) changes and the number of cells."""
    lines = text.split('\n')
    changes, count = [], 0
    for order, heading in HEADINGS.items():
        records = {p['file']: p for p in read(ORDERS[order]['record'])}
        walls = {p['file']: p['wall_min_mm'] for p in read(ORDERS[order]['wall'])['parts']}
        registry = {p.file for p in parts(order)}
        start = next(i for i, line in enumerate(lines) if line.startswith(f'## {heading}'))
        first = next(i for i in range(start + 1, len(lines)) if lines[i].startswith('|'))
        end = next((i for i in range(first, len(lines)) if not lines[i].startswith('|')), len(lines))
        table = range(first, end)                                   # the first table under the heading
        header = split_row(lines[table[0]])
        col = lambda word: next(i for i, h in enumerate(header) if word in h)
        listed = []
        for i in table[2:]:
            cells = split_row(lines[i])
            files = row_files(cells[col('파일')])
            listed += files
            new = dict()
            new[col('X×Y×Z')] = ' / '.join(size(records[f]['print_bbox_mm']) for f in files)
            if order == 'order2':
                (file,) = files
                new[col('부피')] = volume(records[file]['cad_volume_mm3'])
                new[col('최소 벽')] = f'{walls[file]:.2f}'
            for j, cell in enumerate(cells):
                if re.search(r'\([\d.]+ cm³\)', cell):
                    (file,) = files
                    new[j] = re.sub(r'\([\d.]+ cm³\)', f'({records[file]["cad_volume_mm3"] / 1000:.2f} cm³)', cell)
            count += len(new)
            for j, value in new.items():
                if cells[j] != value:
                    changes.append((files[0], header[j], cells[j], value))
                    cells[j] = value
            lines[i] = join_row(cells)
        missing = sorted(set(listed) ^ registry)
        if missing:
            raise SystemExit(f'print_v5/README.md {heading} files differ from tools/parts_v5.py: {missing}')
    return '\n'.join(lines), changes, count


def check():
    """Number of generated cells; raises AssertionError listing the stale ones."""
    text = README.read_text(encoding='utf-8')
    new, changes, count = generate(text)
    if changes:
        listing = '; '.join(f'{f} {c}: {a!r} -> {b!r}' for f, c, a, b in changes)
        raise AssertionError(f'print_v5/README.md generated cells are stale (python 46es/tools/doc_tables.py --write): {listing}')
    return count


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true', help='rewrite the generated cells')
    a = ap.parse_args()
    text = README.read_text(encoding='utf-8')
    new, changes, _ = generate(text)
    for f, c, old, value in changes:
        print(f'{f} {c}: {old!r} -> {value!r}')
    if a.write:
        README.write_text(new, encoding='utf-8', newline='\n')
        print(f'{len(changes)} cells written')
    elif changes:
        sys.exit(1)
    else:
        print('print_v5/README.md generated cells are current')
