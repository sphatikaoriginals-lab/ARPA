import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

def generate_prescription_pdf(data: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    brand_title_style = ParagraphStyle(
        'ARPATitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#001f54"), # Arkaya Deep Navy Blue
        spaceAfter=2
    )
    subtitle_style = ParagraphStyle(
        'ARPASub',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=10
    )
    section_heading = ParagraphStyle(
        'SecHead',
        parent=styles['Heading2'],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=8,
        spaceAfter=5
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    story = []

    # ARPA Header with Arkaya Healthcare Branding
    story.append(Paragraph("<b>ARPA</b> | Arkaya Rational Prescription Algorithm[cite: 1]", brand_title_style))
    report_time = datetime.now().strftime("%d %B %Y, %I:%M %p")
    story.append(Paragraph(f"Powered by: <b>Arkaya Healthcare</b>[cite: 1] | Generated: {report_time}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#001f54"), spaceAfter=8))

    # Patient Details Table
    patient = data.get("patient_profile", {})
    patient_info = [
        [
            Paragraph(f"<b>Patient Age:</b> {patient.get('age', 28)} yrs", body_style),
            Paragraph(f"<b>Pregnancy Status:</b> {'Positive' if patient.get('is_pregnant') else 'Negative'}", body_style)
        ],
        [
            Paragraph(f"<b>Renal Impairment:</b> {'Detected' if patient.get('has_renal_disease') else 'None'}", body_style),
            Paragraph(f"<b>Hepatic Dysfunction:</b> {'Detected' if patient.get('has_liver_disease') else 'None'}", body_style)
        ]
    ]
    t_patient = Table(patient_info, colWidths=[260, 260])
    t_patient.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0fdf4")), # Medical Mint Tint
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_patient)
    story.append(Spacer(1, 8))

    # Active Drug Entities Breakdown
    story.append(Paragraph("Evaluated Formulations & Resolved Chemical Salts", section_heading))
    drugs = data.get("prescribed_drugs", [])
    drug_rows = [["Prescribed Brand", "Resolved Active Chemical Moieties"]]
    for d in drugs:
        salts_text = ", ".join(d.get("salts", [])) if d.get("salts") else "Unresolved generic"
        drug_rows.append([d.get("brand", ""), salts_text])

    t_drugs = Table(drug_rows, colWidths=[180, 340])
    t_drugs.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#001f54")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('TOPPADDING', (0,0), (-1,0), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('BACKGROUND', (0,1), (-1,-1), colors.white),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
    ]))
    story.append(t_drugs)
    story.append(Spacer(1, 8))

    # ARPA Clinical Alerts & Risk Assessment
    story.append(Paragraph("ARPA Clinical Safety & Interaction Evaluation", section_heading))
    alerts = data.get("alerts", [])
    if not alerts:
        story.append(Paragraph("<font color='#059669'><b>✓ ARPA STATUS CLEAR:</b> No significant biochemical conflicts or organ-system contraindications identified.</font>", body_style))
    else:
        alert_rows = [["Risk Level", "Clinical Hazard / Interaction", "ARPA Clinical Directive"]]
        for a in alerts:
            sev = a.get("severity", "HIGH")
            desc_text = f"<b>{a.get('effect')}</b><br/>{a.get('description')}<br/><font color='#64748b'>Trigger: {a.get('conflict_between')}</font>"
            action_text = a.get("action", "")
            alert_rows.append([sev, Paragraph(desc_text, body_style), Paragraph(action_text, body_style)])

        t_alerts = Table(alert_rows, colWidths=[70, 270, 180])
        t_alerts.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#991b1b")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story.append(t_alerts)

    story.append(Spacer(1, 10))

    # ARPA Safe Substitutes
    recommendations = data.get("recommendations", [])
    if recommendations:
        story.append(Paragraph("ARPA Recommended Safe Therapeutic Substitutes", section_heading))
        rec_rows = [["Flagged Conflict", "Recommended Safe Alternatives & Rationale"]]
        for r in recommendations:
            opts = "<br/>".join([f"• <b>{opt['salt']}</b> ({', '.join(opt['brands'])}): {opt['rationale']}" for opt in r.get("options", [])])
            rec_rows.append([Paragraph(r.get("triggered_by", ""), body_style), Paragraph(opts, body_style)])

        t_rec = Table(rec_rows, colWidths=[150, 370])
        t_rec.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284c7")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_rec)
        story.append(Spacer(1, 10))

    footer_text = "Arkaya Healthcare — ARPA (Arkaya Rational Prescription Algorithm)[cite: 1]. Automated clinical safety assessment for registered medical practitioners and licensed pharmacists."
    story.append(Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Italic'], fontSize=7.5, textColor=colors.HexColor("#94a3b8"))))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()