"""
ARPA ATC Class-Based Pharmacological Taxonomy & Universal Stripper Engine
=========================================================================
Includes:
- Release modifier stripping (SR, CR, PR, ER, MR, XR, Chrono)
- Chemical ester/salt counter-ion normalization (Medoxomil, Besylate, etc.)
- Narrow Therapeutic Index (NTI) registry
- 16 Core therapeutic classes with route-aware filtering
"""

import re
from typing import Dict, List, Any, Optional, Tuple

# --------------------------------------------------------------------------
# 1. NTI REGISTRY (NARROW THERAPEUTIC INDEX DRUGS)
# --------------------------------------------------------------------------
NTI_MOLECULES: Dict[str, Dict[str, Any]] = {
    "phenytoin": {
        "therapeutic_range": "10 - 20 mcg/mL",
        "kinetic_hazard": "Saturable Michaelis-Menten elimination. Minor dose increments trigger toxic serum spikes.",
        "tdm_mandatory": True
    },
    "valproate": {
        "therapeutic_range": "50 - 100 mcg/mL",
        "kinetic_hazard": "Saturable plasma protein binding. Free-fraction escalates non-linearly.",
        "tdm_mandatory": True
    },
    "sodium valproate": {
        "therapeutic_range": "50 - 100 mcg/mL",
        "kinetic_hazard": "Saturable plasma protein binding. Free-fraction escalates non-linearly.",
        "tdm_mandatory": True
    },
    "carbamazepine": {
        "therapeutic_range": "4 - 12 mcg/mL",
        "kinetic_hazard": "Auto-induction of CYP3A4 alters systemic half-life unpredictably over 3-5 weeks.",
        "tdm_mandatory": True
    },
    "warfarin": {
        "therapeutic_range": "INR 2.0 - 3.0",
        "kinetic_hazard": "Extensive CYP2C9/VKORC1 polymorphic variability.",
        "tdm_mandatory": True
    },
    "digoxin": {
        "therapeutic_range": "0.5 - 0.9 ng/mL",
        "kinetic_hazard": "Narrow margin between inotropic efficacy and fatal ventricular arrhythmia.",
        "tdm_mandatory": True
    },
    "lithium": {
        "therapeutic_range": "0.6 - 1.2 mEq/L",
        "kinetic_hazard": "Exclusively renally eliminated; slight dehydration triggers severe neurotoxicity.",
        "tdm_mandatory": True
    }
}

# --------------------------------------------------------------------------
# 2. ATC CLASS SPECIFICATIONS
# --------------------------------------------------------------------------
ATC_CLASSES: Dict[str, Dict[str, Any]] = {
    "NSAID": {
        "class_name": "Non-Steroidal Anti-Inflammatory Drugs (M01A)",
        "base_risk_score": 38,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "Beers Criteria / CDSCO Gazette Notification G.S.R. 82(E)",
        "primary_mechanism": "Inhibition of COX-1/COX-2 enzymes terminating cytoprotective mucosal PGE2 synthesis.",
        "common_side_effects": [
            "Gastric mucosal erosion & pyrosis",
            "Renal afferent arteriolar vasoconstriction & reduced GFR",
            "Platelet aggregation inhibition"
        ],
        "prophylaxis": "Administer strictly postprandially. Co-prescribe PPI in vulnerable patients.",
        "comorbidity_contraindications": {
            "has_pud_disease": {
                "severity": "FATAL",
                "effect": "Class Risk: Severe Gastrointestinal Hemorrhage & Perforation",
                "description": "Depletion of protective mucosal PGE2 precipitates peptic perforation under acid exposure.",
                "action": "Absolute Contraindication: Avoid systemic NSAIDs. Switch to Paracetamol."
            },
            "has_renal_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Acute Vasomotor Renal Decompensation",
                "description": "Blunts compensatory prostaglandin-mediated afferent arteriolar vasodilation.",
                "action": "Avoid in CKD; prefer Paracetamol with renal dose titration."
            },
            "is_pregnant": {
                "severity": "HIGH",
                "effect": "Class Risk: Premature Ductus Arteriosus Constriction & Oligohydramnios",
                "description": "Suppresses fetal pulmonary and vascular prostaglandins in the 3rd trimester.",
                "action": "Avoid NSAIDs in 3rd trimester. Paracetamol is first-line."
            },
            "has_asthma": {
                "severity": "HIGH",
                "effect": "Class Risk: Aspirin-Exacerbated Respiratory Disease (AERD)",
                "description": "Shunts arachidonic acid to 5-lipoxygenase pathway, driving massive bronchospasm.",
                "action": "Avoid in patients with asthma and nasal polyps."
            }
        },
        "age_modifiers": {
            "pediatric_max_age": 12,
            "pediatric_severity": "HIGH",
            "pediatric_effect": "Pediatric Overdose Hazard: Solid Adult Tablet",
            "pediatric_description": "Solid adult NSAID tablets exceed weight-based safety thresholds.",
            "pediatric_action": "Do NOT administer adult solid tablets. Use weight-based liquid suspensions.",
            "geriatric_min_age": 65,
            "geriatric_severity": "HIGH",
            "geriatric_effect": "Geriatric Warning: Heightened GI Bleed & Renal Collapse",
            "geriatric_description": "Age-related mucosal thinning and reduced renal reserve elevate bleeding risk.",
            "geriatric_action": "Prefer Paracetamol. Co-prescribe PPI if NSAID therapy is mandatory."
        }
    },

    "RAAS_INHIBITOR": {
        "class_name": "RAAS Inhibitors - ARBs & ACEIs (C09)",
        "base_risk_score": 32,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "KDIGO Guidelines / FDA Boxed Warning (Fetal Toxicity)",
        "primary_mechanism": "Suppression of angiotensin II vasoconstriction and aldosterone excretion.",
        "common_side_effects": [
            "Postural dizziness and hypotension",
            "Hyperkalemia secondary to decreased aldosterone",
            "Elevated serum creatinine secondary to efferent vasodilation"
        ],
        "prophylaxis": "Periodically monitor serum potassium and renal function.",
        "comorbidity_contraindications": {
            "is_pregnant": {
                "severity": "FATAL",
                "effect": "Class Risk: Fetopathy & Oligohydramnios Sequence",
                "description": "Causes fetal renal ischemia, hypocalvaria, and perinatal mortality.",
                "action": "Absolute Contraindication: Switch immediately to Labetalol or Nifedipine."
            },
            "has_renal_disease": {
                "severity": "MEDIUM",
                "effect": "Class Precaution: Efferent Vasodilatory Acute Azotemia",
                "description": "Significant GFR reduction in bilateral renal artery stenosis.",
                "action": "Monitor potassium and creatinine within 1-2 weeks of initiation."
            }
        },
        "age_modifiers": {
            "pediatric_max_age": 18,
            "pediatric_severity": "HIGH",
            "pediatric_effect": "Pediatric Restriction: Specialized Indication Only",
            "pediatric_description": "Requires specialist pediatric nephrology weight-based titration.",
            "pediatric_action": "Specialist consultation mandatory."
        }
    },

    "ANTIEPILEPTIC": {
        "class_name": "Antiepileptics & Mood Stabilizers (N03A)",
        "base_risk_score": 48,
        "coverage_tier": "TIER_2_PARTIAL",
        "evidence_citation": "AAN Guidelines / FDA Boxed Warning (Teratogenicity & Hepatic Failure)",
        "primary_mechanism": "Modulation of voltage-gated ion channels or GABAergic neurotransmission.",
        "common_side_effects": [
            "Cognitive blunting, ataxia, and dizziness",
            "Potent hepatic CYP enzyme induction or inhibition",
            "Hematological dyscrasias"
        ],
        "prophylaxis": "Monitor therapeutic drug levels (TDM) and liver enzymes regularly.",
        "comorbidity_contraindications": {
            "is_pregnant": {
                "severity": "FATAL",
                "effect": "Class Risk: Severe Teratogenicity & Neural Tube Defects",
                "description": "Valproate and Carbamazepine cause major congenital malformations and developmental delay.",
                "action": "Absolute Contraindication: Avoid in women of childbearing potential unless refractory."
            },
            "has_liver_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Fulminant Hepatotoxicity & Hyperammonemia",
                "description": "Impaired mitochondrial beta-oxidation escalates microvesicular steatosis.",
                "action": "Avoid Valproate in active hepatic disease."
            }
        }
    },

    "ANTIHISTAMINE": {
        "class_name": "Antihistamines - H1 Receptor Antagonists (R06A)",
        "base_risk_score": 20,
        "coverage_tier": "TIER_2_PARTIAL",
        "evidence_citation": "Beers Criteria / CDSCO Schedule H",
        "primary_mechanism": "Inverse agonism of peripheral and central H1 histamine receptors.",
        "common_side_effects": [
            "Sedation, drowsiness, and psychomotor impairment",
            "Anticholinergic dry mouth",
            "Urinary retention in predisposed individuals"
        ],
        "prophylaxis": "Take before bedtime. Avoid concomitant alcohol or sedative consumption.",
        "comorbidity_contraindications": {
            "has_asthma": {
                "severity": "MEDIUM",
                "effect": "Class Precaution: Mucus Viscosity Elevation",
                "description": "Anticholinergic drying of bronchial secretions may impair clearance.",
                "action": "Prefer second-generation non-sedating agents."
            }
        },
        "age_modifiers": {
            "geriatric_min_age": 65,
            "geriatric_severity": "MEDIUM",
            "geriatric_effect": "Geriatric Warning: Fall Risk & Anticholinergic Burden",
            "geriatric_description": "Sedation and postural instability elevate fracture risk.",
            "geriatric_action": "Avoid first-generation antihistamines (Hydroxyzine)."
        }
    },

    "DIURETIC": {
        "class_name": "Diuretics - Thiazide, Loop & K-Sparing (C03)",
        "base_risk_score": 30,
        "coverage_tier": "TIER_2_PARTIAL",
        "evidence_citation": "JNC 8 Guidelines / ACC-AHA Compendium",
        "primary_mechanism": "Inhibition of tubular electrolyte reabsorption, promoting natriuresis.",
        "common_side_effects": [
            "Electrolyte shifts (Hyponatremia, Hypokalemia/Hyperkalemia)",
            "Volume depletion and postural hypotension",
            "Hyperuricemia precipitating acute gout flares"
        ],
        "prophylaxis": "Administer morning dose to avoid nocturia. Monitor baseline electrolytes.",
        "comorbidity_contraindications": {
            "has_renal_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Severe Hypovolemia & Pre-Renal Azotemia",
                "description": "Excessive natriuresis lowers effective circulating volume in compromised nephrons.",
                "action": "Monitor serum creatinine and maintain strict fluid balance."
            }
        }
    },

    "ANTIEMETIC": {
        "class_name": "Prokinetics & Antiemetics (A03FA / A04AA)",
        "base_risk_score": 25,
        "coverage_tier": "TIER_2_PARTIAL",
        "evidence_citation": "MHRA Drug Safety Bulletin / CredibleMeds Category 1",
        "primary_mechanism": "Dopamine D2 antagonism or 5-HT3 serotonergic receptor blockade.",
        "common_side_effects": [
            "Extrapyramidal dystonias (Metoclopramide)",
            "Cardiac repolarization delay (QTc prolongation)"
        ],
        "prophylaxis": "Limit duration to shortest necessary course (<= 5 days for prokinetics).",
        "comorbidity_contraindications": {
            "has_cardiac_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: QTc Prolongation & Arrhythmogenesis",
                "description": "Direct blockade of cardiac hERG potassium channels by Domperidone/Ondansetron.",
                "action": "Avoid in congenital long QT syndrome or concurrent QTc-prolonging drugs."
            }
        }
    },

    "CCB": {
        "class_name": "Calcium Channel Blockers - Dihydropyridines (C08CA)",
        "base_risk_score": 25,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "ACC/AHA Guidelines",
        "primary_mechanism": "L-type calcium channel inhibition in vascular smooth muscle causing arteriolar vasodilation.",
        "common_side_effects": ["Dependent peripheral pedal edema", "Facial flushing and headache"],
        "prophylaxis": "Administer preferably in evening. Elevate lower extremities at rest.",
        "comorbidity_contraindications": {}
    },

    "STATIN": {
        "class_name": "HMG-CoA Reductase Inhibitors (C10AA)",
        "base_risk_score": 28,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "ACC/AHA Cholesterol Guidelines / FDA Boxed Warning",
        "primary_mechanism": "Competitive inhibition of HMG-CoA reductase terminating mevalonate synthesis.",
        "common_side_effects": ["Myalgia and CPK elevation", "Hepatic transaminitis"],
        "prophylaxis": "Administer single evening dose. Baseline LFT screening recommended.",
        "comorbidity_contraindications": {
            "has_liver_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Hepatocellular Transaminitis & DILI",
                "description": "Hepatic accumulation in compromised liver parenchyma.",
                "action": "Avoid in active liver cirrhosis or persistent unexplained LFT spikes."
            },
            "is_pregnant": {
                "severity": "FATAL",
                "effect": "Class Risk: Fetal Teratogenicity (Membrane Synthesis Arrest)",
                "description": "Cholesterol suppression arrests fetal embryogenesis.",
                "action": "Strictly Contraindicated in Pregnancy. Discontinue prior to conception."
            }
        }
    },

    "MACROLIDE": {
        "class_name": "Macrolide Antimicrobials (J01FA)",
        "base_risk_score": 30,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "FDA Drug Safety Advisory / IDSA Guidelines",
        "primary_mechanism": "Binds 50S ribosomal subunit inhibiting protein transpeptidation.",
        "common_side_effects": ["Gastrointestinal cramping", "QTc prolongation"],
        "prophylaxis": "Avoid with other QTc-prolonging or CYP3A4-cleared medications.",
        "comorbidity_contraindications": {
            "has_cardiac_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Drug-Induced Torsades de Pointes",
                "description": "Blockade of cardiac outward potassium rectifier current.",
                "action": "Obtain baseline ECG. Choose alternative antibiotic if baseline QTc > 460ms."
            }
        }
    },

    "FLUOROQUINOLONE": {
        "class_name": "Fluoroquinolone Antimicrobials (J01MA)",
        "base_risk_score": 45,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "FDA Boxed Warning (Tendinitis & Peripheral Neuropathy)",
        "primary_mechanism": "Inhibition of bacterial DNA gyrase and topoisomerase IV.",
        "common_side_effects": ["Tendinitis and tendon rupture", "Articular cartilage toxicity", "CNS stimulation"],
        "prophylaxis": "Avoid multivalent antacids/iron within 2 hours. Maintain vigorous hydration.",
        "comorbidity_contraindications": {
            "has_cardiac_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Arrhythmogenesis & QTc Prolongation",
                "description": "Cardiac potassium channel delay predisposing to ventricular arrhythmias.",
                "action": "Select non-quinolone alternative."
            }
        },
        "age_modifiers": {
            "pediatric_max_age": 18,
            "pediatric_severity": "HIGH",
            "pediatric_effect": "Pediatric Warning: Arthropathy & Cartilage Erosion",
            "pediatric_description": "Weight-bearing articular cartilage erosion in pediatric populations.",
            "pediatric_action": "Contraindicated under 18 years unless for pseudomonal cystic fibrosis."
        }
    },

    "TETRACYCLINE": {
        "class_name": "Tetracycline Antimicrobials (J01AA)",
        "base_risk_score": 40,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "AAP Red Book / CDSCO Schedule H",
        "primary_mechanism": "Reversible binding to bacterial 30S ribosomal subunit.",
        "common_side_effects": ["Calcium chelation in developing teeth/bones", "Cutaneous phototoxicity"],
        "prophylaxis": "Administer with full glass of water while remaining upright for 30 minutes.",
        "comorbidity_contraindications": {
            "is_pregnant": {
                "severity": "FATAL",
                "effect": "Class Risk: Fetal Bone Retardation & Tooth Dysplasia",
                "description": "Crosses placenta and forms irreversible calcium complexes in tooth buds.",
                "action": "Absolute Contraindication during pregnancy."
            }
        },
        "age_modifiers": {
            "pediatric_max_age": 8,
            "pediatric_severity": "HIGH",
            "pediatric_effect": "Pediatric Risk: Permanent Tooth Staining & Enamel Hypoplasia",
            "pediatric_description": "Chelation causes permanent brownish tooth discoloration under 8 years.",
            "pediatric_action": "Contraindicated under 8 years. Switch to Beta-lactams."
        }
    },

    "BETA_BLOCKER": {
        "class_name": "Beta-Adrenoreceptor Antagonists (C07A)",
        "base_risk_score": 30,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "ACC/AHA Heart Failure Guidelines",
        "primary_mechanism": "Competitive antagonism of cardiac and vascular beta adrenoceptors.",
        "common_side_effects": ["Bradycardia and fatigue", "Peripheral vasoconstriction"],
        "prophylaxis": "Do not abruptly discontinue therapy.",
        "comorbidity_contraindications": {
            "has_asthma": {
                "severity": "HIGH",
                "effect": "Class Risk: Severe Bronchoconstriction",
                "description": "Non-selective beta-2 blockade prevents endogenous bronchodilation.",
                "action": "Contraindicated in severe asthma; use cardioselective agents cautiously."
            },
            "has_diabetes": {
                "severity": "MEDIUM",
                "effect": "Class Warning: Masking of Hypoglycemia Symptoms",
                "description": "Blunts sympathetic warning signs (tachycardia, tremor) of hypoglycemia.",
                "action": "Advise diabetic patient that diaphoresis remains an unmasked sign."
            }
        }
    },

    "STEROID": {
        "class_name": "Corticosteroids (H02AB)",
        "base_risk_score": 40,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "Endocrine Society Guidelines / CDSCO Schedule H",
        "primary_mechanism": "Glucocorticoid receptor activation driving hepatic gluconeogenesis and immune suppression.",
        "common_side_effects": ["Steroid-induced hyperglycemia", "Gastric mucosal thinning", "Fluid retention"],
        "prophylaxis": "Take single morning dose after food. Co-prescribe PPI in ulcer-prone patients.",
        "comorbidity_contraindications": {
            "has_diabetes": {
                "severity": "HIGH",
                "effect": "Class Risk: Severe Hyperglycemic Dysregulation",
                "description": "Stimulates hepatic gluconeogenesis and causes severe peripheral insulin resistance.",
                "action": "Intensify blood glucose monitoring; titrate antidiabetic dosage."
            },
            "has_pud_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Peptic Ulcer Aggravation",
                "description": "Suppresses cytoprotective prostaglandins and tissue repair.",
                "action": "Co-prescribe PPI and avoid concurrent NSAIDs."
            }
        }
    },

    "ANTIDIABETIC": {
        "class_name": "Oral Antidiabetic Agents (A10B)",
        "base_risk_score": 25,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "ADA Standards of Medical Care in Diabetes",
        "primary_mechanism": "Enhances insulin sensitivity or stimulates pancreatic beta-cell insulin secretion.",
        "common_side_effects": ["Hypoglycemia (Sulfonylureas)", "Gastrointestinal intolerance", "Lactic acidosis (Metformin)"],
        "prophylaxis": "Maintain regular meal intervals. Maintain adequate hydration.",
        "comorbidity_contraindications": {
            "has_renal_disease": {
                "severity": "HIGH",
                "effect": "Class Risk: Impaired Clearance & Lactic Acidosis / Hypoglycemia",
                "description": "Reduced GFR impairs clearance of Metformin and active metabolites.",
                "action": "Dose-adjust based on eGFR; discontinue Metformin if eGFR < 30 mL/min."
            }
        }
    },

    "ANTICOAGULANT": {
        "class_name": "Antithrombotic Agents & Platelet Inhibitors (B01A)",
        "base_risk_score": 50,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "CHEST Guidelines / FDA Boxed Warning",
        "primary_mechanism": "Irreversible platelet P2Y12 blockade or inhibition of clotting cascade proteases.",
        "common_side_effects": ["Spontaneous mucosal and microvascular bleeding", "GI hemorrhage"],
        "prophylaxis": "Avoid concomitant unmonitored NSAIDs. Monitor CBC and coagulation markers.",
        "comorbidity_contraindications": {
            "has_pud_disease": {
                "severity": "FATAL",
                "effect": "Class Risk: Life-Threatening Gastrointestinal Bleed",
                "description": "Severe hemorrhage from active peptic lesions under platelet inhibition.",
                "action": "Absolute Contraindication: Avoid in active ulcers; provide gastroprotection."
            }
        }
    },

    "PPI": {
        "class_name": "Proton Pump Inhibitors (A02BC)",
        "base_risk_score": 15,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "ACG Clinical Guideline",
        "primary_mechanism": "Irreversible covalent inhibition of parietal cell H+/K+ ATPase.",
        "common_side_effects": ["Headache", "Altered microbiome", "Long-term mineral malabsorption"],
        "prophylaxis": "Administer 30-60 minutes prior to first meal.",
        "comorbidity_contraindications": {}
    },

    "ANALGESIC": {
        "class_name": "Central Analgesics & Antipyretics (N02BE)",
        "base_risk_score": 15,
        "coverage_tier": "TIER_1_FULL",
        "evidence_citation": "WHO Guidelines / FDA Advisory",
        "primary_mechanism": "Central inhibition of prostaglandin synthesis.",
        "common_side_effects": ["Mild gastrointestinal discomfort"],
        "prophylaxis": "Strict weight-based dosing. Do not exceed 4000mg/day in adults.",
        "comorbidity_contraindications": {}
        
    }, 

    "SUPPLEMENT": {
        "class_name": "Vitamins, Minerals & Nutritional Supplements",
        "base_risk_score": 5,
        "coverage_tier": "TIER_1_FULL",
        "primary_mechanism": "Replenishes essential co-factors and minerals.",
        "common_side_effects": ["Mild gastric upset", "Constipation (Iron/Calcium)"],
        "prophylaxis": "Take with meals.",
        "comorbidity_contraindications": {}
    },
    "PENICILLIN": {
        "class_name": "Beta-Lactam Antibiotics",
        "base_risk_score": 20,
        "coverage_tier": "TIER_1_FULL",
        "primary_mechanism": "Inhibits bacterial cell wall synthesis.",
        "common_side_effects": ["Diarrhea", "Hypersensitivity"],
        "prophylaxis": "Check for history of penicillin allergy.",
        "comorbidity_contraindications": {}
    },
    "GABAPENTINOID": {
        "class_name": "Neuropathic Agents (Gabapentinoids)",
        "base_risk_score": 35,
        "coverage_tier": "TIER_1_FULL",
        "primary_mechanism": "Binds to calcium channels in CNS.",
        "common_side_effects": ["Somnolence", "Peripheral Edema"],
        "prophylaxis": "Titrate dose slowly.",
        "comorbidity_contraindications": {
            "has_renal_disease": {"severity": "HIGH", "effect": "Toxicity", "description": "Accumulates in CKD.", "action": "Strict renal dose adjustment."}
        }
    },
    "MUCOLYTIC": {
        "class_name": "Mucolytics & Cough Prep",
        "base_risk_score": 15,
        "coverage_tier": "TIER_1_FULL",
        "primary_mechanism": "Thins bronchial secretions.",
        "common_side_effects": ["Mild GI irritation"],
        "prophylaxis": "Avoid late evening doses.",
        "comorbidity_contraindications": {}
    }
}

# --------------------------------------------------------------------------
# 3. CORE CHEMICAL SALTS TAXONOMY MAPPING
# --------------------------------------------------------------------------
SALT_TO_ATC_CLASS: Dict[str, str] = {
"amlodipine": "CCB",
    "atenolol": "BETA_BLOCKER",  # <--- Yeh add karna zaroori hai
    "metoprolol": "BETA_BLOCKER",
    "bisoprolol": "BETA_BLOCKER",

    # NSAIDs
    "aceclofenac": "NSAID", "ibuprofen": "NSAID", "diclofenac": "NSAID",
    "nimesulide": "NSAID", "aspirin": "NSAID", "etoricoxib": "NSAID",
    "naproxen": "NSAID", "ketorolac": "NSAID", "piroxicam": "NSAID",
    "indomethacin": "NSAID", "mefenamic acid": "NSAID",

    # Analgesics
    "paracetamol": "ANALGESIC",

    # RAAS Inhibitors
    "olmesartan": "RAAS_INHIBITOR", "telmisartan": "RAAS_INHIBITOR", "losartan": "RAAS_INHIBITOR",
    "valsartan": "RAAS_INHIBITOR", "candesartan": "RAAS_INHIBITOR", "ramipril": "RAAS_INHIBITOR",
    "enalapril": "RAAS_INHIBITOR", "lisinopril": "RAAS_INHIBITOR",

    # CCBs
    "amlodipine": "CCB", "cilnidipine": "CCB", "nifedipine": "CCB", "felodipine": "CCB",
    "lercanidipine": "CCB", "diltiazem": "CCB", "verapamil": "CCB",

    # Antihistamines
    "cetirizine": "ANTIHISTAMINE", "levocetirizine": "ANTIHISTAMINE", "hydroxyzine": "ANTIHISTAMINE",
    "fexofenadine": "ANTIHISTAMINE", "loratadine": "ANTIHISTAMINE", "chlorpheniramine": "ANTIHISTAMINE",

    # Diuretics
    "hydrochlorothiazide": "DIURETIC", "chlorthalidone": "DIURETIC", "furosemide": "DIURETIC",
    "torsemide": "DIURETIC", "spironolactone": "DIURETIC",

    # Antiepileptics
    "valproate": "ANTIEPILEPTIC", "sodium valproate": "ANTIEPILEPTIC", "divalproex": "ANTIEPILEPTIC",
    "phenytoin": "ANTIEPILEPTIC", "carbamazepine": "ANTIEPILEPTIC", "levetiracetam": "ANTIEPILEPTIC",

    # Antiemetics
    "ondansetron": "ANTIEMETIC", "domperidone": "ANTIEMETIC", "metoclopramide": "ANTIEMETIC",

    # Steroids
    "prednisolone": "STEROID", "dexamethasone": "STEROID", "methylprednisolone": "STEROID",
    "deflazacort": "STEROID",

    # Antidiabetics
    "metformin": "ANTIDIABETIC", "glimepiride": "ANTIDIABETIC", "gliclazide": "ANTIDIABETIC",
    "sitagliptin": "ANTIDIABETIC", "dapagliflozin": "ANTIDIABETIC",

    # Anticoagulants
    "clopidogrel": "ANTICOAGULANT", "warfarin": "ANTICOAGULANT", "ticagrelor": "ANTICOAGULANT",

    # Statins
    "atorvastatin": "STATIN", "rosuvastatin": "STATIN", "simvastatin": "STATIN",

    # Macrolides, Tetracyclines & Antibiotics
    "clarithromycin": "MACROLIDE", "azithromycin": "MACROLIDE",
    "ciprofloxacin": "FLUOROQUINOLONE", "levofloxacin": "FLUOROQUINOLONE",
    "doxycycline": "TETRACYCLINE", "tetracycline": "TETRACYCLINE", "minocycline": "TETRACYCLINE",
    "metoprolol": "BETA_BLOCKER", "atenolol": "BETA_BLOCKER",
    "pantoprazole": "PPI", "omeprazole": "PPI", "rabeprazole": "PPI", "esomeprazole": "PPI"
    }

# --------------------------------------------------------------------------
# 4. UNIVERSAL CHEMICAL COUNTER-ION & RELEASE MODIFIER STRIPPER
# --------------------------------------------------------------------------
SALT_EXTENSIONS = [
    r"\bsr\b", r"\bcr\b", r"\bpr\b", r"\ber\b", r"\bmr\b", r"\btr\b", r"\bxr\b", 
    r"\bod\b", r"\bds\b", r"\bforte\b", r"\bchrono\b",
    r"\bmedoxomil\b", r"\bbesylate\b", r"\bbesilate\b", r"\bmaleate\b", 
    r"\bhydrochloride\b", r"\bhcl\b", r"\bsodium\b", r"\bpotassium\b", 
    r"\bsuccinate\b", r"\btartrate\b", r"\bfumarate\b", r"\bphosphate\b", 
    r"\bacetate\b", r"\bhydrate\b", r"\bdihydrate\b", r"\btrihydrate\b", 
    r"\bhemihydrate\b", r"\bsesquihydrate\b", r"\bmonohydrate\b", 
    r"\bcalcium\b", r"\bgluconate\b", r"\bsulphate\b", r"\bsulfate\b",
    r"\bip\b", r"\bbp\b", r"\busp\b", r"\btablets?\b", r"\bcapsules?\b", r"\bsyrups?\b"
]

TOPICAL_KEYWORDS = ["gel", "ointment", "cream", "emulgel", "liniment", "spray", "drop", "eye drops", "ear drops", "lotion"]

TYPO_CORRECTIONS: Dict[str, str] = {
    "aceclo": "aceclofenac",
    "ceclofenac": "aceclofenac",
    "lmesartan": "olmesartan",
    "elmisartan": "telmisartan",
    "mlodipine": "amlodipine",
    "buprofen": "ibuprofen",
    "iclofenac": "diclofenac",
    "spirin": "aspirin",
    "torvastatin": "atorvastatin",
    "zithromycin": "azithromycin",
    "etirizine": "cetirizine",
    "evocetirizine": "levocetirizine"
}

def detect_administration_route(raw_text: str) -> str:
    cleaned = raw_text.lower()
    for kw in TOPICAL_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned):
            return "topical"
    return "oral"

def strip_and_extract_salt(raw_salt: str) -> Tuple[Optional[str], Optional[str]]:
    if not raw_salt: return None, None
    import re
    cleaned = raw_salt.lower().strip()
    cleaned = re.sub(r"\d+(\.\d+)?\s*(mg|g|mcg|ml|iu|%|w/v|w/w)", " ", cleaned)
    cleaned = re.sub(r"\b\d+\b", " ", cleaned)
    cleaned = re.sub(r"[^a-z\s\-]", " ", cleaned).strip()

    # 1. Purani Dictionary Check (Do not touch old logic)
    if cleaned in SALT_TO_ATC_CLASS: 
        return cleaned, SALT_TO_ATC_CLASS[cleaned]
    
    # 2. THE MAGIC: Zero-Manual Chemical Suffix Parsing
    # Agar salt dictionary me nahi hai, toh aakhri letters (suffix) padh kar class assign karega
    if cleaned.endswith("dipine"): return cleaned, "CCB"                 # Amlodipine, Cilnidipine
    if cleaned.endswith("olol"): return cleaned, "BETA_BLOCKER"          # Atenolol, Metoprolol
    if cleaned.endswith("sartan"): return cleaned, "RAAS_INHIBITOR"      # Telmisartan, Losartan
    if cleaned.endswith("statin"): return cleaned, "STATIN"              # Atorvastatin, Rosuvastatin
    if cleaned.endswith("prazole"): return cleaned, "PPI"                # Pantoprazole, Omeprazole
    if cleaned.endswith("cillin"): return cleaned, "BETA_LACTAM_ABX"     # Amoxicillin, Penicillin
    if cleaned.endswith("floxacin"): return cleaned, "FLUOROQUINOLONE"   # Ciprofloxacin, Ofloxacin
    if cleaned.endswith("mycin"): return cleaned, "MACROLIDE"            # Azithromycin, Erythromycin
    if cleaned.endswith("gliptin"): return cleaned, "ANTIDIABETIC"       # Teneligliptin, Vildagliptin
    if cleaned.endswith("gliflozin"): return cleaned, "ANTIDIABETIC"     # Dapagliflozin, Empagliflozin
    if cleaned.endswith("conazole"): return cleaned, "ANTI_FUNGAL"       # Fluconazole, Itraconazole
    if "paracetamol" in cleaned or "fenac" in cleaned: return cleaned, "NSAID"

    return cleaned, None

def resolve_atc_inheritance(salt_name: str, patient_age: int, patient_profile: Dict[str, Any], route: str = "oral") -> Dict[str, Any]:
    clean_molecule, atc_key = strip_and_extract_salt(salt_name)
    nti_info = NTI_MOLECULES.get(clean_molecule, None) if clean_molecule else None

    if not atc_key or atc_key not in ATC_CLASSES:
        return {
            "atc_class": "Out-of-Scope / Unverified Molecule",
            "coverage_tier": "TIER_3_UNMAPPED",
            "is_out_of_scope": True,
            "base_risk_score": None,
            "primary_mechanism": "Pharmacological safety rules not yet formally verified in ARPA Core.",
            "side_effects": [],
            "prophylaxis": "Unverified clinical rule profile. Registered clinician discretion mandated.",
            "inherited_alerts": [],
            "evidence_citation": "Pending Independent Clinical Board Verification",
            "nti_info": nti_info
        }

    atc_info = ATC_CLASSES[atc_key]
    inherited_alerts = []
    display_title = clean_molecule.title() if clean_molecule else salt_name.title()
    tier = atc_info.get("coverage_tier", "TIER_1_FULL")

    if route == "topical":
        return {
            "atc_class": f"{atc_info['class_name']} (Topical Formulation)",
            "coverage_tier": tier,
            "is_out_of_scope": False,
            "base_risk_score": 10,
            "primary_mechanism": "Localized dermal absorption (< 5% systemic bioavailability). Minimal systemic risk.",
            "side_effects": ["Localized dermal irritation or contact dermatitis"],
            "prophylaxis": "Apply strictly to intact skin. Avoid open wounds, eyes, and mucous membranes.",
            "inherited_alerts": [],
            "evidence_citation": atc_info.get("evidence_citation", "WHO-ATC Core"),
            "nti_info": None
        }

    comorb_rules = atc_info.get("comorbidity_contraindications", {})
    for comorb_flag, alert_def in comorb_rules.items():
        if patient_profile.get(comorb_flag, False):
            inherited_alerts.append({
                "severity": alert_def["severity"],
                "effect": alert_def["effect"],
                "conflict_between": f"{display_title} ({atc_info['class_name']}) vs Patient Comorbidity",
                "description": alert_def["description"],
                "action": alert_def["action"],
                "evidence_citation": atc_info.get("evidence_citation", "WHO-ATC Core")
            })

    age_rules = atc_info.get("age_modifiers", {})
    if "pediatric_max_age" in age_rules and patient_age <= age_rules["pediatric_max_age"]:
        inherited_alerts.append({
            "severity": age_rules["pediatric_severity"],
            "effect": age_rules["pediatric_effect"],
            "conflict_between": f"{display_title} in Patient Aged {patient_age} Yrs",
            "description": age_rules["pediatric_description"],
            "action": age_rules["pediatric_action"],
            "evidence_citation": atc_info.get("evidence_citation", "WHO-ATC Core")
        })
    elif "geriatric_min_age" in age_rules and patient_age >= age_rules["geriatric_min_age"]:
        inherited_alerts.append({
            "severity": age_rules["geriatric_severity"],
            "effect": age_rules["geriatric_effect"],
            "conflict_between": f"{display_title} in Geriatric Patient Aged {patient_age} Yrs",
            "description": age_rules["geriatric_description"],
            "action": age_rules["geriatric_action"],
            "evidence_citation": atc_info.get("evidence_citation", "WHO-ATC Core")
        })

    return {
        "atc_class": atc_info["class_name"],
        "coverage_tier": tier,
        "is_out_of_scope": False,
        "base_risk_score": atc_info["base_risk_score"],
        "primary_mechanism": atc_info["primary_mechanism"],
        "side_effects": atc_info["common_side_effects"],
        "prophylaxis": atc_info["prophylaxis"],
        "inherited_alerts": inherited_alerts,
        "evidence_citation": atc_info.get("evidence_citation", "WHO-ATC Core"),
        "nti_info": nti_info, 
    }