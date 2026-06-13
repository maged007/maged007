"""
AutoMark CLI — generate an automotive story collage from the command line.

Usage:
  python main.py image1.jpg image2.jpg [--output ./out] [--open]

Each image can be prefixed with a type tag:
  python main.py front_34_exterior:car1.jpg side_exterior:car2.jpg
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from core import (
    VehicleAnalyzer,
    ImageScoringEngine,
    LayoutSelector,
    Renderer,
    QualityValidator,
    ExportEngine,
    IMAGE_TYPES,
)


def parse_image_arg(arg: str) -> tuple[str, str]:
    """Parse 'type:path' or just 'path', returning (path, type)."""
    if ":" in arg:
        maybe_type, maybe_path = arg.split(":", 1)
        if maybe_type in IMAGE_TYPES and os.path.exists(maybe_path):
            return maybe_path, maybe_type
    return arg, "auto"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AutoMark — Automotive Story Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("images", nargs="+", help="Image paths (1–6), optionally prefixed with type:path")
    parser.add_argument("-o", "--output", default="./outputs", help="Output directory (default: ./outputs)")
    parser.add_argument("--filename", default=None, help="Output filename (default: auto-generated)")
    parser.add_argument("-c", "--caption", default=None, help="Sale caption to overlay on the hero image (auto-summarised if > 60 words)")
    parser.add_argument("--open", action="store_true", help="Open the result after generation")
    parser.add_argument("--verbose", action="store_true", help="Print scoring details")
    args = parser.parse_args()

    if not 1 <= len(args.images) <= 6:
        print(f"Error: provide 1–6 images, got {len(args.images)}", file=sys.stderr)
        return 1

    image_pairs = [parse_image_arg(a) for a in args.images]

    # Validate paths
    for path, _ in image_pairs:
        if not os.path.exists(path):
            print(f"Error: file not found: {path}", file=sys.stderr)
            return 1

    print("AutoMark — Automotive Story Generator")
    print("=" * 42)

    analyzer  = VehicleAnalyzer()
    scorer    = ImageScoringEngine()
    selector  = LayoutSelector()
    renderer  = Renderer()
    validator = QualityValidator()
    exporter  = ExportEngine()

    # Analyse
    print(f"\nAnalysing {len(image_pairs)} image(s)…")
    analyses = []
    for path, user_type in image_pairs:
        a = analyzer.analyze(path, user_type=user_type)
        analyses.append(a)
        print(f"  [{IMAGE_TYPES[a.image_type][0]:25s}]  {Path(path).name}")

    # Score
    scored = scorer.score(analyses)
    print("\nScoring:")
    for s in scored:
        hero_tag = " ← HERO" if s.rank == 0 else ""
        print(f"  {s.final_score:6.1f}  {Path(s.analysis.path).name}{hero_tag}")
        if args.verbose:
            print(f"         base={s.base_score}  quality_bonus={s.quality_bonus:+.2f}")

    # Select layout
    layout = selector.select(scored)
    print(f"\nLayout: {layout['id']}")

    # Render
    print("Rendering…")
    if args.caption:
        from core import TextOverlayEngine
        summary = TextOverlayEngine().summarize(args.caption)
        n_in, n_out = len(args.caption.split()), len(summary.split())
        if n_out < n_in:
            print(f"Caption summarised: {n_in} → {n_out} words")
    canvas = renderer.render(layout, scored, caption=args.caption)

    # Validate
    result = validator.validate(canvas)
    if not result.passed:
        print("\nValidation FAILED:", file=sys.stderr)
        for issue in result.issues:
            print(f"  ✗ {issue}", file=sys.stderr)
        return 1

    if result.warnings:
        for w in result.warnings:
            print(f"  ⚠ {w}")

    # Export
    out_path = exporter.save(canvas, args.output, args.filename)
    print(f"\nSaved: {out_path}")

    if args.open:
        import subprocess, platform
        cmd = {"Darwin": "open", "Windows": "start", "Linux": "xdg-open"}.get(platform.system(), "xdg-open")
        subprocess.Popen([cmd, out_path])

    return 0


if __name__ == "__main__":
    sys.exit(main())
