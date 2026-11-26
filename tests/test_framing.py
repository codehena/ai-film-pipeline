"""Regression tests for head-safe framing (FAILURES.md F-19: 16:9 cut the boys' heads)."""
import pytest

from pipeline import render

SQ = (1024, 1024)
WIDE, TALL = 16 / 9, 9 / 16
# the measured s04/s05 problem: two standing boys, heads in the top quarter of a square keyframe
HEADS_TOP = (0.26, 0.06, 0.74, 0.30)   # both heads, measured on s04 (x 0.26-0.74)


def inside(box, window, src=SQ):
    x, y, w, h = window
    return (box[0] * src[0] >= x and box[1] * src[1] >= y and
            box[2] * src[0] <= x + w and box[3] * src[1] <= y + h)


def test_the_old_centred_crop_cut_the_heads():
    assert not inside(HEADS_TOP, render.crop_window(*SQ, WIDE))         # the bug, measured


@pytest.mark.parametrize("ratio", [WIDE, TALL])
def test_safe_box_stays_inside_both_crops(ratio):
    assert inside(HEADS_TOP, render.crop_window(*SQ, ratio, safe_box=HEADS_TOP))


def test_margin_is_kept_when_it_fits():
    x, y, w, h = render.crop_window(*SQ, WIDE, safe_box=HEADS_TOP)
    assert y <= (HEADS_TOP[1] - render.SAFE_MARGIN) * 1024 + 1


def test_box_taller_than_the_window_keeps_heads_not_feet():
    tall = (0.3, 0.05, 0.7, 0.95)                    # full figures, head to toe
    x, y, w, h = render.crop_window(*SQ, WIDE, safe_box=tall)
    assert y == 0                                    # top kept (heads); feet are what gets cut


def test_window_never_leaves_the_image():
    for box in [(0.0, 0.0, 0.1, 0.1), (0.9, 0.9, 1.0, 1.0), (0.0, 0.0, 1.0, 1.0)]:
        for r in (WIDE, TALL):
            x, y, w, h = render.crop_window(*SQ, r, safe_box=box)
            assert 0 <= x <= 1024 - w and 0 <= y <= 1024 - h


def test_zoom_is_clamped_so_the_box_stays_visible():
    box = (0.2, 0.1, 0.8, 0.5)                       # 60% of the window wide
    move, fy = render.fit_move(render.Move((1.0, 1.4), (0.5, 0.5)), box)
    assert max(move.zoom) <= 1 / 0.6 + 1e-9
    for z, d in zip(move.zoom, move.drift):
        half = 0.5 / z
        assert d - half <= 0.2 + 1e-9 and d + half >= 0.8 - 1e-9          # box inside horizontally
    half = 0.5 / max(move.zoom)
    assert fy - half <= 0.1 + 1e-9 and fy + half >= 0.5 - 1e-9            # and vertically


def test_pan_is_limited_to_where_the_box_still_fits():
    box = (0.35, 0.2, 0.65, 0.6)
    move, _ = render.fit_move(render.Move((1.12, 1.12), (0.30, 0.70)), box)
    half = 0.5 / 1.12
    assert move.drift[0] >= 0.65 - half - 1e-9 and move.drift[1] <= 0.35 + half + 1e-9


def test_no_box_means_no_change():
    m = render.Move((1.0, 1.1), (0.5, 0.5))
    assert render.fit_move(m, None) == (m, 0.5)


def test_box_in_window_coordinates():
    window = render.crop_window(*SQ, WIDE, safe_box=HEADS_TOP)
    b = render.box_in_window(HEADS_TOP, SQ, window)
    assert all(0 <= v <= 1 for v in b) and b[0] < b[2] and b[1] < b[3]


def test_too_wide_box_is_centred_not_left_aligned():
    wide = (0.1, 0.2, 0.9, 0.4)                      # wider than a 9:16 window (56%)
    x, y, w, h = render.crop_window(*SQ, TALL, safe_box=wide)
    assert abs((x + w / 2) - 512) <= 1               # centred: neither person favoured


def test_margin_shrinks_before_the_box_is_cut():
    box = (0.10, 0.21, 0.92, 0.77)                   # s08: heads to jebena, 56% of the height
    assert inside(box, render.crop_window(*SQ, WIDE, safe_box=box))   # fits without its margin


def test_segment_plan_changes_only_when_the_framing_changes(monkeypatch):
    m = render.Move((1.0, 1.1), (0.5, 0.5))
    a = render.still_plan(SQ, "16:9", (0.5, 0.5), m, HEADS_TOP)
    assert render.still_plan(SQ, "16:9", (0.5, 0.5), m, HEADS_TOP) == a          # stable
    # a rule change that does NOT move any pixels keeps the key (no needless rebuild):
    monkeypatch.setattr(render, "SAFE_MARGIN", 0.06)            # window already pinned at the top
    assert render.still_plan(SQ, "16:9", (0.5, 0.5), m, HEADS_TOP) == a
    # a rule change that DOES change what is shown changes the key (no stale segment):
    monkeypatch.setattr(render, "fit_move", lambda move, box: (render.Move((1.0, 1.0), (0.5, 0.5)), 0.4))
    assert render.still_plan(SQ, "16:9", (0.5, 0.5), m, HEADS_TOP) != a
