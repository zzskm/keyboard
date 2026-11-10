"""The printed parts of 46es v5 in one table (plan 4-1): order, file name, CAD body, source model, material, wall
limit and print orientation. export_print_v5.py exports from it, pipeline.py and check_repository.py compare the
records with it, verify_seam_v5.py reads its part lists, and check_repository.py requires every order-2 body to be
shown by a guide group. Adding or renaming a part is one row here (plus the CAD body it names).

Rows keep the order of the committed records (seam-v5-print-set.json, seam-v5-trial-print-set.json): the exporter
writes them in this order.
"""
from dataclasses import dataclass

from common import ROOT

MODEL = ROOT / 'model/46es_mount_seam_v5.sc'
TRIALS = ROOT / 'model/ctrl_trials_v5.sc'            # snap trials A/C and rear rest height variants (build_seam_v5.py)
SAMPLE = ROOT / 'model/samples/46es_sw_hole_sample.sc'

MJF = 'MJF PA12S-HP 검정'
RESIN = '8001 레진 투명'
WALL_LIMIT = {MJF: 1.0, RESIN: 0.8}                  # minimum wall per material (print_v5 README 「재료·주문 메모」)
WALL_SCAN = dict(limit=1.0, warn=1.5)                # thin_wall_scan.py thresholds for every part

DATA = ROOT / 'inspection/data'
ORDERS = {
    'order1': dict(record=DATA / 'seam-v5-trial-print-set.json', wall=DATA / 'seam-v5-trial-thin-wall.json'),
    'order2': dict(record=DATA / 'seam-v5-print-set.json', wall=DATA / 'seam-v5-mjf-thin-wall.json'),
}


@dataclass(frozen=True)
class Part:
    order: str
    name: str            # file stem without the 46es_v5_ prefix
    body: str            # CAD body name in `source`
    source: object       # Path of the CAD model the body is exported from
    material: str
    flip: bool           # flip about X for printing (top face down); False prints as modelled

    @property
    def file(self):
        return '46es_v5_' + self.name

    @property
    def folder(self):
        return ROOT / 'model/print_v5' / self.order

    @property
    def wall_limit(self):
        return WALL_LIMIT[self.material]


def _rows(order, rows):
    return [Part(order, name, body, source, material, flip) for name, body, source, material, flip in rows]


PARTS = (
    # order 2: the main set; every part prints top face down (print_v5 README)
    *_rows('order2', [
        ('plate_L', 'PLATE_L_SPLIT_V1', MODEL, MJF, True),
        ('plate_R', 'PLATE_R_SPLIT_V1', MODEL, MJF, True),
        ('spine', 'PLATE_SPINE_V1', MODEL, MJF, True),
        ('ctrl_bracket', 'CTRL_BRACKET_SPLIT_V1', MODEL, MJF, True),
        ('cover_L', 'COVER_L_DRAFT_TBD', MODEL, RESIN, True),
        ('cover_T', 'COVER_T_DRAFT_TBD', MODEL, RESIN, True),
        ('cover_R', 'COVER_R_DRAFT_TBD', MODEL, RESIN, True),
    ]),
    # order 1: test parts. Snap bracket trial (tools/ctrl_v5.py TRIALS): B = production, A shallower, C deeper
    *_rows('order1', [
        ('sw_hole_coupon', 'SW_HOLE_SAMPLE', SAMPLE, MJF, True),
        ('boss_tab', 'BOSS_TAB_SAMPLE', SAMPLE, RESIN, False),
        ('seam_coupon_L', 'SEAM_COUPON_L_V4', MODEL, MJF, True),
        ('seam_coupon_R', 'SEAM_COUPON_R_V4', MODEL, MJF, True),
        ('mount_L', 'MOUNT_L_PAIR_V3', MODEL, MJF, False),
        ('mount_R', 'MOUNT_R_PAIR_V3', MODEL, MJF, False),
        ('mount_H02_SO3', 'MOUNT_H02_SO3_MIN_V2', MODEL, MJF, False),
        ('mount_H03_SO6', 'MOUNT_H03_SO6_MIN_V2', MODEL, MJF, False),
        ('ctrl_bracket', 'CTRL_BRACKET_SPLIT_V1', MODEL, MJF, True),
        ('ctrl_snap_A', 'CTRL_SNAP_TRIAL_A', TRIALS, MJF, True),
        ('ctrl_snap_C', 'CTRL_SNAP_TRIAL_C', TRIALS, MJF, True),
        # rear rest blocks on the PSD60 rear-wall bosses (build_seam_v5.py REAR_RESTS): nominal height and the two
        # variants, three prints each; the height that fits at trial assembly is used as it is (no order-2 part)
        ('rear_rest', 'REAR_REST_1_V5', MODEL, MJF, False),
        ('rear_rest_lo', 'REAR_REST_TRIAL_LO', TRIALS, MJF, False),
        ('rear_rest_hi', 'REAR_REST_TRIAL_HI', TRIALS, MJF, False),
    ]),
)
# CAD bodies with the shape of a listed part, printed from that part's file (the guide shows them, no file of their own)
SAME_PRINT = {'REAR_REST_2_V5': 'REAR_REST_1_V5', 'REAR_REST_3_V5': 'REAR_REST_1_V5'}


def parts(order):
    """The rows of one order, in record order."""
    assert order in ORDERS, order
    return [p for p in PARTS if p.order == order]


def by_file(order):
    return {p.file: p for p in parts(order)}


def mount_part(body):
    """The order-1 part printing a mount body (verify_seam_v5.py sections the STL)."""
    return next(p for p in parts('order1') if p.body == body)
