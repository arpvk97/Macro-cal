from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def evaluate_macros(serving_g, calories, protein, carbs, sugars, fibre, fat, satfat, sodium):
    def safe_div(a, b):
        try:
            a = float(a); b = float(b)
            return a / b if b != 0 else None
        except:
            return None
    def f(x):
        try: return float(x)
        except: return 0.0

    serving_g = f(serving_g); calories = f(calories); protein = f(protein)
    carbs = f(carbs); sugars = f(sugars); fibre = f(fibre)
    fat = f(fat); satfat = f(satfat); sodium = f(sodium)

    kcal_per_g    = safe_div(calories, serving_g)
    protein_per_g = safe_div(protein, serving_g)
    carbs_per_g   = safe_div(carbs, serving_g)
    sugars_per_g  = safe_div(sugars, serving_g)
    fibre_per_g   = safe_div(fibre, serving_g)
    fat_per_g     = safe_div(fat, serving_g)
    satfat_per_g  = safe_div(satfat, serving_g)
    sodium_per_g  = safe_div(sodium, serving_g)

    protein_per_100kcal = safe_div(protein, calories)
    protein_per_100kcal = protein_per_100kcal * 100 if protein_per_100kcal is not None else None

    sugar_pct_of_carbs = safe_div(sugars, carbs)
    sugar_pct_of_carbs = sugar_pct_of_carbs * 100 if sugar_pct_of_carbs is not None else None

    satfat_pct_of_fat = safe_div(satfat, fat)
    satfat_pct_of_fat = satfat_pct_of_fat * 100 if satfat_pct_of_fat is not None else None

    if kcal_per_g is None: energy_density_flag = ""
    elif kcal_per_g < 0.6: energy_density_flag = "Low"
    elif kcal_per_g <= 1.5: energy_density_flag = "Moderate"
    else: energy_density_flag = "High"

    checks = {
        "Protein density is strong": protein_per_100kcal is not None and protein_per_100kcal >= 7,
        "Sugar share of carbs is controlled": sugar_pct_of_carbs is not None and sugar_pct_of_carbs <= 30,
        "Saturated fat share is controlled": satfat_pct_of_fat is not None and satfat_pct_of_fat <= 33,
    }
    pass_count = sum(1 for ok in checks.values() if ok)
    verdict = "Good" if pass_count == 3 else "Okay" if pass_count >= 2 else "Limit"

    return {
        "per_gram": {
            "kcal_per_g": kcal_per_g, "protein_per_g": protein_per_g, "carbs_per_g": carbs_per_g,
            "sugars_per_g": sugars_per_g, "fibre_per_g": fibre_per_g, "fat_per_g": fat_per_g,
            "satfat_per_g": satfat_per_g, "sodium_mg_per_g": sodium_per_g,
        },
        "quality": {
            "protein_per_100kcal_g": protein_per_100kcal,
            "sugar_pct_of_carbs": sugar_pct_of_carbs,
            "satfat_pct_of_fat": satfat_pct_of_fat,
            "energy_density_flag": energy_density_flag,
        },
        "verdict": verdict,
        "reasons": [k for k, v in checks.items() if v],
        "watchouts": [k for k, v in checks.items() if not v],
    }

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        form = request.form
        result = evaluate_macros(
            form.get("serving_g"), form.get("calories"), form.get("protein"),
            form.get("carbs"), form.get("sugars"), form.get("fibre"),
            form.get("fat"), form.get("satfat"), form.get("sodium")
        )
    return render_template("index.html", result=result)

@app.route("/api/evaluate", methods=["POST"])
def api_evaluate():
    data = request.get_json(force=True, silent=True) or {}
    result = evaluate_macros(
        data.get("serving_g"), data.get("calories"), data.get("protein"),
        data.get("carbs"), data.get("sugars"), data.get("fibre"),
        data.get("fat"), data.get("satfat"), data.get("sodium")
    )
    return jsonify(result)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
