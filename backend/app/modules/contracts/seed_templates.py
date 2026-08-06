"""Idempotently seed the built-in system contract templates.

System templates have tenant_id=None + is_system=True so they are visible to
every tenant. They cannot be edited or deleted through the API.
"""
from app.core.database import get_db
from app.core.repository import new_id, utcnow_iso


SYSTEM_TEMPLATES: list[dict] = [
    {
        "code": "website_dev",
        "name": "Website Development Agreement",
        "category": "Development",
        "body_html": """
<h1>Website Development Agreement</h1>
<p>This Agreement is entered into on {{today_date}} between <strong>{{company_name_ours}}</strong> (the "Developer") and <strong>{{company_name}}</strong> (the "Client"), represented by {{contact_person}}, of {{address}}.</p>
<h2>1. Scope of Work</h2>
<p>The Developer will design, develop and deploy a website for the Client according to the specifications agreed upon separately. Deliverables include design mock-ups, front-end and back-end implementation, and deployment to the Client's hosting environment.</p>
<h2>2. Timeline</h2>
<p>Kick-off: {{start_date}}. Target delivery: {{end_date}}.</p>
<h2>3. Fees</h2>
<p>The total contract fee is <strong>{{contract_amount}}</strong>, invoiced according to the following schedule: 50% upon signing, 50% upon final delivery.</p>
<h2>4. Ownership</h2>
<p>Upon receipt of full payment, all custom source code, designs and copy produced for the Client become the Client's property. Third-party libraries remain under their respective licences.</p>
<h2>5. Confidentiality</h2>
<p>Each party will keep confidential any information marked or reasonably understood to be confidential.</p>
<h2>6. Term & Termination</h2>
<p>This Agreement remains in force until deliverables are accepted. Either party may terminate with 14 days' written notice; work completed to that date remains payable.</p>
<h2>7. Signatures</h2>
<p>Signed for {{company_name_ours}}: ___________________________<br/>Signed for {{company_name}}: ___________________________</p>
""",
    },
    {
        "code": "graphic_design",
        "name": "Graphic Design Agreement",
        "category": "Design",
        "body_html": """
<h1>Graphic Design Agreement</h1>
<p>Between <strong>{{company_name_ours}}</strong> (Designer) and <strong>{{company_name}}</strong> (Client), dated {{today_date}}.</p>
<h2>1. Deliverables</h2>
<p>Designer will produce the visual assets described in the accompanying brief, including logo variants, colour palette, typography guidelines and application mock-ups.</p>
<h2>2. Revisions</h2>
<p>Two rounds of revisions are included. Additional rounds are billed at the Designer's hourly rate.</p>
<h2>3. Fees</h2>
<p>Total: <strong>{{contract_amount}}</strong>. Deposit: 40%. Balance on delivery.</p>
<h2>4. Licence</h2>
<p>Upon full payment, the Client receives an exclusive, worldwide licence to use the delivered artwork in its business. The Designer retains portfolio rights.</p>
<h2>5. Signatures</h2>
<p>Client: {{contact_person}} — Date: __________<br/>Designer: {{company_name_ours}} — Date: __________</p>
""",
    },
    {
        "code": "marketing",
        "name": "Marketing Agreement",
        "category": "Marketing",
        "body_html": """
<h1>Marketing Services Agreement</h1>
<p>This Agreement is made on {{today_date}} between <strong>{{company_name_ours}}</strong> (the "Agency") and <strong>{{company_name}}</strong> (the "Client"), represented by {{contact_person}}.</p>
<h2>1. Services</h2>
<p>The Agency will provide marketing strategy, campaign execution, content creation and performance reporting as detailed in the attached scope.</p>
<h2>2. Term</h2>
<p>From {{start_date}} to {{end_date}}, renewable monthly by mutual consent.</p>
<h2>3. Fees</h2>
<p>Monthly retainer of <strong>{{contract_amount}}</strong>, invoiced on the 1st of each month, payable within 14 days. Ad spend is billed separately at cost.</p>
<h2>4. Reporting</h2>
<p>The Agency will provide monthly performance reports covering reach, engagement, conversions and ROI.</p>
<h2>5. Confidentiality</h2>
<p>Both parties will keep confidential any non-public information exchanged under this Agreement.</p>
""",
    },
    {
        "code": "printing",
        "name": "Printing Services Agreement",
        "category": "Production",
        "body_html": """
<h1>Printing Services Agreement</h1>
<p>Between <strong>{{company_name_ours}}</strong> (Printer) and <strong>{{company_name}}</strong> (Client), signed {{today_date}}.</p>
<h2>1. Order</h2>
<p>The Printer will produce the items detailed in the Client's approved purchase order, at the agreed specifications for stock, finishing and delivery date.</p>
<h2>2. Proofing</h2>
<p>The Printer will supply a digital proof for the Client's written approval before going to press. Client approval releases the Printer from responsibility for content errors.</p>
<h2>3. Fees</h2>
<p>Total: <strong>{{contract_amount}}</strong>. 50% deposit required to begin production. Balance due before delivery.</p>
<h2>4. Delivery</h2>
<p>Estimated delivery: {{end_date}}. Delays caused by material shortages, courier issues or client-side approvals extend this date correspondingly.</p>
""",
    },
    {
        "code": "maintenance",
        "name": "Maintenance & Support Agreement",
        "category": "Ongoing",
        "body_html": """
<h1>Maintenance & Support Agreement</h1>
<p>Between <strong>{{company_name_ours}}</strong> (Provider) and <strong>{{company_name}}</strong> (Client), effective {{start_date}}.</p>
<h2>1. Scope</h2>
<p>The Provider will supply routine maintenance, updates, security patches and technical support for the systems agreed with the Client.</p>
<h2>2. Response Times</h2>
<ul><li>Critical (system down): within 2 business hours</li><li>High (major degradation): within 1 business day</li><li>Normal: within 3 business days</li></ul>
<h2>3. Fees</h2>
<p>Fixed monthly fee: <strong>{{contract_amount}}</strong>. Work outside this scope is billed hourly.</p>
<h2>4. Term</h2>
<p>Rolling monthly. Either party may terminate with 30 days' written notice.</p>
""",
    },
    {
        "code": "monthly_service",
        "name": "Monthly Service Agreement",
        "category": "Ongoing",
        "body_html": """
<h1>Monthly Service Agreement</h1>
<p>Between <strong>{{company_name_ours}}</strong> and <strong>{{company_name}}</strong>, effective {{start_date}}.</p>
<h2>1. Services</h2>
<p>The Provider will render the services listed in the accompanying scope on a recurring monthly basis.</p>
<h2>2. Payment</h2>
<p>Monthly fee: <strong>{{contract_amount}}</strong>, invoiced on the 1st of each month, due within 7 days.</p>
<h2>3. Term & Renewal</h2>
<p>Auto-renews monthly unless cancelled in writing 30 days in advance.</p>
""",
    },
    {
        "code": "nda",
        "name": "Non-Disclosure Agreement (NDA)",
        "category": "Legal",
        "body_html": """
<h1>Mutual Non-Disclosure Agreement</h1>
<p>This Non-Disclosure Agreement (the "Agreement") is entered into on {{today_date}} between <strong>{{company_name_ours}}</strong> and <strong>{{company_name}}</strong>, together the "Parties".</p>
<h2>1. Definition of Confidential Information</h2>
<p>Confidential Information means any non-public information disclosed by either Party, whether in writing, orally or by any other means, and whether or not marked confidential, that a reasonable person would understand to be confidential.</p>
<h2>2. Obligations</h2>
<p>Each Party shall (a) hold the other's Confidential Information in strict confidence, (b) use it solely to evaluate or perform the purpose for which it was disclosed, and (c) protect it with at least the same care it uses for its own confidential information.</p>
<h2>3. Exclusions</h2>
<p>Confidential Information does not include information that is publicly known, independently developed, rightfully received from a third party, or required to be disclosed by law.</p>
<h2>4. Term</h2>
<p>This Agreement is effective from the date signed and continues for 3 years thereafter.</p>
<h2>5. Governing Law</h2>
<p>This Agreement is governed by the laws of the jurisdiction in which {{company_name_ours}} is registered.</p>
""",
    },
    {
        "code": "freelancer",
        "name": "Freelancer Agreement",
        "category": "Employment",
        "body_html": """
<h1>Freelancer Agreement</h1>
<p>This Agreement is entered into on {{today_date}} between <strong>{{company_name_ours}}</strong> (the "Company") and <strong>{{contact_person}}</strong> (the "Freelancer").</p>
<h2>1. Services</h2>
<p>The Freelancer will deliver the services described in the attached statement of work.</p>
<h2>2. Independent Contractor</h2>
<p>The Freelancer is an independent contractor. Nothing in this Agreement creates an employer-employee relationship. The Freelancer is responsible for their own taxes and benefits.</p>
<h2>3. Fees</h2>
<p>Total: <strong>{{contract_amount}}</strong>. Payment terms: NET 14 upon acceptance of deliverables.</p>
<h2>4. Intellectual Property</h2>
<p>Upon full payment, all deliverables become the property of the Company. Tools, frameworks and background IP owned by the Freelancer remain the Freelancer's property.</p>
<h2>5. Term</h2>
<p>From {{start_date}} to {{end_date}}.</p>
""",
    },
]


async def seed_system_templates() -> int:
    db = get_db()
    added = 0
    for tpl in SYSTEM_TEMPLATES:
        existing = await db.contract_templates.find_one(
            {"tenant_id": None, "is_system": True, "code": tpl["code"]}
        )
        if existing:
            continue
        _id = new_id()
        await db.contract_templates.insert_one({
            "_id": _id, "id": _id,
            "tenant_id": None,
            "is_system": True,
            "code": tpl["code"],
            "name": tpl["name"],
            "category": tpl["category"],
            "body_html": tpl["body_html"].strip(),
            "created_at": utcnow_iso(),
            "updated_at": utcnow_iso(),
        })
        added += 1
    return added
