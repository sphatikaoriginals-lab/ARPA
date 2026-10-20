"""
ARPA Clinical Rule Engine & Dynamic Risk Intelligence (v4.1 Anti-Alert-Fatigue Edition)
=======================================================================================
Upgrades:
1. Zero Alert Fatigue: Suppresses Black Box Warnings, Pediatric Banners, and Organ Clarifications
   when a medicine is prescribed to an age-appropriate patient with no active comorbidities or DDIs.
2. Context-Triggered Disclosure: Dynamically reveals Black Box Warnings, Organ Clarifications, and
   4-Step Cellular Biochemistry ONLY when an Age, Comorbidity, Duplication, or DDI trigger occurs.
"""

import re
from collections import Counter
from typing import Dict, List, Any, Tuple, Optional, Set
from atc_engine import resolve_atc_inheritance, strip_and_extract_salt, detect_administration_route

MOLECULE_OVERRIDES: Dict[str, Dict[str, Any]] = {
    # --- CRITICAL GUARDRAILS & ANALGESICS ---
    "aspirin": {
        "class": "Salicylate / NSAID / Antiplatelet",
        "base_risk_score": 30,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "STRICTLY CONTRAINDICATED (< 16 Years)",
        "pediatric_dosage": "Prohibited in pediatric viral fevers (Risk of Reye's Syndrome)",
        "black_box_warning": "Fatal Reye's syndrome in children/adolescents (<16 yrs) with viral illnesses; severe GI bleeding hazard in active ulceration.",
        "evidence_citation": "FDA Boxed Warning / CDC Reye's Advisory",
        "side_effects": ["Dyspepsia", "Minor easy bruising"],
        "prophylaxis": "Administer after food. Co-prescribe PPI if used long-term.",
        "pediatric_fatal_rule": {
            "max_age": 16,
            "severity": "FATAL",
            "effect": "Pediatric Risk: Reye's Syndrome (Microvesicular Hepatic Steatosis & Encephalopathy)",
            "description": "Salicylates uncouple hepatic mitochondrial beta-oxidation during pediatric viral illnesses, precipitating acute liver failure and cerebral edema.",
            "action": "Strictly Avoid Aspirin in patients <16 years. Substitute with weight-based Paracetamol.",
            "biochemistry": {
                "title": "Salicylate-Induced Mitochondrial Beta-Oxidation Uncoupling",
                "primary_mechanism": "Uncoupling of hepatic mitochondrial oxidative phosphorylation during viral stress.",
                "biochemical_steps": [
                    "1. Salicylate metabolites accumulate inside hepatic mitochondria.",
                    "2. Inhibition of long-chain 3-hydroxyacyl-CoA dehydrogenase arrests fatty acid beta-oxidation.",
                    "3. Opening of mitochondrial permeability transition pores causes rapid ATP depletion and microvesicular steatosis.",
                    "4. Hyperammonemia and cerebral astrocyte swelling precipitate acute fatal encephalopathy."
                ],
                "micro_possibilities": ["Microvesicular hepatic steatosis", "Hyperammonemia (>300 mcg/dL)", "Cerebral edema & herniation"],
                "affected_receptors": ["Mitochondrial Complex I/III", "LCHAD Enzyme Complex", "Astrocyte Aquaporin-4"]
            }
        }
    },
    "nimesulide": {
        "class": "Sulfonanilide COX-2 Inhibitor NSAID",
        "base_risk_score": 45,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "BANNED & CONTRAINDICATED (< 12 Years)",
        "pediatric_dosage": "Strictly Prohibited under 12 years by CDSCO/EMA",
        "black_box_warning": "Fulminant hepatic failure and fatal hepatotoxicity in children under 12 years and patients with hepatic impairment.",
        "evidence_citation": "CDSCO Gazette Notification G.S.R. 82(E)",
        "side_effects": ["Epigastric discomfort", "Mild nausea"],
        "prophylaxis": "Restrict adult duration to <15 days. Take postprandially.",
        "pediatric_fatal_rule": {
            "max_age": 12,
            "severity": "FATAL",
            "effect": "Pediatric Banned Sub-Group: Fulminant Hepatic Failure",
            "description": "Acute centrilobular liver necrosis in pediatric patients due to nitro-aromatic bioactivation.",
            "action": "Absolute Contraindication: Discontinue immediately. Use Paracetamol Syrup (15 mg/kg/dose).",
            "biochemistry": {
                "title": "Nitro-Aromatic Reductive Bioactivation & Hepatocyte Necrosis",
                "primary_mechanism": "Reductive bioactivation of the nitro-aromatic group into reactive diimine intermediates.",
                "biochemical_steps": [
                    "1. Hepatic nitroreductases convert Nimesulide's nitroarene moiety into reactive nitroso and hydroxylamine species.",
                    "2. Covalent binding to mitochondrial respiratory proteins collapses the inner membrane proton gradient.",
                    "3. Massive reactive oxygen species (ROS) generation depletes immature pediatric glutathione stores.",
                    "4. Centrilobular hepatocyte apoptosis and fulminant hepatic failure ensue."
                ],
                "micro_possibilities": ["ALT/AST > 2,000 IU/L", "Centrilobular necrosis", "Coagulopathic encephalopathy"],
                "affected_receptors": ["Hepatic CYP2C9 / Nitroreductase", "Mitochondrial ATP Synthase", "Hepatocyte Bile Salt Export Pump (BSEP)"]
            }
        }
    },
    "ibuprofen": {
        "class": "Propionic Acid Derivative NSAID",
        "base_risk_score": 25,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (> 6 Months: 10 mg/kg/dose Q6-8H) | RESTRICTED (< 6 Months)",
        "pediatric_dosage": "10 mg/kg/dose every 6-8 hours for children >6 months with adequate hydration.",
        "black_box_warning": "Risk of serious GI ulceration/bleeding, acute kidney injury in renal compromise, and premature ductus arteriosus closure in 3rd-trimester pregnancy.",
        "evidence_citation": "AAP Pediatric Pharmacology Guidelines",
        "side_effects": ["Mild dyspepsia", "Heartburn"],
        "prophylaxis": "Administer postprandially with water.",
        "pediatric_fatal_rule": {
            "max_age": 1,
            "severity": "HIGH",
            "effect": "Infant Restriction: Enhanced Nephrotoxicity Risk in Young Infants",
            "description": "Immature renal prostaglandin autoregulation elevates acute kidney injury risk in infants.",
            "action": "Prefer single-agent weight-based Paracetamol drops in infants.",
            "biochemistry": {
                "title": "Neonatal Renal Prostaglandin Depletion & Glomerular Arrest",
                "primary_mechanism": "Inhibition of COX-mediated vasodilatory PGE2 in developing nephrons.",
                "biochemical_steps": [
                    "1. Infant kidneys rely heavily on local PGE2 and PGI2 to maintain afferent arteriolar patency.",
                    "2. Ibuprofen blocks COX-1/COX-2, leaving angiotensin-II vasoconstriction unopposed.",
                    "3. Pre-glomerular vasoconstriction sharply reduces hydrostatic filtration pressure.",
                    "4. Oliguric acute kidney injury and delayed clearance occur."
                ],
                "micro_possibilities": ["Acute oliguria", "Renal cortical ischemia", "Gastric mucosal erosion"],
                "affected_receptors": ["COX-1 / COX-2 Isozymes", "Renal EP2/EP4 Prostaglandin Receptors"]
            }
        }
    },
    "aceclofenac": {
        "class": "Phenylacetic Acid Derivative NSAID (Preferential COX-2 Inhibitor)",
        "base_risk_score": 25,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "CONTRAINDICATED / NOT ESTABLISHED (< 18 Years)",
        "pediatric_dosage": "Adult formulation; safety and efficacy not established in children (<18 years).",
        "black_box_warning": "Increased risk of serious cardiovascular thrombotic events, GI ulceration/perforation, and acute nephrotoxicity in compromised patients.",
        "evidence_citation": "CDSCO / European Medicines Agency (EMA) NSAID Pharmacovigilance",
        "side_effects": ["Mild dyspepsia", "Epigastric fullness"],
        "prophylaxis": "Administer postprandially.",
        "pediatric_fatal_rule": {
            "max_age": 18,
            "severity": "HIGH",
            "effect": "Pediatric Safety Warning: Adult NSAID Formulation (Aceclofenac) in Child",
            "description": "Aceclofenac pharmacokinetics and safety are unestablished under 18 years; carries high risk of GI ulceration, hepatotoxicity, and renal ischemia.",
            "action": "Discontinue Aceclofenac in pediatric patient. Substitute with weight-adjusted Paracetamol (10-15 mg/kg/dose).",
            "biochemistry": {
                "title": "Pediatric Hepatic-Renal NSAID Overload & COX-1/2 Blockade",
                "primary_mechanism": "In-vivo conversion to 4'-hydroxyaceclofenac and diclofenac with mucosal/renal prostaglandin ablation.",
                "biochemical_steps": [
                    "1. Aceclofenac is hydrolyzed and oxidized via CYP2C9 into active diclofenac metabolites.",
                    "2. Systemic COX-1/COX-2 blockade strips gastric PGE2 cytoprotection in pediatric mucosa.",
                    "3. Renal afferent arteriolar dilation is blocked, dropping glomerular filtration pressure.",
                    "4. Reactive acyl-glucuronides stress immature hepatic biliary transporters."
                ],
                "micro_possibilities": ["Gastric erosive gastritis", "Pre-renal azotemia", "Hepatic transaminitis"],
                "affected_receptors": ["COX-1 / COX-2 Isozymes", "Hepatic CYP2C9", "Renal EP2/IP Receptors"]
            }
        }
    },
    "diclofenac": {
        "class": "Phenylacetic Acid Derivative NSAID",
        "base_risk_score": 30,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "RESTRICTED (< 18 Years - Specialist JIA use only)",
        "pediatric_dosage": "Not recommended for routine pediatric fever/pain.",
        "black_box_warning": "High risk of Major Adverse Cardiovascular Events (MACE), GI bleeding, and acute renal injury.",
        "evidence_citation": "FDA Boxed Warning / EMA PRAC Assessment",
        "side_effects": ["Dyspepsia", "Mild abdominal discomfort"],
        "prophylaxis": "Take immediately after meals.",
        "pediatric_fatal_rule": {
            "max_age": 18,
            "severity": "HIGH",
            "effect": "Pediatric Safety Warning: Systemic Diclofenac in Child",
            "description": "Routine use of Diclofenac in children carries elevated gastrointestinal and nephrotoxic risks.",
            "action": "Substitute with weight-based Paracetamol.",
            "biochemistry": {
                "title": "Pediatric COX-1/2 Prostaglandin Depletion",
                "primary_mechanism": "Gastric and renal prostaglandin synthesis inhibition.",
                "biochemical_steps": [
                    "1. Diclofenac blocks COX-1 and COX-2 isozymes systemically.",
                    "2. Gastric mucosal blood flow and mucus secretion decline.",
                    "3. Renal afferent arteriolar dilation is blunted during febrile dehydration.",
                    "4. Hepatic CYP2C9 forms reactive acyl-glucuronides."
                ],
                "micro_possibilities": ["Mucosal erosion", "Prerenal azotemia", "Transaminitis"],
                "affected_receptors": ["COX-1 / COX-2 Isozymes", "Hepatic CYP2C9"]
            }
        }
    },
    "serratiopeptidase": {
        "class": "Proteolytic Anti-Edematous Enzyme",
        "base_risk_score": 15,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "CAUTION (Limited pediatric clinical trials)",
        "evidence_citation": "Clinical Enzyme Pharmacology / Indian National Formulary",
        "side_effects": ["Mild nausea", "Transient GI discomfort"],
        "prophylaxis": "Swallow enteric-coated tablet whole."
    },
    "paracetamol": {
        "class": "Antipyretic & Central Analgesic",
        "base_risk_score": 12,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (First-line Pediatric Analgesic/Antipyretic)",
        "pediatric_dosage": "10-15 mg/kg/dose every 4-6 hours (Max 60 mg/kg/day; do not exceed 5 doses/24h)",
        "black_box_warning": "Hepatotoxicity & Acute Liver Failure risk in cumulative overdose (>4g/day) or severe hepatic impairment.",
        "evidence_citation": "WHO Model Formulary for Children",
        "side_effects": ["Rare mild nausea", "Well tolerated at standard therapeutic doses"],
        "prophylaxis": "Standard dosing. Single dose <= 1000 mg; Max 4000 mg/day in adults."
    },

    # --- CARDIOVASCULAR, ANTIHYPERTENSIVES & STATINS ---
    "atorvastatin": {
        "class": "HMG-CoA Reductase Inhibitor (Lipophilic Statin — CYP3A4 Substrate)",
        "base_risk_score": 20,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "RESTRICTED (Contraindicated <10 Yrs; ≥10 Yrs ONLY for confirmed Heterozygous Familial Hypercholesterolemia)",
        "pediatric_dosage": "10 mg once daily MAX initial dose ONLY in specialist-confirmed HeFH (≥10 years). Prohibited for routine pediatric use.",
        "black_box_warning": "High risk of Rhabdomyolysis & Myoglobinuric Acute Kidney Injury when co-prescribed with CYP3A4 inhibitors (Clarithromycin, Itraconazole). Strictly contraindicated in pregnancy & active liver disease.",
        "evidence_citation": "ACC/AHA Pediatric Dyslipidemia Guidelines / FDA Safety Labeling",
        "side_effects": ["Mild transient myalgia", "Occasional headache"],
        "prophylaxis": "Administer in the evening. Periodic lipid and LFT monitoring.",
        "pediatric_fatal_rule": {
            "max_age": 16,
            "severity": "HIGH",
            "effect": "Pediatric Developmental & Myopathic Guardrail: Statin Therapy in Child",
            "description": "Atorvastatin inhibits de novo cholesterol synthesis required for pediatric steroidogenesis (cortisol/sex hormones) and CNS myelination, and carries heightened pediatric rhabdomyolysis risk if combined with CYP3A4 inhibitors.",
            "action": "Restricted in children (<10 yrs contraindicated; 10-15 yrs restricted strictly to confirmed Familial Hypercholesterolemia at 10mg max). Suspend immediately if macrolide antibiotics (Claribid) are co-prescribed.",
            "biochemistry": {
                "title": "Pediatric Mevalonate Pathway Arrest & Developmental Steroid/Myocyte Depletion",
                "primary_mechanism": "Competitive inhibition of hepatic and extrahepatic HMG-CoA reductase during growth phase.",
                "biochemical_steps": [
                    "1. Atorvastatin blocks conversion of HMG-CoA to mevalonate in hepatocytes and developing peripheral tissues.",
                    "2. Depletion of downstream isoprenoids (farnesyl-PP and geranylgeranyl-PP) impairs ubiquinone (CoQ10) synthesis in pediatric skeletal muscle.",
                    "3. Reduced cholesterol substrate availability blunts adrenal and gonadal steroidogenesis during prepubertal/pubertal development.",
                    "4. If pediatric CYP3A4 clearance is simultaneously inhibited, sarcolemmal ATP collapse precipitates acute rhabdomyolysis."
                ],
                "micro_possibilities": ["Skeletal myocyte CoQ10 depletion", "Elevated serum Creatine Kinase (CPK)", "Blunted steroidogenic precursor pool"],
                "affected_receptors": ["HMG-CoA Reductase Enzyme", "Hepatic OATP1B1 Transporter", "Intestinal/Hepatic CYP3A4"]
            }
        }
    },
    "rosuvastatin": {
        "class": "HMG-CoA Reductase Inhibitor (Hydrophilic Statin)",
        "base_risk_score": 20,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "RESTRICTED (Specialist Familial Hypercholesterolemia use only)",
        "pediatric_dosage": "5-10 mg once daily only in confirmed pediatric HeFH.",
        "black_box_warning": "Contraindicated in pregnancy, lactation, and active liver disease. Risk of myopathy/rhabdomyolysis.",
        "evidence_citation": "ACC/AHA Dyslipidemia Guidelines",
        "side_effects": ["Mild myalgia", "Headache"],
        "prophylaxis": "Can be taken any time of day. Monitor lipid profile.",
        "pediatric_fatal_rule": {
            "max_age": 16,
            "severity": "HIGH",
            "effect": "Pediatric Developmental Guardrail: Rosuvastatin in Child",
            "description": "Statin therapy in children is restricted exclusively to confirmed genetic hypercholesterolemia due to developmental cholesterol requirements.",
            "action": "Verify specialist HeFH diagnosis; suspend if interacting antimicrobials are prescribed.",
            "biochemistry": {
                "title": "Pediatric HMG-CoA Reductase Inhibition & Isoprenoid Depletion",
                "primary_mechanism": "Suppression of mevalonate and ubiquinone synthesis in growing tissues.",
                "biochemical_steps": [
                    "1. Rosuvastatin enters hepatocytes via OATP1B1 and inhibits HMG-CoA reductase.",
                    "2. De novo cholesterol and isoprenoid intermediate synthesis decreases.",
                    "3. Skeletal muscle ubiquinone (CoQ10) levels decline, predisposing to pediatric myopathy.",
                    "4. Steroid hormone precursor availability requires clinical developmental monitoring."
                ],
                "micro_possibilities": ["Myocyte CoQ10 reduction", "CPK elevation", "Transaminitis"],
                "affected_receptors": ["HMG-CoA Reductase", "Hepatic OATP1B1 (SLCO1B1)"]
            }
        }
    },
    "cilnidipine": {
        "class": "4th-Gen Dual L/N-Type Calcium Channel Blocker (CYP3A4 Substrate)",
        "base_risk_score": 20,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "UNESTABLISHED / OFF-LABEL IN PEDIATRICS (< 18 Years)",
        "pediatric_dosage": "Pediatric safety & weight-based dosing NOT established (Adult 5-20mg tablets risk severe pediatric hypotension; Amlodipine is preferred in children).",
        "black_box_warning": "Metabolized extensively by CYP3A4: Co-administration with Clarithromycin/Macrolides causes severe vasodilatory hypotension, syncope, and renal hypoperfusion.",
        "evidence_citation": "ESC/ESH Hypertension Guidelines / Pediatric Nephrology Consensus",
        "side_effects": ["Mild flushing", "Occasional dizziness"],
        "prophylaxis": "Take once daily at the same time. Monitor blood pressure.",
        "pediatric_fatal_rule": {
            "max_age": 18,
            "severity": "HIGH",
            "effect": "Pediatric Off-Label Hemodynamic Hazard: Dual L/N-Type CCB (Cilnidipine) in Child",
            "description": "Cilnidipine lacks established pediatric pharmacokinetics; blocking both vascular L-type and sympathetic N-type calcium channels in a child risks uncompensated hypotension and organ hypoperfusion.",
            "action": "Replace Cilacar (Cilnidipine) with pediatric-approved Amlodipine (0.1-0.2 mg/kg/day) under blood pressure monitoring.",
            "biochemistry": {
                "title": "Dual Vascular L-Type & Sympathetic N-Type Calcium Channel Blockade in Pediatrics",
                "primary_mechanism": "Simultaneous arteriolar smooth muscle relaxation and sympathetic norepinephrine release arrest.",
                "biochemical_steps": [
                    "1. Cilnidipine blocks Cav1.2 (L-type) channels on pediatric arteriolar smooth muscle, preventing Ca2+-calmodulin MLCK contraction.",
                    "2. Simultaneously, it blocks Cav2.2 (N-type) channels on sympathetic nerve terminals, halting synaptic norepinephrine exocytosis.",
                    "3. Because children have lower baseline systemic vascular resistance, arterial pressure drops sharply.",
                    "4. N-type sympathetic blockade prevents baroreceptor-mediated reflex tachycardia, leading to uncompensated hypotension and renal hypoperfusion."
                ],
                "micro_possibilities": ["Profound arterial vasodilation", "Abolished baroreceptor reflex tachycardia", "Pre-renal glomerular hypoperfusion"],
                "affected_receptors": ["Vascular Smooth Muscle Cav1.2 (L-Type)", "Sympathetic Neuronal Cav2.2 (N-Type)", "Hepatic CYP3A4"]
            }
        }
    },
    "clarithromycin": {
        "class": "Macrolide Antibiotic (CYP3A4, OATP1B1 & P-gp Inhibitor)",
        "base_risk_score": 25,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE AS WEIGHT-BASED SUSPENSION (7.5 mg/kg Q12H)",
        "pediatric_dosage": "7.5 mg/kg twice daily (Max 500 mg/dose).",
        "black_box_warning": "Potent CYP3A4 & OATP1B1 Inhibitor: Causes fatal Rhabdomyolysis with Statins (Atorvastatin), severe Hypotension with CCBs (Cilnidipine/Amlodipine), and QTc prolongation / Torsades de Pointes.",
        "evidence_citation": "FDA Drug Safety Communication / CredibleMeds QT List",
        "side_effects": ["Metallic taste (dysgeusia)", "Mild GI discomfort"],
        "prophylaxis": "Can be taken with or without food. Complete full antibiotic course."
    },
    "telmisartan": {
        "class": "Angiotensin II Receptor Blocker (ARB / RAAS Inhibitor)",
        "base_risk_score": 20,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "RESTRICTED (< 18 Years — Losartan/Enalapril preferred in pediatrics)",
        "pediatric_dosage": "Safety and efficacy not established in children <18 years.",
        "black_box_warning": "Fetal toxicity: Drugs that act directly on the renin-angiotensin system cause fetal renal dysplasia, oligohydramnios, and death (Contraindicated in Pregnancy).",
        "evidence_citation": "KDIGO / AHA Hypertension Guidelines / FDA Boxed Warning",
        "side_effects": ["Mild dizziness", "Orthostatic lightheadedness"],
        "prophylaxis": "Monitor blood pressure and serum electrolytes periodically."
    },
    "amlodipine": {
        "class": "Dihydropyridine Calcium Channel Blocker (CCB)",
        "base_risk_score": 18,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (> 6 Years: 2.5-5 mg once daily or 0.1-0.2 mg/kg/day)",
        "pediatric_dosage": "0.1 to 0.2 mg/kg once daily (Max 5 mg/day in children 6-17 years).",
        "black_box_warning": "CYP3A4 substrate: Co-administration with strong CYP3A4 inhibitors (Clarithromycin) precipitates severe hypotension and edema.",
        "evidence_citation": "JNC 8 / AAP Pediatric Hypertension Guidelines",
        "side_effects": ["Dose-dependent ankle edema", "Mild flushing"],
        "prophylaxis": "Administer once daily. Monitor blood pressure."
    },
    "metformin": {
        "class": "Biguanide Antihyperglycemic",
        "base_risk_score": 18,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (≥ 10 Years for Type 2 Diabetes Mellitus)",
        "pediatric_dosage": "500 mg twice daily with meals (Max 2000 mg/day in children ≥10 years).",
        "black_box_warning": "Metformin-Associated Lactic Acidosis (MALA) in renal failure (eGFR < 30), hepatic insufficiency, or acute heart failure.",
        "evidence_citation": "ADA Standards of Medical Care in Diabetes",
        "side_effects": ["Metallic taste", "Transient mild GI upset"],
        "prophylaxis": "Take with meals to minimize GI intolerance."
    },
    "pantoprazole": {
        "class": "Proton Pump Inhibitor (Gastric H+/K+ ATPase Blocker)",
        "base_risk_score": 10,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (> 5 Years weight-adjusted: 1 mg/kg/day)",
        "pediatric_dosage": "15-40 kg: 20 mg once daily; >40 kg: 40 mg once daily.",
        "evidence_citation": "ACG Clinical Guideline: GERD & Peptic Ulcer",
        "side_effects": ["Mild headache", "Well tolerated"],
        "prophylaxis": "Administer 30-45 minutes before breakfast on an empty stomach."
    },
    "domperidone": {
        "class": "Peripheral Dopamine D2 Antagonist (Prokinetic / Antiemetic)",
        "base_risk_score": 25,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "CAUTION (0.25 mg/kg/dose; avoid prolonged use)",
        "black_box_warning": "Risk of QTc interval prolongation, serious ventricular arrhythmias, and sudden cardiac death when combined with QT-prolonging drugs or in cardiac disease.",
        "evidence_citation": "EMA PRAC / MHRA Drug Safety Update",
        "side_effects": ["Dry mouth", "Mild headache"],
        "prophylaxis": "Take 15-30 minutes before meals for shortest required duration."
    },

    # --- ANTIMICROBIALS & ANTIBIOTICS ---
    "amoxicillin": {
        "class": "Beta-Lactam Antibiotic / Aminopenicillin",
        "base_risk_score": 15,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (First-line Weight-based dosing)",
        "pediatric_dosage": "25-50 mg/kg/day divided 8-12 hourly.",
        "evidence_citation": "STG: Bacterial Infection Guidelines",
        "side_effects": ["Mild loose stools", "Nausea"],
        "prophylaxis": "Verify absence of penicillin allergy prior to administration. Complete full course."
    },
    "clavulanic acid": {
        "class": "Beta-Lactamase Inhibitor",
        "base_risk_score": 18,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (Combined with Amoxicillin)",
        "pediatric_dosage": "Administered in 7:1 or 14:1 ratio with Amoxicillin.",
        "evidence_citation": "STG: Resistant Bacterial Infections",
        "side_effects": ["Mild diarrhea", "Nausea"],
        "prophylaxis": "Administer at the start of a meal to minimize GI intolerance."
    },
    "azithromycin": {
        "class": "Macrolide Antibiotic (Azalide)",
        "base_risk_score": 20,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (10 mg/kg once daily for 3 days)",
        "pediatric_dosage": "10 mg/kg once daily for 3 days (Max 500 mg/day).",
        "black_box_warning": "QTc interval prolongation and polymorphic ventricular tachycardia (Torsades de Pointes) in cardiac arrhythmia or with QTc-prolonging co-therapy.",
        "evidence_citation": "CredibleMeds / STG Respiratory Infections",
        "side_effects": ["Mild abdominal cramping", "Nausea"],
        "prophylaxis": "Can be taken with or without food. Complete 3-5 day course."
    },
    "ciprofloxacin": {
        "class": "Fluoroquinolone Antibiotic (DNA Gyrase Inhibitor)",
        "base_risk_score": 32,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "RESTRICTED (< 18 Years — Risk of Juvenile Weight-Bearing Cartilage Arthropathy)",
        "pediatric_dosage": "Avoid in <18 yrs unless multi-drug resistant typhoid/Pseudomonas (10-15 mg/kg Q12H).",
        "black_box_warning": "Tendonitis/tendon rupture, peripheral neuropathy, CNS seizures, pediatric arthropathy, and acute hemolysis in G6PD deficiency.",
        "evidence_citation": "FDA Boxed Warning / IAP Typhoid Guidelines",
        "side_effects": ["Nausea", "Mild dizziness"],
        "prophylaxis": "Maintain hydration. Separate from calcium/iron/dairy antacids by 2 hours.",
        "pediatric_fatal_rule": {
            "max_age": 18,
            "severity": "HIGH",
            "effect": "Pediatric Musculoskeletal Restriction: Fluoroquinolone Cartilage Arthropathy",
            "description": "Ciprofloxacin chelates magnesium ions in juvenile weight-bearing articular cartilage, causing chondrocyte apoptosis and matrix blister formation.",
            "action": "Avoid in patients <18 years unless no safe beta-lactam/macrolide alternative (e.g., Cefixime or Azithromycin) exists.",
            "biochemistry": {
                "title": "Juvenile Chondrocyte Magnesium Chelation & Matrix Metalloproteinase Upregulation",
                "primary_mechanism": "Divalent cation (Mg2+) chelation in avascular epiphyseal growth plates.",
                "biochemical_steps": [
                    "1. Ciprofloxacin accumulates in juvenile articular cartilage and chelates extracellular Mg2+ ions.",
                    "2. Functional magnesium deficiency disrupts beta-1 integrin signaling between chondrocytes and extracellular matrix.",
                    "3. Upregulation of Matrix Metalloproteinases (MMP-1, MMP-3, MMP-13) degrades Type II collagen and proteoglycans.",
                    "4. Chondrocyte apoptosis and fluid-filled cartilage fissures cause weight-bearing arthropathy and tendonopathy."
                ],
                "micro_possibilities": ["Epiphyseal chondrocyte necrosis", "Collagen Type-II degradation", "Weight-bearing joint effusion"],
                "affected_receptors": ["Chondrocyte Beta-1 Integrin", "Matrix Metalloproteinase (MMP-13)", "Topoisomerase II"]
            }
        }
    },
    "cefixime": {
        "class": "Third-Generation Cephalosporin Antibiotic",
        "base_risk_score": 16,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (8 mg/kg/day once daily or divided Q12H)",
        "pediatric_dosage": "8 mg/kg/day (up to 20 mg/kg/day in enteric fever).",
        "evidence_citation": "STG: Enteric Fever / UTI",
        "side_effects": ["Mild loose stools", "Dyspepsia"],
        "prophylaxis": "Complete full prescribed antibiotic course."
    },

    # --- EMERGENCY & ACLS ---
    "epinephrine": {
        "class": "Sympathomimetic / Catecholamine",
        "base_risk_score": 85,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "LIFE-SAVING (Weight-based dosing)",
        "pediatric_dosage": "0.01 mg/kg IM/IV for anaphylaxis/arrest.",
        "evidence_citation": "AHA ACLS / STG: Anaphylaxis",
        "side_effects": ["Tachycardia", "Hypertension", "Arrhythmia", "Myocardial Ischemia"],
        "prophylaxis": "Primary agent for cardiac arrest and anaphylactic shock."
    },
    "adrenaline": {
        "class": "Sympathomimetic / Catecholamine",
        "base_risk_score": 85,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "LIFE-SAVING (Weight-based dosing)",
        "pediatric_dosage": "0.01 mg/kg IM/IV for anaphylaxis/arrest.",
        "evidence_citation": "AHA ACLS / STG: Anaphylaxis",
        "side_effects": ["Tachycardia", "Hypertension", "Arrhythmia", "Myocardial Ischemia"],
        "prophylaxis": "Primary agent for cardiac arrest and anaphylactic shock."
    },
    "amiodarone": {
        "class": "Class III Antiarrhythmic",
        "base_risk_score": 75,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "CAUTION (ACLS Protocol: 5 mg/kg IV/IO)",
        "black_box_warning": "Pulmonary toxicity, hepatotoxicity, and proarrhythmic effects.",
        "evidence_citation": "AHA ACLS Guidelines",
        "side_effects": ["Hypotension", "Bradycardia", "Thyroid dysfunction", "Pulmonary fibrosis"],
        "prophylaxis": "Used for shock-refractory VF/pulseless VT."
    },
    "atropine": {
        "class": "Anticholinergic / Antimuscarinic",
        "base_risk_score": 60,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "CAUTION (Weight-based dosing: 0.02 mg/kg)",
        "evidence_citation": "STG: Organophosphorus Poisoning / ACLS",
        "side_effects": ["Tachycardia", "Mydriasis", "Urinary retention", "Dry mouth"],
        "prophylaxis": "Primary antidote for OP poisoning and symptomatic bradycardia."
    },
    "pralidoxime": {
        "class": "Cholinesterase Reactivator",
        "base_risk_score": 50,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (25-50 mg/kg IV infusion)",
        "evidence_citation": "STG: Organophosphorus Poisoning",
        "side_effects": ["Dizziness", "Blurred vision", "Tachycardia"],
        "prophylaxis": "Must be administered alongside Atropine."
    },
    "mannitol": {
        "class": "Osmotic Diuretic",
        "base_risk_score": 55,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "CAUTION (0.25-1 g/kg IV over 20-30 min)",
        "evidence_citation": "STG: Head Injury / Cerebral Edema",
        "side_effects": ["Fluid/electrolyte imbalance", "Rebound ICP increase", "Osmotic nephrosis"],
        "prophylaxis": "Used to rapidly reduce intraocular or intracranial pressure."
    },
    "hydrocortisone": {
        "class": "Systemic Corticosteroid",
        "base_risk_score": 45,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "SAFE (Short-term emergency: 1-2 mg/kg IV)",
        "evidence_citation": "STG: Shock / Anaphylaxis",
        "side_effects": ["Hyperglycemia", "Immunosuppression", "Hypertension"],
        "prophylaxis": "Adjunct therapy in severe anaphylaxis and septic shock."
    },
    "anti-snake venom": {
        "class": "Antivenin",
        "base_risk_score": 80,
        "coverage_tier": "TIER_1_FULL",
        "pediatric_safety": "LIFE-SAVING (Same dose as adults — neutralizes venom load)",
        "black_box_warning": "High risk of anaphylactic reaction.",
        "evidence_citation": "STG: Snake Bite Guidelines",
        "side_effects": ["Anaphylaxis", "Serum sickness"],
        "prophylaxis": "Administer only if signs of systemic envenomation exist. Keep adrenaline ready."
    }
}

# --------------------------------------------------------------------------
# SEVERE DDI RULES (All Equipped with 4-Step Cellular Biochemistry)
# --------------------------------------------------------------------------
SEVERE_DDI_RULES: List[Dict[str, Any]] = [
    {
        "pair": ("atorvastatin", "clarithromycin"),
        "severity": "FATAL",
        "effect": "Severe Rhabdomyolysis & Myoglobinuric Acute Renal Failure",
        "conflict_between": "Atorvastatin + Clarithromycin (Claribid)",
        "description": "Clarithromycin potent CYP3A4 & OATP1B1 inhibition elevates Atorvastatin plasma AUC by 400-500%, triggering skeletal myocyte necrosis, massive CPK surge, and myoglobinuric acute kidney injury.",
        "action": "Immediate Cessation: Substitute Clarithromycin with Azithromycin or suspend Atorvastatin immediately.",
        "evidence_citation": "FDA Drug Safety Communication / Clin Pharmacol Ther",
        "biochemistry": {
            "title": "CYP3A4 & OATP1B1 Inhibition — Apoptotic Sarcolemmal Cascade",
            "primary_mechanism": "Irreversible CYP3A4 heme-adduct formation & hepatic OATP1B1 uptake blockade.",
            "biochemical_steps": [
                "1. Clarithromycin nitroso-metabolites complex with CYP3A4 heme iron in gut and liver microsomes.",
                "2. Systemic plasma accumulation of active lipophilic Atorvastatin acid surges >5-fold.",
                "3. Depletion of farnesyl/geranylgeranyl pyrophosphate arrests Rab/Rho GTPase prenylation in skeletal myocytes.",
                "4. Sarcolemmal lysis releases massive myoglobin into renal tubules, precipitating Tamm-Horsfall cast obstruction and AKI."
            ],
            "micro_possibilities": ["Serum CPK > 10,000 IU/L", "Myoglobinuric acute tubular necrosis", "Hyperkalemic cardiac arrest"],
            "affected_receptors": ["CYP3A4 Hemoprotein", "Hepatic OATP1B1 Transporter", "Skeletal Muscle RyR1 Channel"]
        }
    },
    {
        "pair": ("rosuvastatin", "clarithromycin"),
        "severity": "HIGH",
        "effect": "OATP1B1 Transporter Blockade & Statin Myopathy Risk",
        "conflict_between": "Rosuvastatin + Clarithromycin (Claribid)",
        "description": "Clarithromycin inhibits hepatic OATP1B1/1B3 uptake transporters, elevating systemic Rosuvastatin exposure and myotoxicity risk.",
        "action": "Temporarily suspend Statin during macrolide course or switch antibiotic to Azithromycin.",
        "evidence_citation": "Clinical Pharmacokinetics / FDA Statin Interaction Advisory",
        "biochemistry": {
            "title": "Hepatic OATP1B1 Efflux/Uptake Competition & Myocyte Stress",
            "primary_mechanism": "Blockade of SLCO1B1-mediated hepatocyte clearance.",
            "biochemical_steps": [
                "1. Clarithromycin competitively inhibits SLCO1B1 (OATP1B1) on the basolateral hepatocyte membrane.",
                "2. Uncleared hydrophilic Rosuvastatin remains in systemic circulation, doubling skeletal muscle exposure.",
                "3. Intramyocellular mevalonate and ubiquinone (CoQ10) synthesis drops.",
                "4. Mitochondrial dysfunction triggers myalgia, myopathy, and elevated serum creatine kinase."
            ],
            "micro_possibilities": ["2x Plasma Rosuvastatin AUC", "Myocyte CoQ10 depletion", "Transaminitis & myopathy"],
            "affected_receptors": ["Hepatic OATP1B1 (SLCO1B1)", "Skeletal Muscle HMG-CoA Reductase"]
        }
    },
    {
        "pair": ("cilnidipine", "clarithromycin"),
        "severity": "HIGH",
        "effect": "Profound Vasodilatory Hypotension, Syncope & Synergistic Renal Hypoperfusion",
        "conflict_between": "Cilnidipine (Cilacar) + Clarithromycin (Claribid)",
        "description": "Clarithromycin blocks CYP3A4-mediated first-pass clearance of Cilnidipine, causing a 2-3x surge in dual L/N-type calcium channel blockade, severe hypotension (without compensatory reflex tachycardia), and acute renal hypoperfusion.",
        "action": "Avoid combination: Switch Clarithromycin to Azithromycin, or hold/reduce Cilnidipine under strict BP monitoring.",
        "evidence_citation": "CMAJ / FDA CYP3A4-Calcium Channel Blocker Shock Advisory",
        "biochemistry": {
            "title": "CYP3A4 Metabolic Arrest & Dual L/N-Type Calcium Channel Shock",
            "primary_mechanism": "Inhibition of intestinal and hepatic CYP3A4 clearance of dihydropyridine CCB.",
            "biochemical_steps": [
                "1. Clarithromycin inactivates CYP3A4 in enterocytes and hepatocytes, blocking Cilnidipine oxidative de-esterification.",
                "2. Systemic Cilnidipine bioavailability surges >250%, saturating vascular Cav1.2 (L-type) channels.",
                "3. Simultaneous blockade of sympathetic Cav2.2 (N-type) channels prevents compensatory norepinephrine release and reflex tachycardia.",
                "4. Uncompensated systemic arterial vasodilation drops renal perfusion pressure, accelerating acute tubular necrosis."
            ],
            "micro_possibilities": ["Vasodilatory arterial hypotension", "Blunted sympathetic baroreceptor reflex", "Ischemic pre-renal AKI"],
            "affected_receptors": ["Intestinal/Hepatic CYP3A4", "Vascular Cav1.2 (L-Type Ca2+)", "Sympathetic Cav2.2 (N-Type Ca2+)"]
        }
    },
    {
        "pair": ("amlodipine", "clarithromycin"),
        "severity": "HIGH",
        "effect": "CYP3A4-Mediated Severe Hypotension, Vasogenic Edema & Acute Kidney Injury",
        "conflict_between": "Amlodipine + Clarithromycin (Claribid)",
        "description": "Clarithromycin inhibits CYP3A4 metabolism of Amlodipine, doubling plasma CCB concentrations and precipitating profound hypotension and ischemic AKI.",
        "action": "Substitute Clarithromycin with Azithromycin or reduce Amlodipine dose by 50% with BP monitoring.",
        "evidence_citation": "JAMA / FDA CCB-Macrolide Interaction Warning",
        "biochemistry": {
            "title": "CYP3A4 Clearance Blockade & L-Type Calcium Channel Over-Inhibition",
            "primary_mechanism": "Impaired hepatic CYP3A4 pyridine oxidation of Amlodipine.",
            "biochemical_steps": [
                "1. Clarithromycin blocks hepatic CYP3A4, extending Amlodipine's half-life beyond 60-80 hours.",
                "2. Excess Amlodipine hyper-polarizes vascular smooth muscle via Cav1.2 blockade.",
                "3. Pre-capillary arteriolar dilation without venular dilation causes transcapillary fluid extravasation (edema) and systemic hypotension.",
                "4. Reduced mean arterial pressure impairs renal glomerular autoregulation."
            ],
            "micro_possibilities": ["Prolonged Amlodipine t1/2 (>70h)", "Refractory hypotension", "Pre-renal azotemia"],
            "affected_receptors": ["Hepatic CYP3A4", "Vascular L-Type Ca2+ Channel (Cav1.2)"]
        }
    },
    {
        "pair": ("atorvastatin", "cilnidipine"),
        "severity": "MODERATE",
        "effect": "Competitive CYP3A4 Substrate Saturation (Amplified Statin & CCB Exposure)",
        "conflict_between": "Atorvastatin + Cilnidipine (Cilacar)",
        "description": "Both Atorvastatin and Cilnidipine compete for hepatic CYP3A4 binding sites; co-administration elevates statin AUC and becomes critical if a third CYP3A4 inhibitor (like Clarithromycin) is added.",
        "action": "Monitor for myalgia and hypotension; strictly avoid adding macrolide or azole CYP3A4 inhibitors.",
        "evidence_citation": "Clinical Pharmacokinetics — Dual CYP3A4 Substrate Kinetics",
        "biochemistry": {
            "title": "Dual CYP3A4 Substrate Michaelis-Menten Competition",
            "primary_mechanism": "Competitive binding at the CYP3A4 catalytic pocket and P-glycoprotein efflux pump.",
            "biochemical_steps": [
                "1. Dihydropyridine CCB (Cilnidipine) and lipophilic Statin (Atorvastatin) both require CYP3A4 oxidation for clearance.",
                "2. Competitive occupancy slows first-pass intestinal and hepatic extraction of Atorvastatin lactone/acid.",
                "3. Plasma Atorvastatin Cmax and AUC rise by 20-35% (and >400% if a macrolide inhibitor is present).",
                "4. Increased myocyte statin uptake elevates risk of myopathy and transaminitis."
            ],
            "micro_possibilities": ["Competitive CYP3A4 saturation", "Elevated plasma statin AUC", "Subclinical myopathy risk"],
            "affected_receptors": ["Hepatic/Intestinal CYP3A4", "P-glycoprotein (ABCB1) Efflux Pump"]
        }
    },
    {
        "pair": ("telmisartan", "spironolactone"),
        "severity": "FATAL",
        "effect": "Severe Life-Threatening Hyperkalemia",
        "conflict_between": "Telmisartan + Spironolactone",
        "description": "Dual blockade of aldosterone release and mineralocorticoid receptors halts distal tubule potassium excretion, precipitating lethal ventricular arrhythmias.",
        "action": "Strict Monitoring Mandatory: Frequently screen serum potassium; adjust doses.",
        "evidence_citation": "KDIGO Guidelines / AHA Potassium Balance Advisory",
        "biochemistry": {
            "title": "Dual RAAS-Aldosterone Blockade & Cortical Collecting Duct Arrest",
            "primary_mechanism": "Synergistic suppression of ENaC-mediated electrogenic potassium secretion.",
            "biochemical_steps": [
                "1. Telmisartan blocks AT1 receptors in the adrenal zona glomerulosa, suppressing aldosterone synthesis.",
                "2. Spironolactone competitively antagonizes intracellular mineralocorticoid receptors in principal cells.",
                "3. Apical ENaC sodium channels and ROMK potassium channels are downregulated, abolishing lumen-negative potential.",
                "4. Extracellular K+ accumulation (>6.5 mEq/L) depolarizes cardiac resting membrane potential, inactivating Na+ channels."
            ],
            "micro_possibilities": ["Serum K+ > 6.5 mEq/L", "Peaked T-waves & sine-wave ECG", "Ventricular fibrillation / Asystole"],
            "affected_receptors": ["Adrenal AT1 Receptor", "Cytosolic Mineralocorticoid Receptor (NR3C2)", "Renal Apical ENaC / ROMK Channels"]
        }
    },
    {
        "pair": ("telmisartan", "aceclofenac"),
        "severity": "HIGH",
        "effect": "Acute Renal Hemodynamic Injury ('Double Whammy') & Antihypertensive Antagonism",
        "conflict_between": "Telmisartan + Aceclofenac",
        "description": "Aceclofenac constricts the afferent renal arteriole via prostaglandin inhibition while Telmisartan dilates the efferent arteriole, collapsing glomerular filtration pressure.",
        "action": "Avoid concurrent NSAID + ARB therapy. Substitute Aceclofenac with Paracetamol.",
        "evidence_citation": "KDIGO AKI Guidelines / Clinical Nephrology",
        "biochemistry": {
            "title": "Glomerular Hemodynamic Collapse ('Double Whammy' Cascade)",
            "primary_mechanism": "Simultaneous afferent arteriolar constriction and efferent arteriolar dilation.",
            "biochemical_steps": [
                "1. Aceclofenac inhibits renal COX-1/COX-2, depleting vasodilatory prostacyclin (PGI2) and PGE2.",
                "2. Unopposed pre-glomerular vasoconstriction narrows the afferent arteriole, reducing renal plasma inflow.",
                "3. Telmisartan blocks AT1 receptors on the efferent arteriole, preventing compensatory efferent constriction.",
                "4. Intraglomerular capillary hydrostatic pressure (P_GC) plummets, causing acute ischemic GFR collapse."
            ],
            "micro_possibilities": ["Abrupt serum creatinine rise (>0.3 mg/dL in 48h)", "Ischemic acute tubular injury", "Loss of antihypertensive control"],
            "affected_receptors": ["Renal COX-1 / COX-2", "Afferent EP2/IP Receptors", "Efferent AT1 Receptor"]
        }
    },
    {
        "pair": ("telmisartan", "ibuprofen"),
        "severity": "HIGH",
        "effect": "Acute Kidney Injury & Loss of Blood Pressure Control",
        "conflict_between": "Telmisartan + Ibuprofen",
        "description": "Concurrent ARB and NSAID therapy blunts renal autoregulation and antagonizes natriuresis.",
        "action": "Avoid combination; monitor serum creatinine and potassium if unavoidable.",
        "evidence_citation": "KDIGO Guidelines / AHA Scientific Statement",
        "biochemistry": {
            "title": "Glomerular Autoregulatory Failure & Natriuretic Antagonism",
            "primary_mechanism": "Dual disruption of trans-glomerular pressure gradient and macula densa signaling.",
            "biochemical_steps": [
                "1. Ibuprofen blocks COX-derived PGE2 synthesis in the renal cortex and medulla.",
                "2. Afferent arteriolar resistance rises sharply while thick ascending limb Na-K-2Cl cotransport increases.",
                "3. Telmisartan dilates the efferent arteriole via AT1 blockade, abolishing filtration fraction compensation.",
                "4. Net glomerular filtration pressure drops while sodium/water retention blunts Telmisartan's antihypertensive effect."
            ],
            "micro_possibilities": ["Acute GFR decline", "Hyperkalemia", "Refractory systolic hypertension"],
            "affected_receptors": ["Renal Cyclooxygenase (COX-1/2)", "Glomerular Efferent AT1 Receptor", "Tubular NKCC2 Transporter"]
        }
    },
    {
        "pair": ("telmisartan", "diclofenac"),
        "severity": "HIGH",
        "effect": "Severe Nephrotoxicity & Attenuated Antihypertensive Efficacy",
        "conflict_between": "Telmisartan + Diclofenac",
        "description": "Synergistic reduction in glomerular filtration rate and heightened risk of hyperkalemia.",
        "action": "Discontinue Diclofenac; use non-NSAID analgesia.",
        "evidence_citation": "KDIGO Guidelines",
        "biochemistry": {
            "title": "Synergistic Glomerular Hypoperfusion & Renal Ischemia",
            "primary_mechanism": "Afferent prostaglandin depletion paired with efferent angiotensin-II blockade.",
            "biochemical_steps": [
                "1. Diclofenac potently inhibits renal prostaglandin E2 and prostacyclin synthesis.",
                "2. Afferent arteriolar vasoconstriction decreases blood flow entering the glomerular tuft.",
                "3. Telmisartan prevents angiotensin-II mediated efferent arteriolar tone.",
                "4. Hydrostatic filtration pressure collapses, triggering prerenal azotemia and acute tubular necrosis."
            ],
            "micro_possibilities": ["Prerenal azotemia", "Hyperkalemic acidosis", "Renal papillary ischemia"],
            "affected_receptors": ["COX-1 / COX-2 Isozymes", "Vascular AT1 Receptor"]
        }
    },
    {
        "pair": ("azithromycin", "ondansetron"),
        "severity": "HIGH",
        "effect": "Synergistic QTc Prolongation & Torsades de Pointes",
        "conflict_between": "Azithromycin + Ondansetron",
        "description": "Dual inhibition of cardiac hERG potassium channels prolongs repolarization.",
        "action": "ECG Monitoring: Substitute Ondansetron with Metoclopramide.",
        "evidence_citation": "CredibleMeds QTdrugs List (Category 1)",
        "biochemistry": {
            "title": "Synergistic hERG (KCNH2) Potassium Channel Blockade",
            "primary_mechanism": "Dual pore blockade of the rapid delayed rectifier potassium current (IKr).",
            "biochemical_steps": [
                "1. Both Azithromycin and Ondansetron bind to aromatic Tyr652/Phe656 residues inside the inner cavity of cardiac hERG channels.",
                "2. Outward K+ efflux during Phase 3 of the ventricular action potential is severely retarded.",
                "3. Ventricular action potential duration (APD90) and surface QTc interval (>500 ms) prolong markedly.",
                "4. Reactivation of L-type Ca2+ channels generates early afterdepolarizations (EADs), triggering Torsades de Pointes."
            ],
            "micro_possibilities": ["QTc prolongation > 500 ms", "Early Afterdepolarizations (EADs)", "Polymorphic Ventricular Tachycardia"],
            "affected_receptors": ["Cardiac hERG / Kv11.1 Channel (IKr)", "Ventricular L-Type Ca2+ Channel (Cav1.2)"]
        }
    },
    {
        "pair": ("azithromycin", "domperidone"),
        "severity": "FATAL",
        "effect": "Lethal QTc Prolongation & Ventricular Arrhythmia",
        "conflict_between": "Azithromycin + Domperidone",
        "description": "Additive cardiac hERG potassium channel blockade plus CYP3A4 inhibition of domperidone clearance.",
        "action": "Strictly Contraindicated: Discontinue Domperidone immediately.",
        "evidence_citation": "CredibleMeds / EMA PRAC Warning",
        "biochemistry": {
            "title": "Pharmacokinetic-Pharmacodynamic Dual IKr Repolarization Arrest",
            "primary_mechanism": "High-affinity hERG channel blockade compounded by P-glycoprotein/CYP3A4 interaction.",
            "biochemical_steps": [
                "1. Domperidone exhibits nanomolar affinity for cardiac Kv11.1 (hERG) channels, potently blocking IKr.",
                "2. Azithromycin co-administration inhibits P-gp efflux and adds direct myocardial IKr blockade.",
                "3. Transmural dispersion of repolarization across ventricular M-cells widens dangerously.",
                "4. Phase 2/3 early afterdepolarizations initiate re-entrant Torsades de Pointes and sudden cardiac arrest."
            ],
            "micro_possibilities": ["QTc > 520 ms", "Torsades de Pointes", "Sudden Arrhythmic Death Syndrome"],
            "affected_receptors": ["Kv11.1 (hERG) Potassium Channel", "Hepatic/Intestinal CYP3A4 & P-gp (ABCB1)"]
        }
    },
    {
        "pair": ("clarithromycin", "domperidone"),
        "severity": "FATAL",
        "effect": "Lethal CYP3A4 Inhibition & QTc Prolongation (Torsades de Pointes)",
        "conflict_between": "Clarithromycin + Domperidone",
        "description": "Clarithromycin blocks CYP3A4 clearance of Domperidone (raising levels 3-fold) while both agents block cardiac hERG channels.",
        "action": "Strictly Contraindicated: Stop Domperidone or switch antibiotic immediately.",
        "evidence_citation": "EMA PRAC / CredibleMeds QT List",
        "biochemistry": {
            "title": "3-Fold Domperidone Surge & Synergistic hERG Potassium Blockade",
            "primary_mechanism": "Complete CYP3A4 metabolic arrest combined with dual IKr channel blockade.",
            "biochemical_steps": [
                "1. Clarithromycin blocks hepatic and intestinal CYP3A4, tripling systemic Domperidone concentrations.",
                "2. Both drugs bind intracellular pore sites of cardiac Kv11.1 (hERG) potassium channels.",
                "3. Ventricular Phase 3 repolarization is severely delayed, extending QTc > 520 ms.",
                "4. Early afterdepolarizations trigger polymorphic ventricular tachycardia (Torsades de Pointes)."
            ],
            "micro_possibilities": ["3x Domperidone plasma Cmax", "QTc > 520 ms", "Ventricular fibrillation"],
            "affected_receptors": ["Cardiac Kv11.1 (hERG) Channel", "Hepatic CYP3A4 Isozyme"]
        }
    },
    {
        "pair": ("ciprofloxacin", "azithromycin"),
        "severity": "HIGH",
        "effect": "Additive QTc Prolongation & Arrhythmia Hazard",
        "conflict_between": "Ciprofloxacin + Azithromycin",
        "description": "Concurrent administration of two QTc-prolonging antimicrobials multiplies cardiac repolarization delay.",
        "action": "Monitor ECG or use alternative non-interacting antimicrobial.",
        "evidence_citation": "CredibleMeds / Clinical Pharmacokinetics",
        "biochemistry": {
            "title": "Dual Antimicrobial Cardiac Repolarization Reserve Exhaustion",
            "primary_mechanism": "Additive inhibition of ventricular IKr potassium currents.",
            "biochemical_steps": [
                "1. Ciprofloxacin and Azithromycin simultaneously occupy intracellular pore sites on cardiac hERG channels.",
                "2. Delayed rectifier K+ current (IKr) amplitude drops below the safety threshold of repolarization reserve.",
                "3. Phase 3 repolarization slows, extending the vulnerable period of the ventricular myocardium.",
                "4. Triggered activity from intracellular Ca2+ overload precipitates malignant ventricular tachyarrhythmias."
            ],
            "micro_possibilities": ["Marked QTc prolongation", "T-wave alternans", "Ventricular ectopy / Torsades"],
            "affected_receptors": ["Cardiac Kv11.1 (hERG) Subunit", "Myocardial Na+/Ca2+ Exchanger (NCX1)"]
        }
    },
    {
        "pair": ("clopidogrel", "omeprazole"),
        "severity": "HIGH",
        "effect": "Attenuated Antiplatelet Efficacy (CYP2C19 Competition)",
        "conflict_between": "Clopidogrel + Omeprazole",
        "description": "Omeprazole competitive inhibition prevents bioactivation of Clopidogrel prodrug.",
        "action": "Switch Omeprazole to Pantoprazole.",
        "evidence_citation": "FDA Safety Alert / J Am Coll Cardiol",
        "biochemistry": {
            "title": "CYP2C19 Metabolic Arrest & P2Y12 Thiol-Activating Failure",
            "primary_mechanism": "Competitive inhibition of two-step hepatic CYP2C19 prodrug bioactivation.",
            "biochemical_steps": [
                "1. Clopidogrel is an inactive thienopyridine prodrug requiring hepatic CYP2C19 oxidation to form 2-oxo-clopidogrel.",
                "2. Omeprazole avidly binds and inhibits CYP2C19, shunting >85% of Clopidogrel to inactive carboxylic acid derivatives via CES1.",
                "3. Generation of the reactive active thiol metabolite (H4) drops by 40-50%.",
                "4. Platelet P2Y12 ADP receptors remain unblocked (no Cys97 disulfide bridge), preserving ADP-induced GPIIb/IIIa aggregation and stent thrombosis risk."
            ],
            "micro_possibilities": ["High On-Treatment Platelet Reactivity (HTPR)", "Uninhibited ADP-induced aggregation", "Acute coronary stent thrombosis"],
            "affected_receptors": ["Hepatic CYP2C19 Isozyme", "Platelet P2Y12 Purinergic Receptor", "Integrin GPIIb/IIIa (alpha-IIb/beta-3)"]
        }
    },
    {
        "pair": ("amoxicillin", "allopurinol"),
        "severity": "MODERATE",
        "effect": "Increased Incidence of Cutaneous Hypersensitivity Rash",
        "conflict_between": "Amoxicillin + Allopurinol",
        "description": "Concurrent use significantly heightens skin rash frequency.",
        "action": "Monitor patient for erythematous skin eruptions.",
        "evidence_citation": "Clinical Pharmacology Database",
        "biochemistry": {
            "title": "Hapten-Mediated T-Cell Cutaneous Delayed Hypersensitivity",
            "primary_mechanism": "Hyperuricemic/allopurinol-potentiated aminopenicillin hapten presentation.",
            "biochemical_steps": [
                "1. Amoxicillin beta-lactam ring opens to form penicilloyl hapten-protein conjugates on epidermal keratinocytes.",
                "2. Allopurinol and oxypurinol alter purine metabolism and lower the activation threshold of cutaneous antigen-presenting cells.",
                "3. CD4+ and CD8+ T-lymphocytes recognize MHC-presented penicilloyl peptides.",
                "4. Cytokine release (IFN-gamma, TNF-alpha) and perforin/granzyme exocytosis produce maculopapular exanthema."
            ],
            "micro_possibilities": ["Maculopapular erythematous exanthem", "Perivascular lymphocytic infiltrate", "Eosinophilia"],
            "affected_receptors": ["HLA Class I/II Antigen Complex", "T-Cell Receptor (TCR)", "Keratinocyte Fas/FasL"]
        }
    }
]

CLINICAL_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "combiflam_pediatric": {
        "triggered_by": "Combiflam (Ibuprofen + Paracetamol) in Young Child",
        "clinical_problem": "Fixed-dose combination adult formulations present high risk of inadvertent double-dosing and organ toxicity in pediatric care.",
        "options": [
            {"salt": "Paracetamol Syrup", "brands": ["Calpol 250 mg/5ml", "Dolo Suspension"], "rationale": "Single-agent weight-based antipyretic is safer for young children."}
        ]
    },
    "claribid_statin_ccb_pediatric": {
        "triggered_by": "CYP3A4 Inhibitor (Clarithromycin) + Statin / CCB Collision",
        "clinical_problem": "Clarithromycin blocks CYP3A4 clearance of Statins (causing Rhabdomyolysis) and Calcium Channel Blockers (causing severe Hypotension & AKI).",
        "options": [
            {"salt": "Azithromycin (10 mg/kg/day)", "brands": ["Azithral Liquid 200mg/5ml", "Zithromax"], "rationale": "Does not inhibit CYP3A4; eliminates Rhabdomyolysis and CCB hypotension interaction."},
            {"salt": "Amlodipine (Pediatric Titrated)", "brands": ["Stamlo 2.5mg"], "rationale": "Preferred over Cilnidipine if pediatric CCB therapy is clinically indicated."}
        ]
    }
}

def split_fdc_salts(raw_salt: str) -> List[str]:
    parts = re.split(r"\s*(?:\+|\/|&|\bwith\b)\s*", raw_salt, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


# --------------------------------------------------------------------------
# CONTEXT-AWARE CLARIFICATION GATE (Prevents Alert Fatigue!)
# --------------------------------------------------------------------------
def get_triggered_clarifications_only(
    salt: str,
    atc_cls: str,
    base_effects: List[str],
    base_prophylaxis: str,
    is_salt_triggered: bool,
    patient_age: int,
    patient: Dict[str, Any],
    ddi_involved_salts: Set[str]
) -> Tuple[List[str], str]:
    """
    ANTI-ALERT-FATIGUE GATE:
    - If `is_salt_triggered` is False (right age, normal organs, no DDI/duplication),
      returns ONLY the clean, calm baseline side_effects and prophylaxis.
    - If `is_salt_triggered` is True, appends ONLY the specific clarifications relevant
      to the active trigger (e.g. DDI, Pediatric age, or the specific toggled organ).
    """
    effects = list(base_effects) if base_effects else ["Well tolerated at standard therapeutic dosing"]
    if not is_salt_triggered:
        return effects, base_prophylaxis

    s = salt.lower().strip()
    cls_low = atc_cls.lower()
    triggered_notes = []

    has_renal = bool(patient.get("has_renal_disease", False))
    has_liver = bool(patient.get("has_liver_disease", False))
    has_cardiac = bool(patient.get("has_cardiac_disease", False))
    has_pud = bool(patient.get("has_pud_disease", False))
    has_asthma = bool(patient.get("has_asthma", False))
    is_pregnant = bool(patient.get("is_pregnant", False))
    in_ddi = s in ddi_involved_salts

    # 1. DDI-Triggered Clarifications
    if in_ddi:
        if "statin" in s or "statin" in cls_low:
            triggered_notes.append("Active DDI Hazard: CYP3A4/OATP1B1 blockade multiplies statin exposure -> Rhabdomyolysis & Myoglobinuric AKI risk")
        elif any(k in s for k in ["dipine", "cilnidipine", "amlodipine"]):
            triggered_notes.append("Active DDI Hazard: Impaired CYP3A4 clearance -> Profound vasodilatory hypotension, syncope & renal hypoperfusion")
        elif "clarithromycin" in s:
            triggered_notes.append("Active DDI Culprit: Potent CYP3A4 & OATP1B1 inhibitor blocking clearance of co-prescribed Statin/CCB")
        elif any(k in s for k in ["fenac", "profen", "aceclo"]) or "nsaid" in cls_low:
            triggered_notes.append("Active DDI/Duplication Hazard: Synergistic prostaglandin ablation -> GI hemorrhage & 'Double Whammy' glomerular collapse")
        else:
            triggered_notes.append("Active Pharmacokinetic/Pharmacodynamic Collision detected with co-prescribed medication")

    # 2. Age-Triggered Clarifications
    if patient_age < 18:
        if "statin" in s:
            triggered_notes.append(f"Pediatric Trigger ({patient_age} Yrs): De novo cholesterol inhibition interferes with steroidogenesis & myelination unless confirmed HeFH")
        elif "cilnidipine" in s:
            triggered_notes.append(f"Pediatric Trigger ({patient_age} Yrs): Dual L/N-type Ca2+ blockade blunts reflex tachycardia -> Uncompensated pediatric hypotension")
        elif any(k in s for k in ["aceclo", "diclofenac", "nimesulide", "aspirin"]):
            triggered_notes.append(f"Pediatric Trigger ({patient_age} Yrs): High risk of pediatric hepatotoxicity, Reye's syndrome, or mucosal ulceration")

    # 3. Organ Comorbidity-Triggered Clarifications (Only for toggled organs!)
    if has_renal:
        triggered_notes.append(f"Renal Trigger (eGFR {patient.get('egfr_value', 90)} mL/min): Impaired glomerular clearance or afferent vasoconstriction hazard")
    if has_liver:
        triggered_notes.append("Hepatic Trigger: Reduced first-pass biotransformation & elevated hepatotoxicity / transaminitis risk")
    if has_cardiac:
        triggered_notes.append("Cardiac Trigger: Risk of QTc prolongation (hERG blockade) or prothrombotic fluid retention")
    if has_pud:
        triggered_notes.append("GI Ulcer Trigger: COX-1 mucosal prostaglandin depletion -> High risk of peptic hemorrhage/perforation")
    if has_asthma:
        triggered_notes.append("Asthma Trigger: Arachidonic acid 5-LOX leukotriene shunting or beta-2 blockade -> Acute bronchospasm")
    if is_pregnant:
        triggered_notes.append(f"Pregnancy Trigger (Trimester {patient.get('pregnancy_trimester', 1)}): Transplacental teratogenic or ductus arteriosus closure hazard")

    for note in triggered_notes:
        if note not in effects:
            effects.append(note)

    return effects, base_prophylaxis


# --------------------------------------------------------------------------
# HELPER: DEFAULT BIOCHEMISTRY GENERATOR FOR INHERITED ATC ALERTS
# --------------------------------------------------------------------------
def attach_default_biochemistry(alert: Dict[str, Any], salt: str) -> Dict[str, Any]:
    if alert.get("biochemistry"):
        return alert

    eff = str(alert.get("effect", "")).lower()
    s_title = salt.title()

    if "renal" in eff or "nephro" in eff or "kidney" in eff:
        alert["biochemistry"] = {
            "title": f"{s_title}-Induced Renal Hemodynamic & Tubular Stress",
            "primary_mechanism": "Impaired glomerular autoregulation and reduced tubular clearance.",
            "biochemical_steps": [
                f"1. {s_title} alters intrarenal prostaglandin synthesis or accumulates in reduced GFR states.",
                "2. Afferent arteriolar tone increases, reducing cortical and medullary blood flow.",
                "3. Glomerular capillary hydrostatic pressure drops while tubular epithelial cells experience ischemic stress.",
                "4. Serum creatinine and nitrogenous waste products accumulate systemically."
            ],
            "micro_possibilities": ["Declining eGFR", "Tubular epithelial vacuolization", "Azotemia & fluid overload"],
            "affected_receptors": ["Renal COX-1/2", "Glomerular Arteriolar Receptors", "Proximal Organic Anion Transporters (OAT1/3)"]
        }
    elif "ulcer" in eff or "gastro" in eff or "bleed" in eff or "pud" in eff:
        alert["biochemistry"] = {
            "title": f"{s_title}-Mediated Gastric Mucosal Barrier Breakdown",
            "primary_mechanism": "Depletion of gastroprotective PGE2 and direct epithelial acid injury.",
            "biochemical_steps": [
                f"1. {s_title} inhibits gastric mucosal cyclooxygenase or directly irritates surface foveolar cells.",
                "2. Mucus and bicarbonate secretion drop while mucosal microcirculation constricts.",
                "3. Luminal HCl and pepsin penetrate the lamina propria, eroding submucosal capillaries.",
                "4. Ulceration, hemorrhage, and potential transmural perforation ensue."
            ],
            "micro_possibilities": ["Mucosal PGE2 depletion", "Submucosal capillary erosion", "Upper GI hemorrhage"],
            "affected_receptors": ["Gastric Epithelial COX-1", "EP3 Prostaglandin Receptor", "Parietal H+/K+ ATPase"]
        }
    elif "pregnan" in eff or "fetal" in eff or "terato" in eff or "ductus" in eff:
        alert["biochemistry"] = {
            "title": f"Transplacental {s_title} Transfer & Embryo-Fetal Signaling Disruption",
            "primary_mechanism": "Placental transfer altering fetal vascular, renal, or morphogenetic pathways.",
            "biochemical_steps": [
                f"1. Unbound maternal {s_title} crosses the syncytiotrophoblast placental barrier into fetal circulation.",
                "2. Drug molecules bind fetal target enzymes/receptors (e.g., ductal COX or fetal renal AT1 receptors).",
                "3. Fetal renal perfusion drops (oligohydramnios) or ductus arteriosus smooth muscle constricts prematurely.",
                "4. Structural teratogenicity, fetal hypoxia, or persistent pulmonary hypertension develops."
            ],
            "micro_possibilities": ["Oligohydramnios", "Premature ductal constriction", "Fetal renal tubular dysgenesis"],
            "affected_receptors": ["Fetal Ductal EP4 Receptor", "Fetal Renal AT1 Receptor", "Placental Efflux Transporters"]
        }
    elif "liver" in eff or "hepat" in eff:
        alert["biochemistry"] = {
            "title": f"{s_title} Hepatic Biotransformation Overload & Hepatocellular Stress",
            "primary_mechanism": "Impaired Phase I/II hepatic clearance and reactive metabolite accumulation.",
            "biochemical_steps": [
                f"1. Compromised hepatocytes exhibit reduced CYP450 and glucuronidation capacity for {s_title}.",
                "2. Reactive intermediates and unmetabolized parent drug accumulate within the space of Disse.",
                "3. Mitochondrial beta-oxidation and bile salt export pump (BSEP) transport are inhibited.",
                "4. Hepatocyte membrane blebbing releases ALT/AST and worsens cholestasis or encephalopathy."
            ],
            "micro_possibilities": ["Elevated serum transaminases (ALT/AST)", "Intrahepatic cholestasis", "Systemic drug accumulation"],
            "affected_receptors": ["Hepatic CYP450 Isozymes", "Bile Salt Export Pump (ABCB11)", "Hepatocyte Mitochondrial Complex"]
        }
    else:
        alert["biochemistry"] = {
            "title": f"{s_title} Systemic Pharmacokinetic & Receptor Interaction",
            "primary_mechanism": "Altered receptor sensitivity and organ-specific clearance dynamics.",
            "biochemical_steps": [
                f"1. Systemic absorption of {s_title} reaches vulnerable target tissues.",
                "2. Underlying patient pathophysiology amplifies primary receptor or enzyme binding.",
                "3. Compensatory homeostatic pathways are overwhelmed by sustained drug concentrations.",
                "4. Clinical adverse toxicities manifest in the compromised organ system."
            ],
            "micro_possibilities": ["Amplified target receptor occupancy", "Delayed systemic clearance", "End-organ functional strain"],
            "affected_receptors": ["Primary Therapeutic Target Receptor", "Hepatic/Renal Clearance Transporters"]
        }
    return alert


# --------------------------------------------------------------------------
# UNIVERSAL FALLBACK ENGINE (Equipped with 4-Step Cellular Biochemistry)
# --------------------------------------------------------------------------
def build_dynamic_fallback_profile(salt: str, patient_age: int, patient: Dict[str, Any], route: str = "oral") -> Dict[str, Any]:
    s = salt.lower().strip()
    inherited_alerts = []
    
    egfr = float(patient.get("egfr_value", 90.0))
    has_renal = bool(patient.get("has_renal_disease", False))
    is_pregnant = bool(patient.get("is_pregnant", False))
    trimester = int(patient.get("pregnancy_trimester", 1)) if is_pregnant else 0

    if any(k in s for k in ["fenac", "profen", "oxicam", "coxib", "naproxen", "ketorolac", "mefenamic", "etodolac", "indomethacin", "aceclo"]):
        atc_cls = "NSAID (Cyclooxygenase Inhibitor / Anti-Inflammatory)"
        base_score = 25
        side_effects = ["Mild dyspepsia", "Epigastric discomfort"]
        prophylaxis = "Administer after meals."
        
        if has_renal:
            inherited_alerts.append({
                "severity": "HIGH" if egfr >= 30 else "FATAL",
                "effect": "Nephrotoxicity & Acute Renal Hemodynamic Injury",
                "conflict_between": f"{salt.title()} + Renal Impairment (eGFR: {egfr} mL/min)",
                "description": "Inhibition of renal vasodilatory prostaglandins precipitates acute kidney injury.",
                "action": "Contraindicated in renal compromise. Substitute with Paracetamol.",
                "evidence_citation": "KDIGO Clinical Practice Guideline for AKI",
                "biochemistry": {
                    "title": "COX-Mediated Afferent Arteriolar Vasoconstriction & Glomerular Ischemia",
                    "primary_mechanism": "Blockade of renal cortical PGE2 and prostacyclin (PGI2) synthesis.",
                    "biochemical_steps": [
                        f"1. {salt.title()} inhibits renal cyclooxygenase (COX-1 and COX-2) in the macula densa and glomerulus.",
                        "2. Local synthesis of vasodilatory prostaglandins PGE2 and PGI2 drops precipitously.",
                        "3. Unopposed angiotensin-II and endothelin-1 constrict the pre-glomerular afferent arteriole.",
                        "4. Glomerular capillary hydrostatic pressure collapses, causing acute tubular ischemia and GFR decline."
                    ],
                    "micro_possibilities": ["Afferent arteriolar spasm", "Acute tubular necrosis (ATN)", "Hyperkalemia & metabolic acidosis"],
                    "affected_receptors": ["Renal COX-1 / COX-2", "Vascular EP2 / EP4 & IP Prostaglandin Receptors"]
                }
            })
        if patient.get("has_pud_disease"):
            inherited_alerts.append({
                "severity": "HIGH",
                "effect": "Peptic Ulcer Hemorrhage & Perforation Hazard",
                "conflict_between": f"{salt.title()} + Peptic Ulcer Disease",
                "description": "Depletes gastroprotective prostaglandins, exposing ulcer base to acid-peptic digestion.",
                "action": "Avoid NSAID or mandate concurrent high-dose PPI.",
                "evidence_citation": "ACG Peptic Ulcer Guideline",
                "biochemistry": {
                    "title": "COX-1 Mucosal Prostaglandin Depletion & Acid-Peptic Ulceration",
                    "primary_mechanism": "Dual topical ion-trapping injury and systemic PGE2/PGI2 suppression.",
                    "biochemical_steps": [
                        f"1. Weakly acidic {salt.title()} remains non-ionized in gastric juice (pH 1.5), diffusing across lipid membranes into foveolar cells.",
                        "2. Neutral intracellular pH (7.4) ionizes and traps the drug, uncoupling mitochondrial oxidative phosphorylation.",
                        "3. Systemic COX-1 inhibition halts PGE2 synthesis, stripping the mucus-bicarbonate barrier and reducing mucosal blood flow.",
                        "4. Luminal HCl and pepsin digest exposed submucosal capillaries, triggering ulcer hemorrhage."
                    ],
                    "micro_possibilities": ["Epithelial ion-trapping necrosis", "Mucosal bicarbonate depletion", "Submucosal arterial erosion"],
                    "affected_receptors": ["Gastric COX-1 Isozyme", "Mucosal EP1/EP3 Prostaglandin Receptors"]
                }
            })
        if patient.get("has_cardiac_disease"):
            inherited_alerts.append({
                "severity": "HIGH",
                "effect": "Cardiovascular Thrombotic & Fluid Retention Hazard",
                "conflict_between": f"{salt.title()} + Cardiac Disease",
                "description": "NSAIDs promote sodium retention and increase vascular atherothrombotic risk.",
                "action": "Avoid systemic NSAIDs in ischemic heart disease or heart failure.",
                "evidence_citation": "AHA / ESC Cardiovascular Safety Guidelines",
                "biochemistry": {
                    "title": "Endothelial Prostacyclin-Thromboxane Imbalance & Atherothrombosis",
                    "primary_mechanism": "Selective endothelial COX-2 suppression without platelet COX-1 inhibition.",
                    "biochemical_steps": [
                        f"1. {salt.title()} inhibits vascular endothelial COX-2, depleting antithrombotic prostacyclin (PGI2).",
                        "2. Platelet COX-1 remains active, continuing unchecked production of prothrombotic Thromboxane A2 (TXA2).",
                        "3. Unopposed TXA2 drives platelet aggregation and coronary vasoconstriction.",
                        "4. Concurrent renal sodium/water retention expands preload, worsening myocardial wall stress."
                    ],
                    "micro_possibilities": ["Depressed PGI2 / TXA2 ratio", "Shear-induced platelet aggregation", "Coronary plaque thrombosis"],
                    "affected_receptors": ["Endothelial COX-2", "Platelet TP (Thromboxane) Receptor", "Vascular IP Receptor"]
                }
            })
        if patient.get("has_liver_disease"):
            inherited_alerts.append({
                "severity": "HIGH",
                "effect": "Hepatotoxicity & Hepatorenal Decompensation Risk",
                "conflict_between": f"{salt.title()} + Liver Disease",
                "description": "Impaired hepatic clearance and prostaglandin inhibition increase risk of variceal bleed and hepatorenal syndrome.",
                "action": "Avoid in moderate-to-severe hepatic impairment.",
                "evidence_citation": "EASL Cirrhosis Clinical Practice Guidelines",
                "biochemistry": {
                    "title": "Acyl-Glucuronide Protein Adduct Formation & Hepatorenal Cascade",
                    "primary_mechanism": "Reactive CYP2C9/UGT metabolite binding and splanchnic-renal vasoconstriction.",
                    "biochemical_steps": [
                        f"1. {salt.title()} undergoes hepatic CYP2C9 oxidation and UGT2B7 glucuronidation into reactive acyl-glucuronides.",
                        "2. Covalent binding to canalicular proteins induces oxidative hepatocyte stress and transaminitis.",
                        "3. In cirrhotic portal hypertension, COX inhibition removes renal compensatory prostaglandins.",
                        "4. Intense renal cortical vasoconstriction precipitates Type-1 Hepatorenal Syndrome and variceal bleeding."
                    ],
                    "micro_possibilities": ["Covalent hepatocyte protein adducts", "Hepatorenal vasoconstriction", "Portal hypertensive hemorrhage"],
                    "affected_receptors": ["Hepatic CYP2C9 & UGT2B7", "Canalicular MRP2 Transporter"]
                }
            })
        if patient.get("has_asthma"):
            inherited_alerts.append({
                "severity": "MODERATE",
                "effect": "NSAID-Exacerbated Respiratory Disease (Bronchospasm)",
                "conflict_between": f"{salt.title()} + Bronchial Asthma",
                "description": "COX inhibition shunts arachidonic acid to bronchoconstrictive leukotrienes.",
                "action": "Monitor respiratory status closely; avoid if aspirin/NSAID-sensitive.",
                "evidence_citation": "GINA Asthma Guidelines",
                "biochemistry": {
                    "title": "Arachidonic Acid 5-Lipoxygenase (5-LOX) Leukotriene Shunt",
                    "primary_mechanism": "Diversion of arachidonic acid substrate into cysteinyl leukotriene synthesis.",
                    "biochemical_steps": [
                        f"1. {salt.title()} blocks the cyclooxygenase pathway, halting bronchodilatory PGE2 synthesis.",
                        "2. Unmetabolized arachidonic acid is shunted into the 5-lipoxygenase (5-LOX) pathway in mast cells and eosinophils.",
                        "3. Overproduction of cysteinyl leukotrienes (LTC4, LTD4, LTE4) surges in bronchial mucosa.",
                        "4. Activation of airway CysLT1 receptors triggers intense bronchoconstriction, mucus hypersecretion, and airway edema."
                    ],
                    "micro_possibilities": ["Massive LTC4/LTD4 surge", "Loss of PGE2 mast-cell stabilization", "Acute bronchial smooth muscle spasm"],
                    "affected_receptors": ["Bronchial CysLT1 Receptor", "Airway Epithelial COX-1", "5-Lipoxygenase (ALOX5)"]
                }
            })
        if is_pregnant and trimester >= 3:
            inherited_alerts.append({
                "severity": "FATAL",
                "effect": "Premature Closure of Fetal Ductus Arteriosus",
                "conflict_between": f"{salt.title()} + Pregnancy (Trimester {trimester})",
                "description": "Late-pregnancy prostaglandin inhibition constricts the fetal ductus arteriosus and causes oligohydramnios.",
                "action": "Strictly Contraindicated in 3rd Trimester.",
                "evidence_citation": "FDA / ACOG Obstetric Safety Advisory",
                "biochemistry": {
                    "title": "Fetal Ductal EP4 Receptor Deprivation & Ductus Arteriosus Constriction",
                    "primary_mechanism": "Transplacental COX inhibition abolishing PGE2-maintained ductal patency.",
                    "biochemical_steps": [
                        f"1. {salt.title()} crosses the placenta and inhibits fetal cyclooxygenase-1 and -2.",
                        "2. Circulating fetal PGE2 drops, depriving ductal smooth muscle EP4 receptors of cAMP/PKA vasodilatory signaling.",
                        "3. Unopposed myosin light-chain kinase activation contracts the fetal ductus arteriosus in utero.",
                        "4. Fetal right ventricular afterload spikes (causing PPHN) while fetal renal hypoperfusion causes oligohydramnios."
                    ],
                    "micro_possibilities": ["In-utero ductus arteriosus closure", "Persistent Pulmonary Hypertension of Newborn (PPHN)", "Fetal oligohydramnios"],
                    "affected_receptors": ["Fetal Ductal EP4 Prostaglandin Receptor", "Fetal Renal COX-2"]
                }
            })

    elif any(k in s for k in ["sartan", "pril"]):
        atc_cls = "RAAS Inhibitor (ARB / ACE Inhibitor Antihypertensive)"
        base_score = 20
        side_effects = ["Mild dizziness", "Orthostatic lightheadedness"]
        prophylaxis = "Monitor blood pressure and electrolytes periodically."
        if is_pregnant:
            inherited_alerts.append({
                "severity": "FATAL",
                "effect": "Fetal Renal Dysplasia & Teratogenicity (Black Box Warning)",
                "conflict_between": f"{salt.title()} + Pregnancy",
                "description": "RAAS blockade disrupts fetal renal development and causes severe oligohydramnios.",
                "action": "Discontinue immediately; switch to Labetalol or Nifedipine.",
                "evidence_citation": "FDA Boxed Warning",
                "biochemistry": {
                    "title": "Fetal Nephrogenesis Arrest & Potter Sequence Teratogenicity",
                    "primary_mechanism": "Transplacental blockade of fetal angiotensin-II AT1 receptor signaling.",
                    "biochemical_steps": [
                        f"1. {salt.title()} crosses the placental barrier and blocks fetal AT1 receptors (or ACE) during nephrogenesis.",
                        "2. Fetal glomerular filtration pressure collapses due to loss of efferent arteriolar tone.",
                        "3. Fetal urine production ceases (anuria), resulting in severe anhydramnios/oligohydramnios.",
                        "4. Loss of amniotic fluid cushion causes fetal pulmonary hypoplasia, limb contractures, and calvarial hypoplasia."
                    ],
                    "micro_possibilities": ["Fetal renal tubular dysgenesis", "Severe oligohydramnios", "Calvarial & pulmonary hypoplasia (Potter syndrome)"],
                    "affected_receptors": ["Fetal Glomerular AT1 Receptor", "Ureteric Bud GDNF/RET Signaling"]
                }
            })

    elif any(k in s for k in ["dipine", "olol", "thiazide", "chlorthalidone", "furosemide", "torsemide", "spironolactone", "cilnidipine"]):
        atc_cls = "Cardiovascular & Antihypertensive Agent"
        base_score = 20
        side_effects = ["Mild postural dizziness", "Flushing"]
        prophylaxis = "Monitor blood pressure and heart rate."
        if "olol" in s and patient.get("has_asthma"):
            inherited_alerts.append({
                "severity": "HIGH",
                "effect": "Beta-Blocker Induced Bronchospasm",
                "conflict_between": f"{salt.title()} + Bronchial Asthma",
                "description": "Blockade of bronchial beta-2 receptors precipitates acute bronchoconstriction.",
                "action": "Avoid non-selective beta-blockers in asthmatic patients.",
                "evidence_citation": "GINA Asthma Guidelines",
                "biochemistry": {
                    "title": "Bronchial Beta-2 Adrenoceptor Antagonism & cAMP Depletion",
                    "primary_mechanism": "Competitive blockade of Gs-coupled bronchial smooth muscle beta-2 receptors.",
                    "biochemical_steps": [
                        f"1. {salt.title()} binds bronchial smooth muscle beta-2 adrenergic receptors.",
                        "2. Gs-protein activation of adenylyl cyclase is inhibited, causing intracellular cAMP levels to fall.",
                        "3. Reduced Protein Kinase A (PKA) activity permits unopposed myosin light-chain kinase (MLCK) phosphorylation.",
                        "4. Vagal M3 muscarinic tone dominates, causing severe bronchoconstriction and blunting rescue salbutamol efficacy."
                    ],
                    "micro_possibilities": ["Intracellular cAMP depletion", "Refractory bronchospasm", "Antagonism of SABA rescue inhalers"],
                    "affected_receptors": ["Bronchial Beta-2 Adrenoceptor (ADRB2)", "Adenylyl Cyclase / PKA Pathway"]
                }
            })

    elif any(k in s for k in ["cillin", "cef", "mycin", "floxacin", "cycline", "azole", "penem", "linezolid", "ofi", "nitrofurantoin"]):
        atc_cls = "Systemic Antimicrobial / Anti-Infective"
        base_score = 20
        side_effects = ["Mild gastrointestinal upset", "Nausea"]
        prophylaxis = "Complete full prescribed antimicrobial course."
        if has_renal and egfr < 45:
            inherited_alerts.append({
                "severity": "MODERATE",
                "effect": "Impaired Renal Antimicrobial Clearance",
                "conflict_between": f"{salt.title()} + Reduced eGFR ({egfr} mL/min)",
                "description": "Decreased glomerular filtration delays elimination of renally cleared antimicrobials.",
                "action": "Adjust dose or dosing interval according to eGFR.",
                "evidence_citation": "Sanford Guide to Antimicrobial Therapy",
                "biochemistry": {
                    "title": "Tubular OAT1/OAT3 Secretion Saturation & Systemic Accumulation",
                    "primary_mechanism": "Reduced glomerular filtration and basolateral organic anion transport in CKD.",
                    "biochemical_steps": [
                        f"1. Reduced functional nephron mass (eGFR {egfr} mL/min) decreases filtration of unbound {salt.title()}.",
                        "2. Proximal tubular OAT1/OAT3 secretion is saturated by uremic toxins.",
                        "3. Elimination half-life doubles or triples, driving peak and trough plasma concentrations into toxic ranges.",
                        "4. Excess drug crosses the blood-brain barrier (GABA-A antagonism) or precipitates intratubular crystalluria."
                    ],
                    "micro_possibilities": ["Prolonged elimination half-life", "Intratubular crystal precipitation", "CNS neurotoxicity / lowered seizure threshold"],
                    "affected_receptors": ["Renal Basolateral OAT1/OAT3 (SLC22A6/8)", "Central GABA-A Receptor"]
                }
            })

    elif any(k in s for k in ["gliptin", "flozin", "piride", "gliclazide", "voglibose", "pioglitazone", "insulin"]):
        atc_cls = "Antihyperglycemic / Antidiabetic Agent"
        base_score = 20
        side_effects = ["Monitor for hypoglycemia", "Mild GI fullness"]
        prophylaxis = "Administer as directed with meals."
        if "piride" in s and patient.get("has_g6pd_deficiency"):
            inherited_alerts.append({
                "severity": "HIGH",
                "effect": "Sulfonylurea-Induced Hemolytic Anemia",
                "conflict_between": f"{salt.title()} + G6PD Deficiency",
                "description": "Sulfonylureas induce oxidative stress in G6PD-deficient erythrocytes.",
                "action": "Prefer DPP-4 inhibitors over sulfonylureas in G6PD deficiency.",
                "evidence_citation": "Pharmacogenetics & Clinical Hematology",
                "biochemistry": {
                    "title": "Pentose Phosphate Shunt Failure & Heinz Body Erythrocyte Lysis",
                    "primary_mechanism": "NADPH depletion unable to neutralize sulfonylurea-induced oxidative radicals.",
                    "biochemical_steps": [
                        f"1. {salt.title()} metabolites generate reactive oxygen species (ROS) and hydrogen peroxide inside erythrocytes.",
                        "2. G6PD-deficient red blood cells cannot regenerate NADPH via the hexose monophosphate shunt.",
                        "3. Reduced glutathione (GSH) is exhausted, allowing oxidation of hemoglobin sulfhydryl groups into insoluble Heinz bodies.",
                        "4. Splenic macrophages bite out Heinz bodies and rigid erythrocyte membranes rupture intravascularly."
                    ],
                    "micro_possibilities": ["Heinz body inclusions", "Bite cells & hemoglobinuria", "Acute hemolytic anemia"],
                    "affected_receptors": ["Erythrocyte G6PD Enzyme", "Glutathione Peroxidase (GPX1)", "Hemoglobin Beta-93 Cysteine"]
                }
            })

    elif any(k in s for k in ["prazole", "tidine", "levosulpiride", "itopride", "ondansetron", "sucralfate"]):
        atc_cls = "Gastrointestinal Acid Suppressant / Prokinetic"
        base_score = 12
        side_effects = ["Mild headache", "Well tolerated"]
        prophylaxis = "Administer 30 minutes prior to meals."

    elif any(k in s for k in ["cetirizine", "levocetirizine", "fexofenadine", "montelukast", "loratadine", "chlorpheniramine"]):
        atc_cls = "Antihistamine / Leukotriene Receptor Antagonist (Anti-Allergic)"
        base_score = 12
        side_effects = ["Mild drowsiness", "Dry mouth"]
        prophylaxis = "Administer in the evening if sedation occurs."

    elif any(k in s for k in ["prednisolone", "deflazacort", "dexamethasone", "betamethasone", "budesonide"]):
        atc_cls = "Corticosteroid (Glucocorticoid Anti-Inflammatory)"
        base_score = 28
        side_effects = ["Increased appetite", "Mild fluid retention", "Gastric irritation"]
        prophylaxis = "Administer after breakfast."
        if patient.get("has_diabetes"):
            inherited_alerts.append({
                "severity": "HIGH",
                "effect": "Glucocorticoid-Induced Severe Hyperglycemia",
                "conflict_between": f"{salt.title()} + Diabetes Mellitus",
                "description": "Corticosteroids stimulate hepatic gluconeogenesis and antagonize peripheral insulin action.",
                "action": "Monitor blood glucose closely and titrate antidiabetic therapy.",
                "evidence_citation": "Endocrine Society Clinical Practice Guideline",
                "biochemistry": {
                    "title": "GR-Mediated PEPCK Upregulation & GLUT4 Translocation Blockade",
                    "primary_mechanism": "Genomic induction of hepatic gluconeogenesis and peripheral insulin resistance.",
                    "biochemical_steps": [
                        f"1. {salt.title()} binds cytosolic Glucocorticoid Receptors (NR3C1), translocating to the nucleus to bind GREs.",
                        "2. Transcription of hepatic gluconeogenic rate-limiting enzymes (PEPCK and Glucose-6-Phosphatase) is strongly upregulated.",
                        "3. In skeletal muscle and adipocytes, PI3K/Akt signaling is blunted, preventing GLUT4 vesicle translocation to the cell membrane.",
                        "4. Unchecked hepatic glucose output combined with peripheral insulin resistance triggers severe postprandial hyperglycemia."
                    ],
                    "micro_possibilities": ["Hepatic PEPCK/G6Pase induction", "Impaired skeletal muscle GLUT4 translocation", "Hyperglycemic hyperosmolar state"],
                    "affected_receptors": ["Cytosolic Glucocorticoid Receptor (NR3C1)", "Insulin Receptor Substrate-1 (IRS-1)", "GLUT4 Transporter"]
                }
            })

    else:
        atc_cls = "Active Pharmaceutical Ingredient (Therapeutic Formulation)"
        base_score = 15
        side_effects = ["Mild gastrointestinal intolerance (rare)"]
        prophylaxis = "Standard postprandial administration."

    return {
        "atc_class": atc_cls,
        "coverage_tier": "TIER_1_FULL",
        "is_out_of_scope": False,
        "base_risk_score": base_score,
        "side_effects": side_effects,
        "prophylaxis": prophylaxis,
        "inherited_alerts": inherited_alerts,
        "evidence_citation": "ARPA Universal Pharmacovigilance Knowledge Graph"
    }


def calculate_dynamic_risk(base_score: Optional[int], salt: str, patient_age: int, patient: Dict[str, Any], route: str = "oral") -> Tuple[Optional[int], str]:
    if base_score is None:
        base_score = 15
    if route == "topical":
        return 10, "LOW / TOPICAL"

    score = base_score
    clean_root, atc_class = strip_and_extract_salt(salt)
    atc_class = atc_class or ""
    clean_root = clean_root or salt.lower().strip()

    if not atc_class and any(k in clean_root for k in ["fenac", "profen", "oxicam", "coxib", "aceclo"]):
        atc_class = "NSAID"
    elif not atc_class and any(k in clean_root for k in ["sartan", "pril"]):
        atc_class = "RAAS_INHIBITOR"
    elif not atc_class and any(k in clean_root for k in ["statin"]):
        atc_class = "STATIN"
    elif not atc_class and any(k in clean_root for k in ["dipine", "cilnidipine", "amlodipine"]):
        atc_class = "CCB"

    # Dynamic pediatric & adult risk adjustments
    if patient_age < 16 and clean_root == "aspirin": score += 60
    elif patient_age < 12 and clean_root == "nimesulide": score += 45
    elif patient_age < 16 and atc_class == "STATIN": score += 45
    elif patient_age < 18 and clean_root == "cilnidipine": score += 40
    elif patient_age < 18 and clean_root in ["aceclofenac", "diclofenac"]: score += 35
    elif patient_age < 6 and clean_root == "ibuprofen": score += 40
    elif patient_age < 12 and atc_class == "NSAID": score += 35
    elif patient_age < 18 and clean_root == "ciprofloxacin": score += 35
    elif patient_age >= 65 and atc_class == "NSAID": score += 30

    # Comorbidity interactions (Strictly checks explicit toggles!)
    if patient.get("has_pud_disease") and atc_class in ["NSAID", "ANTICOAGULANT", "CORTICOSTEROID"]: score += 50
    if patient.get("is_pregnant") and (atc_class in ["RAAS_INHIBITOR", "STATIN", "ANTIEPILEPTIC"] or clean_root == "sodium valproate"): score += 65
    if patient.get("has_renal_disease") and atc_class in ["NSAID", "DIURETIC", "AMINOGLYCOSIDE"]: score += 45
    if patient.get("has_liver_disease") and (clean_root in ["nimesulide", "isoniazid", "rifampicin", "diclofenac", "aceclofenac"] or atc_class in ["STATIN", "ANTIEPILEPTIC"]): score += 45
    if patient.get("has_cardiac_disease") and (atc_class in ["MACROLIDE", "FLUOROQUINOLONE", "ANTIEMETIC", "NSAID"]): score += 40

    score = min(100, max(5, score))
    level = "CRITICAL / HIGH" if score >= 85 else "HIGH / ELEVATED" if score >= 65 else "MODERATE / MEDIUM" if score >= 35 else "LOW / MILD"
    return score, level

def evaluate_prescription(prescribed_drugs: List[Dict[str, Any]], patient: Dict[str, Any]) -> Dict[str, Any]:
    alerts = []
    recommendations = []
    out_of_scope_drugs = []
    nti_detected_drugs = []
    surveillance_tiers = set()
    
    # Track which salts are actively involved in ANY clinical hazard (Age, Organ, DDI, or Duplication)
    triggered_salts: Set[str] = set()
    ddi_involved_salts: Set[str] = set()
    
    patient_age = int(patient.get("age", 28))
    is_pediatric = patient_age < 18

    # 1. Expand FDCs and Detect Administration Route
    for d in prescribed_drugs:
        brand_str = d.get("brand", "")
        route = detect_administration_route(brand_str)
        d["route"] = route
        
        expanded_salts = []
        for s in d.get("salts", []):
            expanded_salts.extend(split_fdc_salts(s))
        d["salts"] = expanded_salts

    # Check for Pediatric Fatal & Developmental Rules in Overrides
    for d in prescribed_drugs:
        for s in d.get("salts", []):
            clean_root, _ = strip_and_extract_salt(s)
            lookup_r = clean_root or s.lower().strip()
            if lookup_r in MOLECULE_OVERRIDES:
                prof = MOLECULE_OVERRIDES[lookup_r]
                if "pediatric_fatal_rule" in prof:
                    rule = prof["pediatric_fatal_rule"]
                    if patient_age < rule["max_age"]:
                        triggered_salts.add(lookup_r)
                        alerts.append({
                            "severity": rule["severity"],
                            "effect": rule["effect"],
                            "conflict_between": f"{d.get('brand')} ({lookup_r.title()}) in {patient_age}-year-old pediatric patient",
                            "description": rule["description"],
                            "action": rule["action"],
                            "evidence_citation": prof.get("evidence_citation", "Pediatric Safety Advisory"),
                            "biochemistry": rule.get("biochemistry")
                        })

    # Special Pediatric Guardrail for Combination Products like Combiflam
    if patient_age < 12:
        for d in prescribed_drugs:
            brand_lower = d.get("brand", "").lower()
            salts_low = [s.lower() for s in d.get("salts", [])]
            if "combiflam" in brand_lower or ("ibuprofen" in salts_low and "paracetamol" in salts_low):
                triggered_salts.update(["ibuprofen", "paracetamol"])
                alerts.append({
                    "severity": "HIGH",
                    "effect": "Pediatric Safety Warning: Fixed-Dose Combination in Young Child",
                    "conflict_between": f"{d.get('brand')} (Ibuprofen + Paracetamol) in {patient_age}-year-old child",
                    "description": "Combination adult-oriented painkillers carry high risk of dosage calculation error and renal/hepatic strain in young children.",
                    "action": "Discontinue combination product. Administer single-agent weight-based Paracetamol suspension under pediatric guidance.",
                    "evidence_citation": "AAP / Indian Academy of Pediatrics (IAP) Guidelines",
                    "biochemistry": {
                        "title": "Synergistic Pediatric Renal-Hepatic Clearance Overload",
                        "primary_mechanism": "Concurrent CYP2E1 NAPQI generation and renal PGE2 inhibition in immature organs.",
                        "biochemical_steps": [
                            "1. Fixed-dose tablet ratios prevent independent milligram-per-kilogram titration for Ibuprofen and Paracetamol.",
                            "2. Ibuprofen inhibits renal prostaglandin synthesis, reducing glomerular filtration during febrile dehydration.",
                            "3. Paracetamol saturates immature pediatric glucuronidation (UGT1A6), shunting metabolism to CYP2E1.",
                            "4. Combined renal medullary ischemia and hepatic glutathione depletion elevate multi-organ toxicity risk."
                        ],
                        "micro_possibilities": ["UGT1A6 saturation", "Renal medullary ischemia", "Supratherapeutic plasma accumulation"],
                        "affected_receptors": ["Hepatic UGT1A6 / CYP2E1", "Renal COX-1 / COX-2"]
                    }
                })
                if CLINICAL_RECOMMENDATIONS["combiflam_pediatric"] not in recommendations:
                    recommendations.append(CLINICAL_RECOMMENDATIONS["combiflam_pediatric"])

    # 2. Extract molecules
    all_salts_raw = set()
    all_salts_root = set()
    systemic_root_list: List[str] = []
    systemic_class_list: List[str] = []
    nsaid_salts_in_rx: List[str] = []

    for d in prescribed_drugs:
        route = d.get("route", "oral")
        for s in d.get("salts", []):
            raw = s.lower().strip()
            all_salts_raw.add(raw)
            root, atc_cls = strip_and_extract_salt(raw)
            final_root = root if root else raw
            all_salts_root.add(final_root)
            
            if not atc_cls and any(k in final_root for k in ["fenac", "profen", "oxicam", "coxib", "naproxen", "ketorolac", "mefenamic", "nimesulide", "aceclo"]):
                atc_cls = "NSAID"

            if route != "topical":
                systemic_root_list.append(final_root)
                if atc_cls:
                    systemic_class_list.append(atc_cls)
                if atc_cls == "NSAID":
                    nsaid_salts_in_rx.append(final_root)

    combined_lookup = all_salts_raw.union(all_salts_root)

    # 3. Duplication Checks
    root_counts = Counter(systemic_root_list)
    for molecule, count in root_counts.items():
        if count > 1:
            triggered_salts.add(molecule)
            ddi_involved_salts.add(molecule)
            if molecule == "paracetamol":
                alerts.append({
                    "severity": "FATAL",
                    "effect": "Overdose Hazard: Multi-Source Paracetamol Accumulation",
                    "conflict_between": f"Duplicate Paracetamol ({count}x across systemic brands)",
                    "description": "Cumulative daily intake risks exceeding maximum hepatic saturation thresholds.",
                    "action": "Immediate Action: Retain single paracetamol product; enforce weight-based max dose.",
                    "evidence_citation": "FDA Acetaminophen Advisory / WHO",
                    "biochemistry": {
                        "title": "Phase II Glucuronidation Saturation & NAPQI Centrilobular Necrosis",
                        "primary_mechanism": "Exhaustion of hepatic glutathione (GSH) by reactive NAPQI quinoneimine.",
                        "biochemical_steps": [
                            "1. Supratherapeutic Paracetamol load saturates hepatic Phase II glucuronidation (UGT1A1/1A6) and sulfation (SULT1A1) pathways.",
                            "2. Excess parent drug is shunted into Phase I cytochrome P450 (CYP2E1, CYP1A2, CYP3A4) oxidation.",
                            "3. Massive generation of toxic N-acetyl-p-benzoquinone imine (NAPQI) depletes >70% of intracellular hepatic glutathione (GSH).",
                            "4. Unbound NAPQI covalently arylates mitochondrial sulfhydryl proteins, triggering peroxynitrite stress, ATP collapse, and Zone 3 centrilobular necrosis."
                        ],
                        "micro_possibilities": ["Hepatic GSH depletion (>70%)", "NAPQI mitochondrial protein adducts", "Zone 3 centrilobular hepatocyte lysis"],
                        "affected_receptors": ["Hepatic CYP2E1 Isozyme", "UGT1A6 / SULT1A1 Transferases", "Mitochondrial Glutathione (GSH) Pool"]
                    }
                })
            else:
                alerts.append({
                    "severity": "HIGH",
                    "effect": f"Duplicate Molecule Hazard: {molecule.title()}",
                    "conflict_between": f"Duplicate API ({molecule.title()} prescribed {count} times)",
                    "description": f"Multiple systemic products containing {molecule.title()} double systemic burden.",
                    "action": f"De-prescribe duplicate {molecule.title()} formulation.",
                    "evidence_citation": "Beers Criteria / Clinical Pharmacokinetics",
                    "biochemistry": {
                        "title": f"Supratherapeutic {molecule.title()} Receptor Saturation & Clearance Overload",
                        "primary_mechanism": "Non-linear plasma accumulation beyond the therapeutic window.",
                        "biochemical_steps": [
                            f"1. Concurrent administration of {count} formulations containing {molecule.title()} doubles systemic bioavailability (AUC).",
                            "2. Primary target receptors reach 100% saturation, providing zero additional therapeutic benefit.",
                            "3. Hepatic CYP450 enzymes and renal tubular transporters experience Michaelis-Menten saturation kinetics.",
                            "4. Off-target receptor binding and toxic metabolite accumulation trigger dose-dependent organ toxicity."
                        ],
                        "micro_possibilities": ["2x Plasma Cmax & AUC", "Target receptor ceiling saturation", "Off-target dose-dependent toxicity"],
                        "affected_receptors": [f"Primary {molecule.title()} Target Receptor", "Hepatic/Renal Elimination Transporters"]
                    }
                })

    class_counts = Counter(systemic_class_list)
    if class_counts.get("NSAID", 0) > 1:
        triggered_salts.update(nsaid_salts_in_rx)
        ddi_involved_salts.update(nsaid_salts_in_rx)
        alerts.append({
            "severity": "FATAL",
            "effect": "Therapeutic Duplication: Dual Systemic NSAID Toxicity",
            "conflict_between": f"Concurrent Systemic NSAIDs ({class_counts['NSAID']} NSAIDs prescribed)",
            "description": "Co-prescribing multiple systemic NSAIDs multiplies mucosal perforation and acute renal collapse risk.",
            "action": "Immediate Action: Discontinue all but ONE systemic NSAID.",
            "evidence_citation": "NICE Guidelines / American College of Rheumatology",
            "biochemistry": {
                "title": "Synergistic COX-1/COX-2 Ablation & Mucosal-Renal Collapse",
                "primary_mechanism": "Complete systemic abolition of cytoprotective and vasodilatory prostanoids.",
                "biochemical_steps": [
                    "1. Concurrent NSAIDs competitively and non-competitively occupy both COX-1 and COX-2 catalytic channels.",
                    "2. Gastric mucosal PGE2 and PGI2 synthesis drops to near-zero, abolishing mucus/bicarbonate secretion and epithelial restitution.",
                    "3. Simultaneous direct topical uncoupling of enterocyte mitochondrial phosphorylation causes deep mucosal ulceration.",
                    "4. In the kidney, total blockade of afferent arteriolar vasodilatory prostaglandins precipitates acute ischemic papillary necrosis."
                ],
                "micro_possibilities": ["Complete gastric PGE2 ablation", "Transmucosal gastric perforation", "Acute renal papillary necrosis"],
                "affected_receptors": ["Catalytic Tyr385 / Ser530 of COX-1 & COX-2", "Gastric EP1-EP4 & Renal IP Receptors"]
            }
        })

    # 4. Severe DDI Checks
    seen_alert_effects = set()
    for rule in SEVERE_DDI_RULES:
        d1, d2 = rule["pair"]
        if d1 in combined_lookup and d2 in combined_lookup:
            triggered_salts.update([d1, d2])
            ddi_involved_salts.update([d1, d2])
            dedup_k = f"{rule['severity']}_{rule['effect']}"
            seen_alert_effects.add(dedup_k)
            alerts.append({
                "severity": rule["severity"],
                "effect": rule["effect"],
                "conflict_between": rule["conflict_between"],
                "description": rule["description"],
                "action": rule["action"],
                "evidence_citation": rule.get("evidence_citation", "Clinical Pharmacokinetics"),
                "biochemistry": rule.get("biochemistry")
            })
            if "clarithromycin" in (d1, d2) and CLINICAL_RECOMMENDATIONS["claribid_statin_ccb_pediatric"] not in recommendations:
                recommendations.append(CLINICAL_RECOMMENDATIONS["claribid_statin_ccb_pediatric"])

    # Dynamic Triple CYP3A4 Synergistic Collapse Check
    cyp3a4_inhibitors = [s for s in combined_lookup if any(k in s for k in ["clarithromycin", "erythromycin", "itraconazole", "ketoconazole", "ritonavir"])]
    statins_present = [s for s in combined_lookup if "statin" in s]
    ccbs_present = [s for s in combined_lookup if any(k in s for k in ["dipine", "cilnidipine", "amlodipine", "nifedipine", "felodipine", "diltiazem", "verapamil"])]

    if cyp3a4_inhibitors and statins_present and ccbs_present:
        triggered_salts.update(cyp3a4_inhibitors + statins_present + ccbs_present)
        ddi_involved_salts.update(cyp3a4_inhibitors + statins_present + ccbs_present)
        alerts.append({
            "severity": "FATAL",
            "effect": "Triple CYP3A4 Metabolic Bottleneck: Synergistic Rhabdomyolysis, Vasodilatory Shock & Acute Tubular Necrosis",
            "conflict_between": f"{cyp3a4_inhibitors[0].title()} + {statins_present[0].title()} + {ccbs_present[0].title()}",
            "description": "Co-administration of a potent CYP3A4 inhibitor alongside both a Statin and a Calcium Channel Blocker creates a two-hit renal catastrophe: massive statin-induced myoglobinuria obstructs renal tubules while CCB-induced hypotension collapses renal perfusion pressure.",
            "action": "CRITICAL INTERVENTION: Discontinue Clarithromycin immediately (switch to Azithromycin) and hold Statin/CCB until hemodynamic and CPK parameters are verified.",
            "evidence_citation": "FDA Multi-Drug CYP3A4 Pharmacovigilance / KDIGO AKI Consensus",
            "biochemistry": {
                "title": "Two-Hit Nephrotoxic & Hemodynamic Collapse (Myoglobin Casts + Renal Ischemia)",
                "primary_mechanism": "Complete hepatic/intestinal CYP3A4 arrest driving simultaneous statin myolysis and CCB vasoplegia.",
                "biochemical_steps": [
                    f"1. {cyp3a4_inhibitors[0].title()} irreversibly inactivates CYP3A4 and blocks hepatic OATP1B1, halting clearance of both {statins_present[0].title()} and {ccbs_present[0].title()}.",
                    f"2. Hit 1 (Tubular Obstruction): 5-fold {statins_present[0].title()} surge lyses skeletal muscle fibers, flooding renal tubules with heme-iron myoglobin that precipitates with Tamm-Horsfall protein.",
                    f"3. Hit 2 (Hemodynamic Collapse): 3-fold {ccbs_present[0].title()} surge blocks vascular L/N-type Ca2+ channels, causing profound arterial hypotension and dropping glomerular filtration pressure.",
                    "4. Ischemic, acidotic renal tubules cannot flush out myoglobin casts, resulting in rapid, irreversible Acute Tubular Necrosis (ATN) and hyperkalemic arrest."
                ],
                "micro_possibilities": ["Synergistic Tamm-Horsfall myoglobin cast occlusion", "Uncompensated vasodilatory shock", "Anuric Acute Renal Failure & Hyperkalemia"],
                "affected_receptors": ["Hepatic/Enterocyte CYP3A4 & OATP1B1", "Vascular Cav1.2 / Neuronal Cav2.2", "Renal Proximal Tubule Megalin/Cubilin"]
            }
        })

    # 5. Resolve ATC, Overrides & Apply Anti-Alert-Fatigue Gating
    drug_scores = []

    for drug in prescribed_drugs:
        drug_profiles = []
        route = drug.get("route", "oral")
        
        for salt in drug.get("salts", []):
            clean_root, atc_key = strip_and_extract_salt(salt)
            lookup_key = clean_root or salt.lower().strip()
            
            if lookup_key in MOLECULE_OVERRIDES and "base_risk_score" in MOLECULE_OVERRIDES[lookup_key]:
                prof = MOLECULE_OVERRIDES[lookup_key]
                tier = prof.get("coverage_tier", "TIER_1_FULL")
                surveillance_tiers.add(tier)
                
                extra_data = build_dynamic_fallback_profile(lookup_key, patient_age, patient, route)
                salt_organ_alerts = extra_data.get("inherited_alerts", [])
                for inh_alert in salt_organ_alerts:
                    triggered_salts.add(lookup_key)
                    inh_alert = attach_default_biochemistry(inh_alert, lookup_key)
                    dedup_key = f"{inh_alert['severity']}_{inh_alert['effect']}"
                    if dedup_key not in seen_alert_effects:
                        seen_alert_effects.add(dedup_key)
                        alerts.append(inh_alert)

                # Also check if atc_engine generated any comorbidity alerts for this salt
                atc_check = resolve_atc_inheritance(salt, patient_age, patient, route)
                for inh_alert in atc_check.get("inherited_alerts", []):
                    triggered_salts.add(lookup_key)
                    inh_alert = attach_default_biochemistry(inh_alert, lookup_key)
                    dedup_key = f"{inh_alert['severity']}_{inh_alert['effect']}"
                    if dedup_key not in seen_alert_effects:
                        seen_alert_effects.add(dedup_key)
                        alerts.append(inh_alert)

                dyn_score, dyn_level = calculate_dynamic_risk(prof["base_risk_score"], lookup_key, patient_age, patient, route)
                if lookup_key in ddi_involved_salts:
                    dyn_score = max(dyn_score or 25, 78)
                    dyn_level = "CRITICAL / HIGH" if dyn_score >= 85 else "HIGH / ELEVATED"
                if dyn_score is not None:
                    drug_scores.append(dyn_score)

                is_this_salt_triggered = (lookup_key in triggered_salts) or (dyn_score is not None and dyn_score >= 55)

                gated_effects, gated_prophylaxis = get_triggered_clarifications_only(
                    lookup_key,
                    prof.get("class", "Unclassified"),
                    prof.get("side_effects", []),
                    prof.get("prophylaxis", ""),
                    is_this_salt_triggered,
                    patient_age,
                    patient,
                    ddi_involved_salts
                )

                # ANTI-ALERT-FATIGUE: Only show Black Box Warning when a clinical trigger is active!
                active_black_box = prof.get("black_box_warning") if is_this_salt_triggered else None

                drug_profiles.append({
                    "salt": lookup_key.title(),
                    "class": prof.get("class", "Unclassified"),
                    "coverage_tier": tier,
                    "risk_level": dyn_level,
                    "risk_score": dyn_score,
                    "route": route,
                    "pediatric_safety": prof.get("pediatric_safety") if is_pediatric else None,
                    "pediatric_dosage": prof.get("pediatric_dosage") if is_pediatric else None,
                    "side_effects": gated_effects,
                    "prophylaxis": gated_prophylaxis,
                    "black_box_warning": active_black_box,
                    "evidence_citation": prof.get("evidence_citation")
                })
                continue

            atc_data = resolve_atc_inheritance(salt, patient_age, patient, route)
            
            if atc_data.get("is_out_of_scope") or atc_data.get("coverage_tier") == "TIER_3_UNMAPPED" or atc_data.get("base_risk_score") is None:
                atc_data = build_dynamic_fallback_profile(lookup_key, patient_age, patient, route)

            tier = atc_data.get("coverage_tier", "TIER_1_FULL")
            surveillance_tiers.add(tier)

            for inh_alert in atc_data.get("inherited_alerts", []):
                triggered_salts.add(lookup_key)
                inh_alert = attach_default_biochemistry(inh_alert, lookup_key)
                dedup_key = f"{inh_alert['severity']}_{inh_alert['effect']}"
                if dedup_key not in seen_alert_effects:
                    seen_alert_effects.add(dedup_key)
                    alerts.append(inh_alert)

            base_score = atc_data.get("base_risk_score", 20)
            dyn_score, dyn_level = calculate_dynamic_risk(base_score, salt, patient_age, patient, route)
            if lookup_key in ddi_involved_salts:
                dyn_score = max(dyn_score or 20, 75)
                dyn_level = "HIGH / ELEVATED"
            if dyn_score is not None:
                drug_scores.append(dyn_score)

            is_this_salt_triggered = (lookup_key in triggered_salts) or (dyn_score is not None and dyn_score >= 55)
            atc_cls_str = atc_data.get("atc_class", "Active Pharmaceutical Ingredient")

            gated_effects, gated_prophylaxis = get_triggered_clarifications_only(
                lookup_key,
                atc_cls_str,
                atc_data.get("side_effects", []),
                atc_data.get("prophylaxis", ""),
                is_this_salt_triggered,
                patient_age,
                patient,
                ddi_involved_salts
            )

            drug_profiles.append({
                "salt": (clean_root or salt).title(),
                "class": atc_cls_str,
                "coverage_tier": tier,
                "risk_level": dyn_level,
                "risk_score": dyn_score,
                "route": route,
                "pediatric_safety": ("SAFE (Weight-based dosing)" if dyn_score and dyn_score < 35 else "CAUTION (Consult Pediatric Formulary)") if is_pediatric else None,
                "pediatric_dosage": "Verify mg/kg pediatric weight titration." if is_pediatric else None,
                "side_effects": gated_effects,
                "prophylaxis": gated_prophylaxis,
                "black_box_warning": "Active Organ/Pharmacokinetic Risk Detected: Verify clearance and co-prescribed medications." if is_this_salt_triggered else None,
                "evidence_citation": atc_data.get("evidence_citation")
            })

        drug["clinical_profiles"] = drug_profiles

    has_fatal = any(a["severity"] == "FATAL" for a in alerts)
    has_high = any(a["severity"] == "HIGH" for a in alerts)

    if has_fatal:
        cumulative_risk_score = 96
        cumulative_risk_level = "CRITICAL / FATAL HAZARD"
        audit_verdict = "COLLISION_DETECTED"
    elif has_high:
        cumulative_risk_score = max(78, max(drug_scores) if drug_scores else 78)
        cumulative_risk_level = "HIGH RISK ELEVATION"
        audit_verdict = "COLLISION_DETECTED"
    elif alerts:
        cumulative_risk_score = max(45, max(drug_scores) if drug_scores else 45)
        cumulative_risk_level = "MODERATE WARNING"
        audit_verdict = "WARNING_DETECTED"
    elif drug_scores:
        cumulative_risk_score = min(100, int(sum(drug_scores) / len(drug_scores)))
        cumulative_risk_level = "MODERATE" if cumulative_risk_score >= 35 else "MILD / SAFE"
        audit_verdict = "FULL_CLEAR"
    else:
        cumulative_risk_score = 15
        cumulative_risk_level = "SAFE BASELINE"
        audit_verdict = "FULL_CLEAR"

    return {
        "prescribed_drugs": prescribed_drugs,
        "is_pediatric": is_pediatric,
        "patient_age": patient_age,
        "alerts": alerts,
        "recommendations": recommendations,
        "out_of_scope_drugs": [],
        "nti_detected_drugs": nti_detected_drugs,
        "surveillance_tiers": list(surveillance_tiers),
        "audit_verdict": audit_verdict,
        "cumulative_risk_score": cumulative_risk_score,
        "cumulative_risk_level": cumulative_risk_level,
        "medicolegal_disclaimer": "ARPA is an auxiliary clinical decision support system (CDSS) for licensed medical practitioners."
    }