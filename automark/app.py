"""
AutoMark Flask web application.
Handles image upload, pipeline orchestration, and file download.
"""

from __future__ import annotations

import os
import uuid
import json
from pathlib import Path

from flask import (
    Flask,
    request,
    jsonify,
    send_file,
    render_template,
    abort,
)
from werkzeug.utils import secure_filename

from core import (
    VehicleAnalyzer,
    ImageScoringEngine,
    LayoutSelector,
    Renderer,
    QualityValidator,
    ExportEngine,
    IMAGE_TYPES,
)

# ------------------------------------------------------------------ #
# App setup
# ------------------------------------------------------------------ #

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic", "heif"}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB total

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "automark-dev-secret")

# Pipeline singletons
_analyzer = VehicleAnalyzer()
_scorer = ImageScoringEngine()
_selector = LayoutSelector()
_renderer = Renderer()
_validator = QualityValidator()
_exporter = ExportEngine()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #

@app.route("/")
def index():
    image_types = {k: v[0] for k, v in IMAGE_TYPES.items() if k != "auto"}
    return render_template("index.html", image_types=image_types)


@app.route("/api/analyze", methods=["POST"])
def analyze():
    """
    Accept one image file + optional type tag.
    Returns analysis metadata (used by the frontend for preview info).
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    user_type = request.form.get("type", "auto")

    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    session_id = request.form.get("session_id") or str(uuid.uuid4())
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(file.filename)
    # Prefix with UUID to avoid collisions
    unique_name = f"{uuid.uuid4().hex[:8]}_{filename}"
    file_path = session_dir / unique_name
    file.save(str(file_path))

    try:
        analysis = _analyzer.analyze(str(file_path), user_type=user_type)
        _, base_score = IMAGE_TYPES.get(analysis.image_type, ("Unknown", 50))
        return jsonify({
            "session_id": session_id,
            "file_id": unique_name,
            "image_type": analysis.image_type,
            "type_label": IMAGE_TYPES.get(analysis.image_type, ("Unknown", 0))[0],
            "base_score": base_score,
            "width": analysis.width,
            "height": analysis.height,
            "orientation": analysis.orientation,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    Accept a JSON payload describing the uploaded images and generate the collage.

    Payload:
    {
      "session_id": "...",
      "images": [
        {"file_id": "...", "type": "front_34_exterior"},
        ...
      ]
    }
    """
    data = request.get_json(force=True)
    session_id = data.get("session_id")
    images_meta = data.get("images", [])
    caption = (data.get("caption") or "").strip()

    if not session_id or not images_meta:
        return jsonify({"error": "Missing session_id or images"}), 400
    if not 1 <= len(images_meta) <= 4:
        return jsonify({"error": "Must provide 1–4 images"}), 400

    session_dir = UPLOAD_DIR / session_id
    if not session_dir.exists():
        return jsonify({"error": "Session not found"}), 404

    # Build analyses
    analyses = []
    for meta in images_meta:
        file_path = session_dir / meta["file_id"]
        if not file_path.exists():
            return jsonify({"error": f"File not found: {meta['file_id']}"}), 404
        try:
            analysis = _analyzer.analyze(str(file_path), user_type=meta.get("type", "auto"))
            analyses.append(analysis)
        except Exception as e:
            return jsonify({"error": f"Analysis failed for {meta['file_id']}: {e}"}), 500

    variation   = int(data.get("variation", 0))
    hero_file_id = data.get("hero_file_id")

    try:
        scored = _scorer.score(analyses)

        # Hero override: user can pin which image goes in the hero slot
        if hero_file_id:
            hero_idx = next(
                (i for i, s in enumerate(scored) if Path(s.analysis.path).name == hero_file_id),
                None,
            )
            if hero_idx is not None and hero_idx > 0:
                hero = scored.pop(hero_idx)
                scored.insert(0, hero)
                for i, s in enumerate(scored):
                    s.rank = i

        # Variation: shuffle secondary images for different arrangements on regenerate
        if variation > 0 and len(scored) > 1:
            import random
            rng = random.Random(variation)
            rest = scored[1:]
            rng.shuffle(rest)
            scored = [scored[0]] + rest
            for i, s in enumerate(scored):
                s.rank = i

        layout = _selector.select(scored)
        canvas = _renderer.render(layout, scored, caption=caption)
        validation = _validator.validate(canvas)

        final_caption = caption  # no longer auto-summarised

        if not validation.passed:
            return jsonify({"error": "Validation failed", "issues": validation.issues}), 500

        output_filename = f"{session_id}.png"
        output_path = _exporter.save(canvas, str(OUTPUT_DIR), output_filename)

        # Build scoring info for the response
        scores_info = []
        for s in scored:
            scores_info.append({
                "file_id": Path(s.analysis.path).name,
                "type": s.analysis.image_type,
                "type_label": IMAGE_TYPES.get(s.analysis.image_type, ("Unknown", 0))[0],
                "base_score": s.base_score,
                "quality_bonus": s.quality_bonus,
                "final_score": s.final_score,
                "rank": s.rank,
                "is_hero": s.rank == 0,
            })

        return jsonify({
            "session_id": session_id,
            "output_file": output_filename,
            "layout_id": layout["id"],
            "warnings": validation.warnings,
            "scores": scores_info,
            "caption": {
                "original_words": len(caption.split()) if caption else 0,
                "final_words": len(final_caption.split()) if final_caption else 0,
                "summarized": bool(caption) and final_caption != caption,
                "text": final_caption,
            },
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<filename>")
def download(filename: str):
    """Stream the generated PNG to the client."""
    safe = secure_filename(filename)
    file_path = OUTPUT_DIR / safe
    if not file_path.exists():
        abort(404)
    return send_file(
        str(file_path),
        mimetype="image/png",
        as_attachment=True,
        download_name=safe,
    )


@app.route("/api/preview/<filename>")
def preview(filename: str):
    """Return a JPEG preview (smaller, for the result panel)."""
    from PIL import Image as PILImage
    safe = secure_filename(filename)
    file_path = OUTPUT_DIR / safe
    if not file_path.exists():
        abort(404)
    img = PILImage.open(str(file_path))
    preview_bytes = _exporter.to_jpeg_preview(img, quality=88)
    from flask import Response
    return Response(preview_bytes, mimetype="image/jpeg")


# ------------------------------------------------------------------ #

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
