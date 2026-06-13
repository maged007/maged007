"""
Layout library for the Automotive Story Generator.
All coordinates follow the spec: 1080x1620 canvas with 16px outer margin and 8px gutters.
"""

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1620
OUTER_MARGIN = 16
GUTTER = 8
CORNER_RADIUS = 24
SHADOW_BLUR = 12
SHADOW_OFFSET_Y = 4
SHADOW_OPACITY = 40  # 0-255

LAYOUTS: dict[str, dict] = {
    "layout_1": {
        "id": "layout_1",
        "image_count": 1,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 1048, "h": 1588},
        ],
    },
    "layout_2a": {
        "id": "layout_2a",
        "image_count": 2,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 1048, "h": 950},
            {"slot": 2, "x": 16, "y": 974, "w": 1048, "h": 630},
        ],
    },
    "layout_2b": {
        "id": "layout_2b",
        "image_count": 2,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 680, "h": 1588},
            {"slot": 2, "x": 704, "y": 16, "w": 360, "h": 1588},
        ],
    },
    "layout_3a": {
        "id": "layout_3a",
        "image_count": 3,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 1048, "h": 850},
            {"slot": 2, "x": 16, "y": 874, "w": 520, "h": 730},
            {"slot": 3, "x": 544, "y": 874, "w": 520, "h": 730},
        ],
    },
    "layout_3b": {
        "id": "layout_3b",
        "image_count": 3,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 700, "h": 1588},
            {"slot": 2, "x": 724, "y": 16, "w": 340, "h": 790},
            {"slot": 3, "x": 724, "y": 814, "w": 340, "h": 790},
        ],
    },
    "layout_4a": {
        "id": "layout_4a",
        "image_count": 4,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 1048, "h": 750},
            {"slot": 2, "x": 16, "y": 774, "w": 520, "h": 410},
            {"slot": 3, "x": 544, "y": 774, "w": 520, "h": 410},
            {"slot": 4, "x": 16, "y": 1192, "w": 1048, "h": 412},
        ],
    },
    "layout_4b": {
        "id": "layout_4b",
        "image_count": 4,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 700, "h": 900},
            {"slot": 2, "x": 724, "y": 16, "w": 340, "h": 446},
            {"slot": 3, "x": 724, "y": 470, "w": 340, "h": 446},
            {"slot": 4, "x": 16, "y": 924, "w": 1048, "h": 680},
        ],
    },
    "layout_5a": {
        "id": "layout_5a",
        "image_count": 5,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 1048, "h": 700},
            {"slot": 2, "x": 16, "y": 724, "w": 344, "h": 430},
            {"slot": 3, "x": 368, "y": 724, "w": 344, "h": 430},
            {"slot": 4, "x": 720, "y": 724, "w": 344, "h": 430},
            {"slot": 5, "x": 16, "y": 1162, "w": 1048, "h": 442},
        ],
    },
    "layout_5b": {
        "id": "layout_5b",
        "image_count": 5,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 680, "h": 950},
            {"slot": 2, "x": 704, "y": 16, "w": 360, "h": 470},
            {"slot": 3, "x": 704, "y": 494, "w": 360, "h": 472},
            {"slot": 4, "x": 16, "y": 974, "w": 520, "h": 630},
            {"slot": 5, "x": 544, "y": 974, "w": 520, "h": 630},
        ],
    },
    "layout_6a": {
        "id": "layout_6a",
        "image_count": 6,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 1048, "h": 700},
            {"slot": 2, "x": 16, "y": 724, "w": 344, "h": 430},
            {"slot": 3, "x": 368, "y": 724, "w": 344, "h": 430},
            {"slot": 4, "x": 720, "y": 724, "w": 344, "h": 430},
            {"slot": 5, "x": 16, "y": 1162, "w": 520, "h": 442},
            {"slot": 6, "x": 544, "y": 1162, "w": 520, "h": 442},
        ],
    },
    "layout_6b": {
        "id": "layout_6b",
        "image_count": 6,
        "slots": [
            {"slot": 1, "x": 16, "y": 16, "w": 680, "h": 900},
            {"slot": 2, "x": 704, "y": 16, "w": 360, "h": 296},
            {"slot": 3, "x": 704, "y": 320, "w": 360, "h": 296},
            {"slot": 4, "x": 704, "y": 624, "w": 360, "h": 292},
            {"slot": 5, "x": 16, "y": 924, "w": 520, "h": 680},
            {"slot": 6, "x": 544, "y": 924, "w": 520, "h": 680},
        ],
    },
}

# Hero slot is always slot 1 in every layout (largest, highest-scoring image goes here)
HERO_SLOT = 1

# Maps image count to available layout IDs.
# Only story-optimised (portrait-hero, top-to-bottom) layouts included.
LAYOUTS_BY_COUNT: dict[int, list[str]] = {
    1: ["layout_1"],
    2: ["layout_2a"],
    3: ["layout_3a"],
    4: ["layout_4a"],
}


def get_slot_area(slot: dict) -> int:
    return slot["w"] * slot["h"]


def get_hero_slot(layout_id: str) -> dict:
    return LAYOUTS[layout_id]["slots"][0]
