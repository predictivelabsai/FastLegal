"""Public FastLegal product landing page (GTM stub)."""
from urllib.parse import quote

from fasthtml.common import *

ACCENT = "#4f46e5"
TINT = "#f2f1ff"
FAVICON = "data:image/svg+xml," + quote(
    """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="7" fill="#4f46e5"/><path fill="white" d="M16 4 28 16 16 28 4 16Z"/></svg>""",
    safe="",
)

CSS = """
:root{--accent:#4f46e5;--tint:#f2f1ff;--ink:#111827;--muted:#667085;--line:#e7eaf0}
*{box-sizing:border-box} body{margin:0;background:#fff;color:var(--ink);font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}
.lp-nav{height:68px;display:flex;align-items:center;justify-content:space-between;max-width:1180px;margin:auto;padding:0 24px;border-bottom:1px solid var(--line)}
.lp-brand{display:flex;align-items:center;gap:10px;font-weight:750;color:var(--ink);text-decoration:none} .lp-mark{width:30px;height:30px;border-radius:10px;background:var(--accent);display:grid;place-items:center;color:white}
.lp-nav-actions{display:flex;align-items:center;gap:18px} .lp-nav-link{color:var(--muted);text-decoration:none;font-size:14px;font-weight:650}
.lp-hero{max-width:1180px;margin:auto;padding:104px 24px 76px} .lp-kicker{color:var(--accent);font-size:12px;font-weight:750;text-transform:uppercase;letter-spacing:.16em}
.lp-hero h1{font-size:clamp(42px,7vw,78px);line-height:1.02;letter-spacing:-.055em;max-width:920px;margin:22px 0} .lp-lede{font-size:20px;line-height:1.65;color:var(--muted);max-width:720px}
.lp-pricing{max-width:1180px;margin:auto;padding:72px 24px;scroll-margin-top:80px} .lp-pricing-head{max-width:720px}
.lp-pricing-head h2{font-size:32px;letter-spacing:-.03em;margin:10px 0 12px} .lp-pricing-head p{color:var(--muted);line-height:1.65;margin:0}
.lp-pricing-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:32px}
.lp-pricing-card{border:1px solid var(--line);border-radius:18px;padding:26px;background:#fff}
.lp-pricing-eyebrow{color:var(--accent);font-size:10px;font-weight:750;text-transform:uppercase;letter-spacing:.1em}
.lp-pricing-card h3{font-size:22px;margin:14px 0 8px} .lp-pricing-price{font-size:36px;font-weight:750;letter-spacing:-.03em;margin:8px 0 12px}
.lp-pricing-card>p:last-child{color:var(--muted);line-height:1.6;margin:0}
.lp-footer{max-width:1180px;margin:auto;padding:30px 24px 48px;color:var(--muted);font-size:13px;display:flex;justify-content:space-between;gap:20px}
@media(max-width:760px){.lp-pricing-grid{grid-template-columns:1fr}}
"""


def pricing_section():
    return Section(
        Div(
            Span("Pricing", cls="lp-kicker"),
            H2("Simple pricing for every FastSME product."),
            P("Every Fast* product uses the same two options: bring your own cloud for free, or host with us for €1 per month."),
            cls="lp-pricing-head",
        ),
        Div(
            Article(
                Span("BYOC", cls="lp-pricing-eyebrow"),
                H3("Bring Your Own Cloud"),
                P("Free", cls="lp-pricing-price"),
                P("Self-host on your own infrastructure or cloud. Full control of data and upgrades. No per-seat platform fee."),
                cls="lp-pricing-card",
            ),
            Article(
                Span("Hosted", cls="lp-pricing-eyebrow"),
                H3("Host with us"),
                P("€1 / month", cls="lp-pricing-price"),
                P("We run the product for you on FastSME-managed infrastructure. €1 per product per month."),
                cls="lp-pricing-card",
            ),
            cls="lp-pricing-grid",
        ),
        id="pricing",
        cls="lp-pricing",
    )


def landing_page():
    return Html(
        Head(
            Title("FastLegal · FastSME"),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            Meta(name="description", content="An open FastSME legal workspace with grounded assistant workflows."),
            Link(rel="icon", type="image/svg+xml", href=FAVICON),
            Link(rel="preconnect", href="https://fonts.googleapis.com"),
            Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;750&display=swap"),
            Style(CSS),
        ),
        Body(
            Nav(
                A(Span("F", cls="lp-mark"), Span("FastLegal"), href="/", cls="lp-brand"),
                Div(
                    A("Pricing", href="#pricing", cls="lp-nav-link"),
                    A("FastSME suite", href="https://fastsme.com/products", cls="lp-nav-link"),
                    A("GitHub", href="https://github.com/predictivelabsai/FastLegal", cls="lp-nav-link"),
                    cls="lp-nav-actions",
                ),
                cls="lp-nav",
            ),
            Main(
                Section(
                    Span("Legal AI", cls="lp-kicker"),
                    H1("Legal work with an open assistant."),
                    P("An open FastSME legal workspace with grounded assistant workflows.", cls="lp-lede"),
                    cls="lp-hero",
                ),
                pricing_section(),
            ),
            Footer(
                Span("FastLegal is part of the open-source FastSME suite."),
                A("View all products", href="https://fastsme.com/products", style="color:var(--accent)"),
                cls="lp-footer",
            ),
        ),
    )
