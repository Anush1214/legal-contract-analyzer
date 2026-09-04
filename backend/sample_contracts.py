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
    """Ensure sample contract PDFs exist on disk."""
    p1 = SAMPLE_DIR / "Enterprise_SaaS_Vendor_Agreement.pdf"
    p2 = SAMPLE_DIR / "Standard_Consulting_Services_Agreement.pdf"
    
    if not p1.exists():
        generate_pdf("Enterprise_SaaS_Vendor_Agreement.pdf", "ENTERPRISE SAAS MASTER SUBSCRIPTION AGREEMENT", CONTRACT_1_CLAUSES)
    if not p2.exists():
        generate_pdf("Standard_Consulting_Services_Agreement.pdf", "STANDARD CONSULTING AND PROFESSIONAL SERVICES AGREEMENT", CONTRACT_2_CLAUSES)
        
    return [p1, p2]
