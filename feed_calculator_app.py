
from flask import Flask, request, render_template_string

app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<title>Cattle Feed Calculator</title>
<h2>Cattle Feed Calculator</h2>
<form method="post">
  <label>Body Weight (kg):</label><br>
  <input name="body_weight" required><br><br>

  <label>Stage (growth, maintenance, lactating, breeding, pregnant):</label><br>
  <input name="stage" required><br><br>

  <label>If lactating: Milk yield (kg):</label><br>
  <input name="milk_yield"><br><br>

  <label>If lactating: Fat %:</label><br>
  <input name="fat_pct"><br><br>

  <label>Dry Matter Requirement (% of BW):</label><br>
  <input name="dm_pct" required><br><br>

  <h4>Green Roughage - Non-legume</h4>
  <label>Name:</label><input name="green_non_legume_name" required><br>
  <label>TDN %:</label><input name="green_non_legume_tdn" required><br>
  <label>DCP %:</label><input name="green_non_legume_dcp" required><br>
  <label>Moisture %:</label><input name="green_non_legume_moisture" required><br><br>

  <h4>Green Roughage - Legume (Optional)</h4>
  <label>Name:</label><input name="green_legume_name"><br>
  <label>TDN %:</label><input name="green_legume_tdn"><br>
  <label>DCP %:</label><input name="green_legume_dcp"><br>
  <label>Moisture %:</label><input name="green_legume_moisture"><br><br>

  <h4>Dry Roughage</h4>
  <label>Name:</label><input name="dry_name" required><br>
  <label>TDN %:</label><input name="dry_tdn" required><br>
  <label>DCP %:</label><input name="dry_dcp" required><br>
  <label>Moisture %:</label><input name="dry_moisture" required><br><br>

  <h4>Concentrate Mixture</h4>
  <label>TDN %:</label><input name="conc_tdn" required><br>
  <label>DCP %:</label><input name="conc_dcp" required><br>
  <label>Moisture %:</label><input name="conc_moisture" required><br><br>

  <input type="submit" value="Calculate">
</form>
{% if result %}
  <h3>Result</h3>
  {{ result|safe }}
{% endif %}
"""

@app.route("/", methods=["GET", "POST"])
def calculate():
    if request.method == "POST":
        try:
            bw = float(request.form["body_weight"])
            stage = request.form["stage"].strip().lower()
            milk_yield = float(request.form.get("milk_yield") or 0)
            fat_pct = float(request.form.get("fat_pct") or 0)
            dm_pct = float(request.form["dm_pct"])

            # Inputs for feeds
            green_non_legume = {
                "name": request.form["green_non_legume_name"],
                "tdn": float(request.form["green_non_legume_tdn"]),
                "dcp": float(request.form["green_non_legume_dcp"]),
                "moisture": float(request.form["green_non_legume_moisture"]),
            }
            green_legume = {
                "name": request.form.get("green_legume_name") or "",
                "tdn": float(request.form.get("green_legume_tdn") or 0),
                "dcp": float(request.form.get("green_legume_dcp") or 0),
                "moisture": float(request.form.get("green_legume_moisture") or 0),
            }
            dry_roughage = {
                "name": request.form["dry_name"],
                "tdn": float(request.form["dry_tdn"]),
                "dcp": float(request.form["dry_dcp"]),
                "moisture": float(request.form["dry_moisture"]),
            }
            concentrate = {
                "tdn": float(request.form["conc_tdn"]),
                "dcp": float(request.form["conc_dcp"]),
                "moisture": float(request.form["conc_moisture"]),
            }

            mbw = bw ** 0.75
            dm_req = bw * dm_pct / 100

            # Maintenance & Lactation needs
            tdn_maint = 0.034 * mbw
            dcp_maint = 0.00284 * mbw

            fcm = milk_yield * (0.4 + 0.15 * fat_pct)
            tdn_lact = 0.33 * fcm
            dcp_lact = ((1.9 + 0.4 * fat_pct) * 14.28 / 100) * milk_yield

            tdn_total = tdn_maint + tdn_lact
            dcp_total = dcp_maint + dcp_lact

            # Dry Matter Distribution
            roughage_dm = dm_req * 2/3
            conc_dm = dm_req * 1/3

            dry_fodder_dm = roughage_dm * 2/3
            green_fodder_dm = roughage_dm * 1/3

            green_non_legume_dm = green_fodder_dm * 2/3
            green_legume_dm = green_fodder_dm * 1/3

            # Nutrient contributions from roughages
            def nutrient(dm, tdn, dcp):
                return dm * tdn / 100, dm * dcp / 100

            tdn_gnl, dcp_gnl = nutrient(green_non_legume_dm, green_non_legume["tdn"], green_non_legume["dcp"])
            tdn_gl, dcp_gl = nutrient(green_legume_dm, green_legume["tdn"], green_legume["dcp"])
            tdn_dry, dcp_dry = nutrient(dry_fodder_dm, dry_roughage["tdn"], dry_roughage["dcp"])

            tdn_from_rough = tdn_gnl + tdn_gl + tdn_dry
            dcp_from_rough = dcp_gnl + dcp_gl + dcp_dry

            tdn_needed = tdn_total - tdn_from_rough
            dcp_needed = dcp_total - dcp_from_rough

            conc_needed_tdn = tdn_needed / (concentrate["tdn"] / 100)
            conc_needed_dcp = dcp_needed / (concentrate["dcp"] / 100)
            conc_needed = max(conc_needed_tdn, conc_needed_dcp)

            result = f"""
            <b>Metabolic Body Weight:</b> {mbw:.2f} kg<br>
            <b>Dry Matter Required:</b> {dm_req:.2f} kg<br><br>
            <b>TDN Requirement:</b><br>
            - Maintenance: {tdn_maint:.2f} kg<br>
            - Lactation: {tdn_lact:.2f} kg<br>
            - <b>Total: {tdn_total:.2f} kg</b><br><br>
            <b>DCP Requirement:</b><br>
            - Maintenance: {dcp_maint:.2f} kg<br>
            - Lactation: {dcp_lact:.2f} kg<br>
            - <b>Total: {dcp_total:.2f} kg</b><br><br>
            <b>Estimated Concentrate Needed:</b> {conc_needed:.2f} kg (as fed)
            """
            return render_template_string(HTML_FORM, result=result)
        except Exception as e:
            return render_template_string(HTML_FORM, result=f"Error: {e}")
    return render_template_string(HTML_FORM)
