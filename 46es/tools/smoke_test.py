"""Run the generator's pure-Python geometry without SolidCraft and compare it with the committed records.

Run from any directory: python -B 46es/tools/smoke_test.py
CI runs this beside check_repository.py, so a change to the mount, bracket or cover-window logic that would
change the CAD fails the pull request even though the CAD kernel is not available there.
"""
import json
import time

from common import ROOT
import ctrl_v5
from mounts_v5 import profiles, expected_volume
from build_seam_v5 import cover_windows, switch_openings
import seam_v5


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))


def main():
    started = time.perf_counter()
    verification = read('inspection/data/seam-v5-verification.json')
    order1 = {r['body']: r for r in read('inspection/data/seam-v5-trial-print-set.json')}
    order2 = {r['body']: r for r in read('inspection/data/seam-v5-print-set.json')}

    # Mounts: the layered plan volume must equal the one verify_seam_v5 recorded for the committed CAD.
    mounts = profiles()
    for suffix, profile in mounts.items():
        name = profile['mount']
        recorded = verification['mounts'][name]['layered_volume_mm3']
        layered = expected_volume(profile)
        assert abs(layered - recorded) < 0.002, f'{name}: layered volume {layered:.3f} != recorded {recorded}'
        cad = order1[name]['cad_volume_mm3']
        assert abs(cad - layered) / layered < 0.002, f'{name}: order-1 CAD volume {cad} far from the profile {layered:.3f}'

    # Controller bracket (production, order 2) and the seats of the snap coupon (order 1): keep-outs and wall checks,
    # volume estimate vs the export records.
    designs = {ctrl_v5.BODY: ctrl_v5.bracket()}
    designs.update({f'{ctrl_v5.TRIAL_BODY}_{seat}': ctrl_v5.bracket(**spec) for seat, spec, _ in ctrl_v5.trial_seats()})
    for design in designs.values():
        ctrl_v5.check(design)
    for body, estimate, record in ((ctrl_v5.BODY, ctrl_v5.expected_volume(), order2),
                                   (ctrl_v5.TRIAL_BODY, ctrl_v5.trial_volume(), order1)):
        cad = record[body]['cad_volume_mm3']
        assert abs(cad - estimate) / estimate < 0.015, f'{body}: exported CAD volume {cad} far from the estimate {estimate:.3f}'

    # Front seam: every variant passes its wall rules; the production screw is where the Front mount pad is drilled.
    openings = switch_openings()
    seams = {'production': seam_v5.check(seam_v5.PRODUCTION, openings)}
    seams.update({name: seam_v5.check(variant) for name, variant in seam_v5.VARIANTS.items()})
    assert all(len(seam_v5.coupon_blank(body)) == 8 for body in seam_v5.COUPON_PIECES)

    # Cover silhouette window: the generator asserts keycap coverage and the keep-outs itself.
    windows = cover_windows()

    print(f'OK: {len(mounts)} mount profiles, {len(designs)} bracket seats, {len(seams)} seam variants, {len(windows)} cover windows '
          f'({time.perf_counter() - started:.1f} s, no SolidCraft)')


if __name__ == '__main__':
    main()
