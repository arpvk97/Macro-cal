from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# --- Business rules (tweak to taste) ---
PROTEIN_PER_100_KCAL_MIN = 7      # g per 100 kcal
SUGAR_PCT_OF_CARBS_MAX    = 30     # %
SATFAT_PCT_OF_FAT_MAX     = 33     # %

LOW_DENSITY_MAX_KCAL_PER_G  = 0.6
MOD_DENSITY_MAX_KCAL_PER_G  = 1.5


def _f(x, default=0.0):
    """Robust float cast."""
    try:
        return float(x)
    except Exception:
        return default


def _safe_div(a, b):
    """Division that returns None if invalid or divide-by-zero."""
    try:
        a = float(a); b = float(b)
        return a / b if b != 0 else None
    except Exception:
        return None


def evaluate_macros(serving_g, calories, protein, carbs, sugars, fibre, fat, satfat, sodium):
    # --- ingest ---
    serving_g = _f(serving_g)
    calories  = _f(calories)
    protein   = _f(protein)
    carbs     = _f(carbs)
    sugars    = _f(sugars)
    fibre     = _f(fibre)
    fat       = _f(fat)
    satfat    = _f(satfat)
    sodium    = _f(sodium)

    # --- per-gram metrics ---
    kcal_per_g    = _safe_div(calories, serving_g)
    protein_per_g = _safe_div(protein, serving_g)
    carbs_per_g   = _safe_div(carbs, serving_g)
    sugars_per_g  = _safe_div(sugars, serving_g)
    fibre_per_g   = _safe_div(fibre, serving_g)
    fat_per_g     = _safe_div(fat, serving_g)
    satfat_per_g  = _safe_div(satfat, serving_g)
    sodium_per_g  = _safe_div(sodium, serving_g)

    # --- quality metrics (density/ratios) ---
    protein_per_100kcal = _safe_div(protein, calories)
    protein_per_100kcal = protein_per_100kcal * 100 if protein_per_100kcal is not None else None

    sugar_pct_of_carbs = _safe_div(sugars, carbs)
    sugar_pct_of_carbs = sugar_pct_of_carbs * 100 if sugar_pct_of_carbs is not None else None

    satfat_pct_of_fat = _safe_div(satfat, fat)
    satfat_pct_of_fat = satfat_pct_of_fat * 100 if satfat_pct_of_fat is not None else None

    # --- energy density flag ---
    if kcal_per_g is None:
        energy_density_flag = ""
    elif kcal_per_g < LOW_DENSITY_MAX_KCAL_PER_G:
        energy_density_flag = "Low"
    elif kcal_per_g <= MOD_DENSITY_MAX_KCAL_PER_G:
        energy_density_flag = "Moderate"
    else:
        energy_density_flag = "High"

    # --- rules: explicit pass/fail messages ---
    rules = [
        ("Protein density is strong",         "Protein density is weak",
         (protein_per_100kcal is not None) and (protein_per_100kcal >= PROTEIN_PER_100_KCAL_MIN)),

        ("Sugar share of carbs is controlled","Sugar share of carbs is high",
         (sugar_pct_of_carbs is not None) and (sugar_pct_of_carbs <= SUGAR_PCT_OF_CARBS_MAX)),

        ("Saturated fat share is controlled", "Saturated fat share is high",
         (satfat_pct_of_fat is not None) and (satfat_pct_of_fat <= SATFAT_PCT_OF_FAT_MAX)),
    ]

    reasons   = [pos for (pos, neg, ok) in rules if ok]
    watchouts = [neg for (pos, neg, ok) in rules if not ok]
    pass_count = sum(1 for (_, _, ok) in rules if ok)

    verdict = "Good" if pass_count == 3 else ("Okay" if pass_count == 2 else "Limit")

    # --- payload for the template / API ---
    return {
        "per_gram": {
            "kcal_per_g": kcal_per_g,
            "protein_per_g": protein_per_g,
            "carbs_per_g": carbs_per_g,
            "sugars_per_g": sugars_per_g,
            "fibre_per_g": fibre_per_g,
            "fat_per_g": fat_per_g,
            "satfat_per_g": satfat_per_g,
            "sodium_mg_per_g": sodium_per_g,
        },
        "quality": {
            "protein_per_100kcal_g": protein_per_100kcal,
            "sugar_pct_of_carbs": sugar_pct_of_carbs,
            "satfat_pct_of_fat": satfat_pct_of_fat,
            "energy_density_flag": energy_density_flag,
        },
        "verdict": verdict,
        "reasons": reasons,
        "watchouts": watchouts,
    }


# --- Routes ------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        form = request.form
        result = evaluate_macros(
            form.get("serving_g"),
            form.get("calories"),
            form.get("protein"),
            form.get("carbs"),
            form.get("sugars"),
            form.get("fibre"),
            form.get("fat"),
            form.get("satfat"),
            form.get("sodium"),
        )
    return render_template("index.html", result=result)


@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    data = request.get_json(force=True, silent=True) or {}
    result = evaluate_macros(
        data.get("serving_g"),
        data.get("calories"),
        data.get("protein"),
        data.get("carbs"),
        data.get("sugars"),
        data.get("fibre"),
        data.get("fat"),
        data.get("satfat"),
        data.get("sodium"),
    )
    return jsonify(result)


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
