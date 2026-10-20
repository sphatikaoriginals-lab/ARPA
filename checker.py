from collections import Counter
from normalize import get_salts
from learning_engine import is_rule_suppressed
from recommender import get_substitute_recommendations

# 1. Comprehensive Drug Adverse Tendency & Common Symptom Trigger Profiles
DRUG_ADVERSE_TENDENCIES = {
    # NSAIDs & Analgesics
    "aceclofenac": {
        "tendencies": ["Gastric Irritation / Acidity", "Abdominal Bloating & Dyspepsia", "Heartburn / Epigastric Distress"],
        "rare_tendencies": ["Frontal Headache", "Dizziness", "Mild Fluid Retention"],
        "prophylaxis": "Strictly consume after a full meal. Co-administering a PPI (e.g., Pantoprazole) prevents mucosal ulceration."
    },
    "diclofenac": {
        "tendencies": ["Severe Gastric Burning / Reflux", "Nausea & Vomiting", "Abdominal Cramping"],
        "rare_tendencies": ["Transaminase Elevation", "Headache"],
        "prophylaxis": "Avoid taking on an empty stomach. Maintain adequate hydration."
    },
    "ibuprofen": {
        "tendencies": ["Acid Reflux & Heartburn", "Stomach Upset / Bloating", "Nausea"],
        "rare_tendencies": ["Tinnitus", "Fluid Congestion"],
        "prophylaxis": "Take with milk or meal. Discontinue if persistent epigastric pain occurs."
    },
    "paracetamol": {
        "tendencies": ["Generally well-tolerated at normal doses"],
        "rare_tendencies": ["Mild Nausea", "Transient Hepatic Enzyme Shifts in high doses"],
        "prophylaxis": "Do not exceed 4,000 mg cumulative daily intake across all combination brands."
    },

    # Statins
    "atorvastatin": {
        "tendencies": ["Diffuse Headache", "Abdominal Flatulence / Bloating", "Mild Diarrhea or Constipation"],
        "rare_tendencies": ["Proximal Muscle Aches (Myalgia)", "Elevated Hepatic Transaminases"],
        "prophylaxis": "Take at bedtime. Report any unexplained dark urine or severe muscular soreness."
    },
    "rosuvastatin": {
        "tendencies": ["Headache", "Abdominal Discomfort & Nausea", "Fatigue"],
        "rare_tendencies": ["Transient Proteinuria", "Myalgia"],
        "prophylaxis": "Administer consistently once daily with or without food."
    },

    # Cardiovascular & Antihypertensives
    "amlodipine": {
        "tendencies": ["Peripheral Dependent Edema (Ankle Swelling)", "Facial Flushing & Headache", "Abdominal Fullness"],
        "rare_tendencies": ["Nasal Congestion / Rhinitis-like symptoms", "Palpitations"],
        "prophylaxis": "Elevate legs during rest if mild ankle edema develops. Maintain regular BP monitoring."
    },
    "telmisartan": {
        "tendencies": ["Orthostatic Dizziness / Lightheadedness", "Upper Respiratory / Sinus Congestion"],
        "rare_tendencies": ["Back Pain", "Diarrhea"],
        "prophylaxis": "Avoid rapid standing up from sitting or lying down positions to prevent postural syncope."
    },
    "carvedilol": {
        "tendencies": ["Fatigue & Lethargy", "Dizziness on standing", "Mild Bronchial Congestion in predisposed individuals"],
        "rare_tendencies": ["Cold Extremities", "Transient Nausea"],
        "prophylaxis": "Take with food to slow absorption rate and minimize sudden hypotensive effects."
    },

    # Antibiotics
    "azithromycin": {
        "tendencies": ["Nausea & Vomiting", "Abdominal Bloating & Cramping", "Loose Stools / Diarrhea"],
        "rare_tendencies": ["Dysgeusia (Altered Taste)", "Headache"],
        "prophylaxis": "Can be taken 1 hour before or 2 hours after meals with ample water."
    },
    "amoxicillin": {
        "tendencies": ["Nausea", "Loose Bowels / Antibiotic-Induced Diarrhea", "Mild Bloating"],
        "rare_tendencies": ["Pruritic Skin Rash", "Oral Candidiasis"],
        "prophylaxis": "Take with meals to minimize GI distress. Consider probiotic supplementation post antibiotic course."
    },
    "clarithromycin": {
        "tendencies": ["Metallic / Bitter Taste", "Nausea & Gastric Dyspepsia", "Headache"],
        "rare_tendencies": ["Transient Liver Enzyme Fluctuations", "Abdominal Distension"],
        "prophylaxis": "Administer with food to reduce taste disturbance and gastric irritation."
    },

    # Neuro / Psychiatric
    "fluvoxamine maleate": {
        "tendencies": ["Nausea (especially during initial 7-14 days)", "Headache", "Somnolence or Insomnia", "Anorexia & Bloating"],
        "rare_tendencies": ["Dry Mouth", "Mild Fine Tremors"],
        "prophylaxis": "Start at low doses taken at bedtime. GI nausea generally subsides after first week of therapy."
    }
}

# 2. Exhaustive Biochemical & Molecular Pathways Library
BIOCHEMICAL_MECHANISMS = {
    "atorvastatin_clarithromycin": {
        "title": "CYP3A4 Inhibition & Statin-Induced Rhabdomyolytic Cascade",
        "primary_mechanism": "Clarithromycin acts as a potent suicide-inhibitor of the Cytochrome P450 3A4 (CYP3A4) hepatic microsomal enzyme, arresting the first-pass oxidative metabolism of Atorvastatin.",
        "biochemical_steps": [
            "Competitive covalent binding of Clarithromycin to the heme group of CYP3A4.",
            "Intracellular accumulation of lipophilic Atorvastatin in skeletal myocytes.",
            "Depletion of Farnesyl Pyrophosphate (FPP) and Geranylgeranyl Pyrophosphate (GGPP) intermediates.",
            "Sarcolemmal rupture releasing massive concentrations of Myoglobin and Creatine Kinase into circulation."
        ],
        "micro_possibilities": [
            "Myoglobinuric Acute Tubular Necrosis (ATN).",
            "Severe metabolic hyperkalemia leading to cardiac arrest."
        ],
        "affected_receptors": ["CYP3A4", "HMG-CoA Reductase", "OATP1B1 Transporter"]
    },
    "aspirin_ibuprofen": {
        "title": "Steric COX-1 Active Site Competition & Unchecked Thromboxane A2 Generation",
        "primary_mechanism": "Ibuprofen binds reversibly to Arg120 of COX-1, sterically obstructing irreversible Aspirin access to Ser529.",
        "biochemical_steps": [
            "Ibuprofen enters the COX-1 catalytic channel and temporarily anchors at Arg120.",
            "Aspirin is physically hindered from permanent acetylation of Ser529.",
            "Platelets regain full ability to generate Thromboxane A2 upon Ibuprofen washout.",
            "Gastric cytoprotective Prostaglandins (PGE2, PGI2) remain severely suppressed."
        ],
        "micro_possibilities": [
            "Loss of cardioprotective antiplatelet effect.",
            "Sub-epithelial gastric micro-hemorrhages and erosive gastritis."
        ],
        "affected_receptors": ["Cyclooxygenase-1 (Ser529 / Arg120)", "Thromboxane Synthase"]
    },
    "symptom_nsaid_gastric": {
        "title": "Prostanoid Depletion & Gastroduodenal Mucosal Barrier Destruction",
        "primary_mechanism": "Systemic NSAIDs shut down the synthesis of gastroprotective Prostaglandin E2 (PGE2) and Prostacyclin (PGI2).",
        "biochemical_steps": [
            "Downregulation of EP3 prostanoid receptors on parietal cells, increasing gastric HCl output.",
            "Decline in mucin and bicarbonate ion secretion by surface mucous cells.",
            "Microvascular vasoconstriction in lamina propria inducing mucosal ischemia."
        ],
        "micro_possibilities": [
            "Torrential upper gastrointestinal hemorrhage.",
            "Gastroduodenal perforation into peritoneal space."
        ],
        "affected_receptors": ["COX-1 / COX-2", "EP3 Prostanoid Receptor", "H+/K+ ATPase"]
    },
    "duplicate_paracetamol": {
        "title": "Hepatic Glutathione Depletion & NAPQI-Induced Hepatocellular Necrosis",
        "primary_mechanism": "Excessive cumulative Paracetamol saturates normal glucuronidation, generating toxic electrophilic NAPQI metabolites.",
        "biochemical_steps": [
            "Rapid saturation of Phase II UDP-glucuronosyltransferase enzymes.",
            "CYP2E1 oxidizes excess Paracetamol into reactive NAPQI.",
            "Endogenous hepatic Glutathione (GSH) reserves drop below 30% baseline.",
            "Mitochondrial permeability transition (MPT) pore opening triggering Centrilobular Zone 3 necrosis."
        ],
        "micro_possibilities": [
            "Serum transaminases (AST/ALT) spike exceeding 10,000 IU/L.",
            "Coagulopathy secondary to impaired hepatic clotting factor synthesis."
        ],
        "affected_receptors": ["CYP2E1", "Glutathione S-Transferase"]
    }
}

def get_biochemical_profile(alert_key: str) -> dict:
    key = alert_key.lower().replace(" ", "_")
    for b_key, data in BIOCHEMICAL_MECHANISMS.items():
        if b_key in key or key in b_key:
            return data
    return {
        "title": "Cellular Receptor & Pharmacokinetic Disturbance",
        "primary_mechanism": "Pharmacological competition and altered clearance pathways causing intracellular metabolic perturbation.",
        "biochemical_steps": [
            "Receptor occupancy conflict at target tissue binding domains.",
            "Altered Phase I hepatic microsomal enzyme kinetics (CYP450 cascade)."
        ],
        "micro_possibilities": ["Tissue hypersensitivity reaction", "Transient metabolic electrolyte shift"],
        "affected_receptors": ["Hepatic Cytochrome P450", "Renal Organic Anion Transporters"]
    }

def get_drug_tendencies(salts: list) -> list:
    """Extracts known physiological side effects, bloating/acidity triggers, and prophylaxis for salts."""
    results = []
    for s in salts:
        s_clean = s.lower().strip()
        profile = DRUG_ADVERSE_TENDENCIES.get(s_clean)
        if profile:
            results.append({
                "salt": s.capitalize(),
                "tendencies": profile["tendencies"],
                "rare_tendencies": profile.get("rare_tendencies", []),
                "prophylaxis": profile.get("prophylaxis", "")
            })
        else:
            # Generic safe profile for unindexed salts
            results.append({
                "salt": s.capitalize(),
                "tendencies": ["Mild Gastrointestinal Sensitization"],
                "rare_tendencies": ["Transient Nausea or Headache"],
                "prophylaxis": "Administer with a glass of water post food."
            })
    return results

SYMPTOM_HAZARD_RULES = [
    {
        "keywords": ["acidity", "gastric", "ulcer", "stomach burn", "gerd", "reflux", "bloating"],
        "banned_salts": ["ibuprofen", "aceclofenac", "diclofenac", "aspirin"],
        "severity": "HIGH",
        "bio_key": "symptom_nsaid_gastric",
        "effect": "NSAID-Induced Gastric Mucosal Aggravation",
        "description": "Patient reports active gastric irritation or ulcer symptoms. Prescribed NSAID suppresses prostaglandin synthesis, risking mucosal erosion and bleeding.",
        "action": "Discontinue NSAID. Substitute with Paracetamol and co-prescribe Pantoprazole 40 mg."
    }
]

INTERACTION_RULES = [
    {
        "salts": ["atorvastatin", "clarithromycin"],
        "severity": "FATAL",
        "bio_key": "atorvastatin_clarithromycin",
        "effect": "Severe Rhabdomyolysis & Statin Myotoxicity",
        "description": "Clarithromycin inhibits CYP3A4, causing massive Atorvastatin accumulation and acute muscle necrosis.",
        "action": "Switch statin to Rosuvastatin or select an alternative antibiotic."
    },
    {
        "salts": ["azithromycin", "ondansetron"],
        "severity": "FATAL",
        "bio_key": "azithromycin_ondansetron",
        "effect": "Additive QT Prolongation & Ventricular Arrhythmia",
        "description": "Additive delay in myocardial repolarization (hERG block) elevating Torsades de Pointes risk.",
        "action": "Substitute antiemetic with Metoclopramide or Domperidone."
    },
    {
        "salts": ["aspirin", "ibuprofen"],
        "severity": "HIGH",
        "bio_key": "aspirin_ibuprofen",
        "effect": "Aspirin Cardioprotection Antagonism & GI Toxicity",
        "description": "Ibuprofen competitively impedes Aspirin access to platelet COX-1 binding pockets.",
        "action": "Use Paracetamol as the preferred analgesic."
    }
]

def check_prescription(medicines: list, patient: dict = None, symptoms_text: str = "") -> dict:
    patient = patient or {}
    resolved_drugs = []
    all_salts = set()
    salt_occurrences = []

    for med in medicines:
        salts = get_salts(med)
        tendencies = get_drug_tendencies(salts)
        resolved_drugs.append({
            "brand": med, 
            "salts": salts,
            "tendency_profiles": tendencies
        })
        for s in salts:
            s_clean = s.lower().strip()
            all_salts.add(s_clean)
            salt_occurrences.append((s_clean, med))

    alerts = []

    # 1. Symptom vs Drug
    symptoms_lower = symptoms_text.lower()
    if symptoms_lower:
        for sym_rule in SYMPTOM_HAZARD_RULES:
            if any(k in symptoms_lower for k in sym_rule["keywords"]):
                for banned in sym_rule["banned_salts"]:
                    if banned in all_salts:
                        alerts.append({
                            "type": "SYMPTOM_CONTRAINDICATION",
                            "conflict_between": f"Reported Symptom vs {banned.capitalize()}",
                            "severity": sym_rule["severity"],
                            "effect": sym_rule["effect"],
                            "description": sym_rule["description"],
                            "action": sym_rule["action"],
                            "biochemistry": get_biochemical_profile(sym_rule.get("bio_key", "symptom_nsaid_gastric"))
                        })

    # 2. Duplicate Overdose
    salt_counts = Counter([item[0] for item in salt_occurrences])
    for salt, count in salt_counts.items():
        if count > 1:
            conflicting_brands = [item[1] for item in salt_occurrences if item[0] == salt]
            alerts.append({
                "type": "DUPLICATE_THERAPY_OVERDOSE",
                "conflict_between": f"Duplicate Active Salt: {salt.capitalize()} in ({', '.join(conflicting_brands)})",
                "severity": "HIGH",
                "effect": f"Accidental {salt.capitalize()} Overdose Hazard",
                "description": f"The prescribed formulations ({', '.join(conflicting_brands)}) share active '{salt.capitalize()}', exceeding safe daily therapeutic limits.",
                "action": f"Prescribe only one formulation containing {salt.capitalize()}.",
                "biochemistry": get_biochemical_profile(f"duplicate_{salt}")
            })

    # 3. Drug-Drug Interactions
    for rule in INTERACTION_RULES:
        rule_salts = [s.lower().strip() for s in rule["salts"]]
        if all(s in all_salts for s in rule_salts):
            if not is_rule_suppressed(rule_salts[0], rule_salts[1]):
                alerts.append({
                    "type": "DRUG_DRUG_INTERACTION",
                    "conflict_between": " + ".join([s.capitalize() for s in rule["salts"]]),
                    "severity": rule["severity"],
                    "effect": rule["effect"],
                    "description": rule["description"],
                    "action": rule["action"],
                    "biochemistry": get_biochemical_profile(rule.get("bio_key", "_".join(rule_salts)))
                })

    recommendations = get_substitute_recommendations(alerts, patient)

    return {
        "prescribed_drugs": resolved_drugs,
        "active_salts": list(all_salts),
        "reported_symptoms": symptoms_text,
        "patient_profile": patient,
        "alerts_count": len(alerts),
        "alerts": alerts,
        "recommendations": recommendations
    }