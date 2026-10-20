from typing import List, Dict, Any

CLINICAL_SUBSTITUTION_RULES: Dict[str, Dict[str, Any]] = {
    "statin_macrolide": {
        "problem": "CYP3A4 inhibition elevates statin concentrations to myotoxic/rhabdomyolysis levels.",
        "recommended_alternatives": [
            {"salt": "Rosuvastatin (Dose-Adjusted)", "brands": ["Rosuvas 5", "Rozavel 10"], "rationale": "Cleared via CYP2C9; not significantly impacted by CYP3A4 inhibitors."},
            {"salt": "Azithromycin / Amoxicillin", "brands": ["Augmentin 625", "Azithral 500"], "rationale": "Alternative antimicrobial regimen with minimal CYP3A4 inhibition."}
        ]
    },
    "dapt_gi_bleed": {
        "problem": "Dual antiplatelets plus NSAIDs cause high-risk gastrointestinal ulceration and bleeding.",
        "recommended_alternatives": [
            {"salt": "Paracetamol", "brands": ["Dolo 650", "Calpol 500"], "rationale": "Non-antiplatelet analgesic with minimal gastric mucosal ulceration risk."},
            {"salt": "Pantoprazole Co-therapy", "brands": ["Pan 40", "Pantocid 40"], "rationale": "Preferred PPI for antiplatelet co-prescription (low CYP2C19 interaction)."}
        ]
    },
    "ras_hyperkalemia": {
        "problem": "Simultaneous ARB/ACEi and potassium-sparing diuretics trigger severe hyperkalemia.",
        "recommended_alternatives": [
            {"salt": "Amlodipine (CCB)", "brands": ["Stamlo 5", "Amlong 5"], "rationale": "Potent blood pressure reduction without altering serum potassium kinetics."},
            {"salt": "Torsemide / Chlorthalidone", "brands": ["Dytor 10"], "rationale": "Potassium-neutral or kaliuretic diuretic options."}
        ]
    },
    "sulfonylurea_hypoglycemia": {
        "problem": "Fluoroquinolones or Aspirin potentiate sulfonylurea hypoglycemia.",
        "recommended_alternatives": [
            {"salt": "Linagliptin / Sitagliptin (DPP-4i)", "brands": ["Trajenta 5", "Januvia 50"], "rationale": "Glucose-dependent insulin secretion with negligible hypoglycemia risk."},
            {"salt": "Augmentin", "brands": ["Augmentin 625 Duo"], "rationale": "First-line beta-lactam antibiotic without pancreatic beta-cell interaction."}
        ]
    },
    "nsaid_renal_hazard": {
        "problem": "NSAIDs cause renal vasoconstriction & acute kidney injury in Renal Disease.",
        "recommended_alternatives": [
            {"salt": "Paracetamol", "brands": ["Dolo 650", "Calpol 500"], "rationale": "First-line analgesic; non-nephrotoxic at therapeutic doses."},
            {"salt": "Tramadol (Adjusted)", "brands": ["Ultracet"], "rationale": "Centrally acting analgesic alternative with dose adjustment."}
        ]
    },
    "nsaid_pregnancy_hazard": {
        "problem": "Fetotoxicity and risk of premature ductus arteriosus closure.",
        "recommended_alternatives": [
            {"salt": "Paracetamol", "brands": ["Dolo 500", "Crocin Advance"], "rationale": "Analgesic with confirmed safety profile across all trimesters."},
            {"salt": "Labetalol / Methyldopa", "brands": ["Labebet 100", "Alphadopa 250"], "rationale": "First-line gestational antihypertensive agents."}
        ]
    },
    "qt_prolongation_hazard": {
        "problem": "Additive QT prolongation elevates risk of Torsades de Pointes.",
        "recommended_alternatives": [
            {"salt": "Metoclopramide / Domperidone (Monitored)", "brands": ["Perinorm"], "rationale": "Alternative antiemetic avoiding additive macrolide interactions."},
            {"salt": "Augmentin", "brands": ["Augmentin 625"], "rationale": "Beta-lactam alternative without cardiac repolarization effects."}
        ]
    }
}

def get_substitute_recommendations(alerts: List[Dict[str, Any]], patient_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    suggestions = []
    seen_keys = set()

    for alert in alerts:
        effect_name = alert.get("effect", "")
        matched_rule_key = None

        if "Rhabdomyolysis" in effect_name or "Statin" in effect_name:
            matched_rule_key = "statin_macrolide"
        elif "Bleed" in effect_name or "Antiplatelet" in effect_name or "Aspirin" in effect_name:
            matched_rule_key = "dapt_gi_bleed"
        elif "Hyperkalemia" in effect_name or "Renin-Angiotensin" in effect_name:
            matched_rule_key = "ras_hyperkalemia"
        elif "Hypoglycem" in effect_name:
            matched_rule_key = "sulfonylurea_hypoglycemia"
        elif "Nephrotoxicity" in effect_name or "Kidney" in effect_name or "Renal" in effect_name:
            matched_rule_key = "nsaid_renal_hazard"
        elif "Teratogenic" in effect_name or "Pregnancy" in effect_name or "Fetal" in effect_name:
            matched_rule_key = "nsaid_pregnancy_hazard"
        elif "QT" in effect_name or "Arrhythmia" in effect_name or "Torsades" in effect_name:
            matched_rule_key = "qt_prolongation_hazard"

        if matched_rule_key and matched_rule_key not in seen_keys:
            seen_keys.add(matched_rule_key)
            rule_data = CLINICAL_SUBSTITUTION_RULES[matched_rule_key]
            suggestions.append({
                "triggered_by": effect_name,
                "clinical_problem": rule_data["problem"],
                "options": rule_data["recommended_alternatives"]
            })

    return suggestions