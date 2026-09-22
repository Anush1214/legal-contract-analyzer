import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from backend.config import SAMPLE_DIR

CONTRACT_1_CLAUSES = [
    ("Section 1. Scope of Enterprise Services",
     "Vendor agrees to provide the cloud-hosted enterprise software platform described in Schedule A. Vendor reserves the right to modify, deprecate, or alter platform features and APIs at any time in its sole discretion without prior notice to Customer."),
    
    ("Section 2. Fees, Pricing Adjustments, and Invoicing",
     "Customer shall pay all annual subscription fees upfront within fifteen (15) days of invoice date. Unpaid balances shall accrue interest at the maximum rate of 1.5% per month or the highest rate permitted by law. All fees paid are strictly non-refundable under any circumstances. Vendor reserves the right to increase fees by up to 15% upon each renewal term without requirement of Customer approval."),
    
    ("Section 3. Term and Automatic Evergreen Renewal",
     "This Agreement shall commence on the Effective Date and continue for an initial fixed commitment period of thirty-six (36) months. Upon expiration of the initial commitment, this Agreement shall automatically renew for successive consecutive twelve (12) month terms unless Customer delivers formal written notice of non-renewal via certified mail at least ninety (90) days prior to the expiration of the then-current term."),
    
    ("Section 4. Early Termination and Liquidated Damages",
     "Customer may not terminate this Agreement for convenience prior to the expiration of the full term. In the event Customer attempts early termination, repudiates the contract, or breaches payment obligations, Customer shall immediately pay Vendor an early termination penalty and liquidated damages amount equal to one hundred percent (100%) of the remaining aggregate subscription fees that would have become due throughout the remainder of the full commitment period."),
    
    ("Section 5. Intellectual Property Rights and Derived Data",
     "Vendor exclusively retains all right, title, and interest in and to the Software, documentation, underlying source code, system algorithms, and all work product created during the engagement. Customer hereby grants Vendor an irrevocable, perpetual, royalty-free, worldwide license to ingest, aggregate, and utilize Customer data to train machine learning models and improve Vendor proprietary algorithms."),
    
    ("Section 6. Confidentiality and Proprietary Information",
     "Each party agrees to safeguard the other party's Confidential Information with the same degree of care it uses to protect its own confidential trade secrets, but not less than reasonable care. Confidential information shall remain protected for a period of five (5) years following termination."),
    
    ("Section 7. Unilateral Customer Indemnification",
     "Customer shall defend, indemnify, and hold harmless Vendor, its parent entities, officers, directors, and affiliates from and against any and all claims, liabilities, lawsuits, damages, penalties, and legal defense fees arising out of or relating to Customer's use of the software, Customer's data, or alleged infringement of third-party intellectual property rights."),
    
    ("Section 8. Absolute Limitation of Vendor Liability",
     "To the maximum extent permitted by applicable law, in no event shall Vendor be liable for any indirect, incidental, special, consequential, or punitive damages. Vendor's total cumulative aggregate liability for any and all claims arising out of this agreement shall under no circumstances exceed fifty United States Dollars ($50.00) or the amount paid by Customer in the single month preceding the event."),
    
    ("Section 9. Restrictive Covenants and Worldwide Non-Compete",
     "During the term of this Agreement and for a period of twenty-four (24) months following termination for any reason, Customer covenants and agrees that it shall not directly or indirectly develop, commercialize, market, or license any software product that provides substantially similar functionality, nor shall Customer hire, solicit, or contract any employee or contractor of Vendor in any territory worldwide."),
    
    ("Section 10. Governing Law, Binding Arbitration, and Waiver of Jury Trial",
     "This Agreement shall be construed and governed strictly by the laws of the State of Delaware, without regard to conflict of law principles. Any dispute arising under this Agreement shall be resolved exclusively through final and binding arbitration administered by the American Arbitration Association in Wilmington, Delaware. Customer irrevocably waives any right to a trial by jury and agrees never to participate in any class action litigation against Vendor.")
]

CONTRACT_2_CLAUSES = [
    ("Section 1. Engagement and Consulting Services",
     "Consultant shall perform the technical consulting and advisory services set forth in the mutually executed Statement of Work. Any material modifications or scope revisions must be executed via mutual written agreement signed by authorized representatives of both parties."),
    
    ("Section 2. Compensation and Payment Milestones",
     "Client shall pay Consultant for approved deliverables within thirty (30) calendar days of receiving a verified itemized invoice (Net 30). In the event of a good faith billing dispute, Client shall notify Consultant within ten (10) days, and undisputed portions of invoices shall be promptly remitted without delay."),
    
    ("Section 3. Term and Mutual Termination for Convenience",
     "This Agreement commences on the Effective Date and shall remain in effect until completion of the Statement of Work or until terminated by either party. Either party may terminate this Agreement at any time for convenience, with or without cause, upon thirty (30) days prior written notice. Upon termination, Client shall only be responsible for paying fees earned for services satisfactorily delivered prior to the termination effective date."),
    
    ("Section 4. Intellectual Property and Deliverable Ownership",
     "Upon receipt of full payment from Client, Consultant hereby assigns and transfers to Client all right, title, and ownership in and to the custom software code, designs, and deliverables created specifically for Client under this Agreement. Consultant retains ownership of its pre-existing background tools and general technical methodologies."),
    
    ("Section 5. Mutual Non-Disclosure and Confidentiality",
     "Both parties agree to treat proprietary information received from the other party as confidential, exercising reasonable care to avoid unauthorized disclosure. Neither party shall disclose confidential terms without prior written authorization, except as strictly required by valid legal subpoena."),
    
    ("Section 6. Mutual Indemnification",
     "Each party agrees to defend, indemnify, and hold harmless the other party from any third-party claims, damages, and reasonable attorney fees resulting directly from the indemnifying party's gross negligence, intentional misconduct, or material breach of confidentiality."),
    
    ("Section 7. Mutual Limitation of Liability",
     "Neither party shall be liable for indirect, incidental, or speculative damages. Each party's maximum aggregate cumulative liability arising out of or relating to this Agreement shall be strictly capped at the total aggregate fees paid or payable by Client to Consultant under the applicable Statement of Work during the preceding twelve (12) month period."),
    
    ("Section 8. Non-Solicitation of Personnel",
     "During the term and for twelve (12) months thereafter, neither party shall actively solicit for employment any employee or key personnel of the other party directly involved in the engagement. This restriction shall not apply to general public job postings or responses to unsolicited job advertisements."),
    
    ("Section 9. Governing Law and Jurisdiction",
     "This Agreement shall be interpreted in accordance with the laws of the State of New York. In the event of any disagreement, the parties agree to first attempt informal executive negotiation for thirty (30) days prior to initiating legal proceedings in state or federal courts located in New York County.")
]

CONTRACT_INDIA_IT_CLAUSES = [
    ("Section 1. Engagement and Scope of Software Services",
     "Vendor (TechFlow Software India Private Limited, Bengaluru) shall deliver cloud software engineering, API integrations, and maintenance services as specified in the Statement of Work. All deliverables shall comply with Indian standard industry specifications."),

    ("Section 2. Invoicing, Goods & Services Tax (GST), and TDS Deductions",
     "Fees shall be invoiced in Indian Rupees (INR). Customer shall pay all undisputed invoices within thirty (30) days of receipt. Invoices shall reflect applicable Goods and Services Tax (GST) under the Central Goods and Services Tax Act, 2017 (CGST/SGST/IGST). Customer shall deduct Tax Deducted at Source (TDS) under Section 194J of the Income Tax Act, 1961, and provide valid Form 16A TDS certificates within the statutory deadline."),

    ("Section 3. Term and Renewal",
     "This Agreement shall be effective for an initial term of twenty-four (24) months from the Effective Date. The Agreement shall renew automatically for successive twelve (12) month periods unless either party provides sixty (60) days prior written non-renewal notice."),

    ("Section 4. Intellectual Property Rights and Indian Copyright Act Waiver",
     "Upon receipt of full payment, Vendor assigns to Customer all ownership rights in custom bespoke code developed under this Agreement. Pursuant to Section 19(4) of the Indian Copyright Act, 1957, Vendor expressly agrees that the assignment of copyright shall not lapse, notwithstanding that Customer does not exercise the rights within a period of one year from the date of assignment."),

    ("Section 5. Data Protection and Digital Personal Data Protection Act Compliance",
     "Each party covenants strict compliance with the Digital Personal Data Protection Act, 2023 (DPDP Act) and the Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011 promulgated under Section 43A of the Information Technology Act, 2000. Customer personal data shall not be transferred outside India without prior statutory notification."),

    ("Section 6. Restrictive Covenants and Post-Termination Non-Compete",
     "During the term of this Agreement and for a period of twenty-four (24) months following termination, Customer and its affiliates shall not directly or indirectly engage in, finance, or operate any software enterprise competing with Vendor within the territory of India, nor recruit any personnel of Vendor. (Note: Under Section 27 of the Indian Contract Act, 1872, agreements in restraint of trade are void to that extent)."),

    ("Section 7. Indemnification and Defense",
     "Customer agrees to indemnify, defend, and hold harmless Vendor and its directors from any third-party claims, tax penalties, or regulatory liabilities arising out of Customer's breach of applicable Indian cyber laws or unauthorized data processing."),

    ("Section 8. Limitation of Liability",
     "To the fullest extent permitted under the Indian Contract Act, 1872, Vendor's total cumulative aggregate liability for all claims under this Agreement shall not exceed fifty thousand Indian Rupees (INR 50,000) or the fees paid by Customer in the preceding one (1) month, excluding cases of gross negligence or willful misconduct."),

    ("Section 9. Stamp Duty and Enforceability",
     "This Agreement shall be duly executed on non-judicial stamp paper of appropriate denomination in accordance with the Karnataka Stamp Act, 1957. The expenses of stamp duty shall be borne equally by both parties."),

    ("Section 10. Governing Law, Seat of Arbitration, and Jurisdiction",
     "This Agreement shall be governed by and construed in accordance with the substantive laws of the Republic of India. Any dispute or claim arising out of or in connection with this Agreement shall be referred to and finally resolved by arbitration administered under the Arbitration and Conciliation Act, 1996. The arbitral tribunal shall consist of a sole arbitrator appointed by mutual consent. The seat and venue of arbitration shall be Bengaluru, Karnataka, India. Subject to arbitration, the courts at Bengaluru shall have exclusive jurisdiction.")
]

CONTRACT_INDIA_EMPLOYMENT_CLAUSES = [
    ("Section 1. Appointment, Role, and Compensation",
     "The Company hereby appoints the Executive as Principal Legal Counsel. Executive shall receive a total annual Cost to Company (CTC) payable monthly, subject to statutory deductions including Employees' Provident Fund (EPF Act, 1952), Professional Tax, and Income Tax TDS."),

    ("Section 2. Probation Period and Separation Notice",
     "The Executive shall serve a probationary period of six (6) months. During probation, either party may terminate the employment with fifteen (15) days written notice. Following confirmation, either party may terminate by providing ninety (90) days advance notice or gross basic salary in lieu thereof."),

    ("Section 3. Liquidated Damages for Early Departure",
     "If the Executive resigns or terminates employment prior to completing twelve (12) months of active service, the Executive agrees to pay the Company an early separation indemnity of INR 5,00,000 as liquidated damages under Section 74 of the Indian Contract Act, 1872 to reimburse specialized onboarding and training expenditures."),

    ("Section 4. Proprietary Information and Inventions Assignment",
     "All patents, trademarks, works of authorship, and technological innovations created by Executive during employment shall constitute works made for hire under the Indian Copyright Act, 1957 and Patents Act, 1970, belonging exclusively to the Company from inception."),

    ("Section 5. Confidentiality Obligations",
     "Executive shall hold all confidential information, business secrets, and client data in strictest confidence during and perpetually after employment, in accordance with Indian common law duties of breach of confidence."),

    ("Section 6. Post-Employment Non-Compete Restriction",
     "Executive undertakes that for a period of twelve (12) months following separation, Executive shall not join, advise, or consult for any direct competitor operating in India. (Note: Indian jurisprudence under Niranjan Shankar Golikari and Percept D'Mark establishes that post-employment non-compete covenants are generally void and unenforceable under Section 27 of the Indian Contract Act, 1872)."),

    ("Section 7. Non-Solicitation of Employees and Clients",
     "For a period of twenty-four (24) months following termination, Executive shall not solicit, entice, or induce any employee, contractor, or vendor of the Company to terminate their engagement with the Company."),

    ("Section 8. Prevention of Sexual Harassment (POSH) and Code of Conduct",
     "Executive covenants strict compliance with the Company Code of Conduct and the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 (POSH Act). Any violation constitutes grounds for immediate termination for cause without notice or severance."),

    ("Section 9. Governing Law and Exclusive Jurisdiction",
     "This Agreement is governed by the laws of India. Any legal action, dispute, or proceeding relating to this Agreement shall be subject to the exclusive jurisdiction of the civil courts and labor tribunals in New Delhi, India.")
]

CONTRACT_INDIA_NDA_CLAUSES = [
    ("Section 1. Parties and Purpose of Evaluation",
     "This Mutual Non-Disclosure Agreement is executed between Mumbai Alpha Innovations Private Limited (Mumbai, Maharashtra) and Bangalore Tech Ventures Private Limited (Bengaluru, Karnataka) to facilitate confidential evaluations of strategic joint commercial software ventures."),

    ("Section 2. Definition of Confidential Information",
     "Confidential Information encompasses all proprietary software architectures, algorithmic models, API specifications, financial forecasts, customer lists, and trade secrets disclosed by either party, whether in oral, visual, or electronic form."),

    ("Section 3. Non-Disclosure Obligations and Standard of Care",
     "The Receiving Party shall safeguard the Disclosing Party's Confidential Information with the same degree of care it employs for its own proprietary trade secrets, but not less than reasonable care. Information shall only be shared with personnel who have a strict need-to-know."),

    ("Section 4. Exclusions and Regulatory Compulsion",
     "Confidential Information does not include information that becomes publicly known through no fault of Receiving Party. Disclosure is permitted where required by court summons under the Code of Civil Procedure, 1908, or regulatory directives issued by SEBI, RBI, or the Ministry of Corporate Affairs (MCA)."),

    ("Section 5. Digital Personal Data Protection Act Compliance",
     "Where Confidential Information includes personal identifiers of Indian citizens, both parties shall adhere strictly to the Digital Personal Data Protection Act, 2023 (DPDP Act) and implement standard data security safeguards under Section 43A of the Information Technology Act, 2000."),

    ("Section 6. Return or Verified Destruction of Proprietary Data",
     "Within fourteen (14) days of receiving a written request, the Receiving Party shall return or certify the permanent destruction of all documents, memory drives, and derived analytical summaries containing Confidential Information."),

    ("Section 7. Injunctive Relief and Specific Performance",
     "Both parties acknowledge that monetary damages alone would be inadequate compensation for a breach of trade secrets. The Disclosing Party shall be entitled to seek immediate preliminary and permanent injunctive relief and specific performance under the Specific Relief Act, 1963 without requirement of posting bond."),

    ("Section 8. Term of Protection",
     "The confidentiality obligations under this Agreement shall persist for a period of three (3) years from the date of disclosure; provided that trade secrets and proprietary source code shall remain confidential perpetually until public disclosure without fault."),

    ("Section 9. Governing Law, Stamp Duty, and Jurisdiction",
     "This Agreement is executed under the laws of the Republic of India and subject to appropriate stamp duty under the Maharashtra Stamp Act, 1958. Any dispute arising out of or related to this Agreement shall be subject to the exclusive jurisdiction of the competent courts in Mumbai, Maharashtra, India.")
]

CONTRACT_INDIA_LEASE_CLAUSES = [
    ("Section 1. Demised Premises and Term of Lease",
     "Lessor (Embassy TechParks Developers Private Limited, Bengaluru) grants to Lessee (CloudMatrix Technologies Private Limited) a commercial lease of Suite 401, measuring 8,500 square feet at Outer Ring Road IT Corridor, Bengaluru, for an initial term of five (5) years."),

    ("Section 2. Monthly Rent, GST, and Maintenance Escalation",
     "Lessee shall pay monthly lease rent of INR 8,50,000 plus applicable Goods & Services Tax (18% GST) in advance by the 5th day of each calendar month. The lease rent shall be subject to a predetermined escalation of 5% per annum at the end of each consecutive twelve (12) month period."),

    ("Section 3. Interest-Free Refundable Security Deposit",
     "Lessee has deposited with Lessor an interest-free refundable security deposit equal to six (6) months' rent (INR 51,00,000). The deposit shall be refunded within thirty (30) days of vacant handover of the premises, subject to deductions for unpaid utilities or structural restoration."),

    ("Section 4. Mandatory Lock-in Period and Liquidated Damages",
     "Both parties agree to a mandatory lock-in period of thirty-six (36) months from the Commencement Date. In the event Lessee vacates, surrenders, or breaches the lease prior to the expiration of the lock-in period, Lessee shall be liable to pay liquidated damages equal to the entire balance of rent payable for the remainder of the lock-in period under Section 74 of the Indian Contract Act, 1872."),

    ("Section 5. Statutory Duties and Transfer of Property Act Covenants",
     "The rights and obligations of the Lessor and Lessee shall be governed by Section 108 of the Transfer of Property Act, 1882. Lessee shall keep the interior in good tenantable repair, while Lessor remains responsible for major structural integrity and external facade."),

    ("Section 6. Permitted Commercial Use and Subletting Restrictions",
     "The demised premises shall be utilized exclusively for IT/ITES software development. Lessee shall not assign, sublet, underlet, or part with possession of the premises or any part thereof without obtaining the prior written consent of the Lessor."),

    ("Section 7. Default, Notice, and Right of Re-entry",
     "In the event of default in rent payment exceeding thirty (30) days, Lessor shall serve a fifteen (15) day cure notice under Section 111(g) of the Transfer of Property Act, 1882. If uncured, Lessor shall have the right of re-entry and immediate termination of lease."),

    ("Section 8. Stamp Duty, Registration, and Legal Costs",
     "This lease agreement shall be compulsorily registered under Section 17 of the Registration Act, 1908, with stamp duty paid in compliance with the Karnataka Stamp Act, 1957. The cost of stamp duty and registration fees shall be shared equally between Lessor and Lessee."),

    ("Section 9. Governing Law, Arbitration, and Jurisdiction",
     "This Lease shall be interpreted under the laws of India. Any dispute arising out of this lease shall be resolved by arbitration under the Arbitration and Conciliation Act, 1996 by a sole arbitrator sitting at Bengaluru. The civil courts and commercial courts at Bengaluru shall have exclusive jurisdiction.")
]

def generate_pdf(filename: str, title: str, clauses: list) -> Path:
    """Generate a clean, professional PDF file containing legal clauses."""
    filepath = SAMPLE_DIR / filename
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ContractTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=14
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=10,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'ClauseBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    
    story = [
        Paragraph(title, title_style),
        Spacer(1, 10)
    ]
    
    for sec_header, sec_text in clauses:
        story.append(Paragraph(sec_header, section_style))
        story.append(Paragraph(sec_text, body_style))
        story.append(Spacer(1, 4))
        
    doc.build(story)
    return filepath

def ensure_sample_contracts():
    """Ensure sample contract PDFs exist on disk, including Indian law contracts."""
    p1 = SAMPLE_DIR / "Enterprise_SaaS_Vendor_Agreement.pdf"
    p2 = SAMPLE_DIR / "Standard_Consulting_Services_Agreement.pdf"
    p3 = SAMPLE_DIR / "India_Master_IT_Services_Agreement.pdf"
    p4 = SAMPLE_DIR / "India_Executive_Employment_Agreement.pdf"
    p5 = SAMPLE_DIR / "India_Mutual_Non_Disclosure_Agreement.pdf"
    p6 = SAMPLE_DIR / "India_Commercial_Office_Lease_Agreement.pdf"
    
    if not p1.exists():
        generate_pdf("Enterprise_SaaS_Vendor_Agreement.pdf", "ENTERPRISE SAAS MASTER SUBSCRIPTION AGREEMENT", CONTRACT_1_CLAUSES)
    if not p2.exists():
        generate_pdf("Standard_Consulting_Services_Agreement.pdf", "STANDARD CONSULTING AND PROFESSIONAL SERVICES AGREEMENT", CONTRACT_2_CLAUSES)
    if not p3.exists():
        generate_pdf("India_Master_IT_Services_Agreement.pdf", "MASTER IT SERVICES AGREEMENT (INDIAN JURISDICTION)", CONTRACT_INDIA_IT_CLAUSES)
    if not p4.exists():
        generate_pdf("India_Executive_Employment_Agreement.pdf", "EXECUTIVE EMPLOYMENT & CONFIDENTIALITY AGREEMENT (INDIAN LAW)", CONTRACT_INDIA_EMPLOYMENT_CLAUSES)
    if not p5.exists():
        generate_pdf("India_Mutual_Non_Disclosure_Agreement.pdf", "MUTUAL NON-DISCLOSURE AGREEMENT (INDIAN CONTRACT ACT 1872)", CONTRACT_INDIA_NDA_CLAUSES)
    if not p6.exists():
        generate_pdf("India_Commercial_Office_Lease_Agreement.pdf", "COMMERCIAL OFFICE LEASE AGREEMENT (TRANSFER OF PROPERTY ACT 1882)", CONTRACT_INDIA_LEASE_CLAUSES)
        
    return [p1, p2, p3, p4, p5, p6]
