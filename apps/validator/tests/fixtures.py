"""Realistic HTML fixtures for validator tests.

Each constant is a small but valid HTML document exercising a particular
structured-data shape or edge case.
"""

# A clean, fully-valid Organization (JSON-LD).
ORG_VALID = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Acme Corp",
  "url": "https://acme.example",
  "logo": "https://acme.example/logo.png",
  "contactPoint": {"@type": "ContactPoint", "telephone": "+1-800-555-0100"}
}
</script></head><body><h1>Acme</h1></body></html>
"""

# Product missing the required "image" and recommended "offers".
PRODUCT_MISSING_IMAGE = """
<!doctype html><html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Product", "name": "Widget"}
</script></head><body></body></html>
"""

# Product with offers but the offer lacks price/priceCurrency (warnings).
PRODUCT_INCOMPLETE_OFFER = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Gadget",
  "image": "https://shop.example/gadget.jpg",
  "offers": {"@type": "Offer", "availability": "https://schema.org/InStock"}
}
</script></head><body></body></html>
"""

# Article with a wrong-typed datePublished (a bare year, not ISO).
ARTICLE_BAD_DATE = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "Big News",
  "author": {"@type": "Person", "name": "Jane Doe"},
  "datePublished": "last tuesday",
  "image": "https://news.example/a.jpg"
}
</script></head><body></body></html>
"""

# BreadcrumbList where the second item is missing "item".
BREADCRUMB_MISSING_ITEM = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://x.example/"},
    {"@type": "ListItem", "position": 2, "name": "Blog"}
  ]
}
</script></head><body></body></html>
"""

# FAQPage where one Question has no acceptedAnswer.text.
FAQ_MISSING_ANSWER = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {"@type": "Question", "name": "What is it?",
     "acceptedAnswer": {"@type": "Answer", "text": "A thing."}},
    {"@type": "Question", "name": "How much?",
     "acceptedAnswer": {"@type": "Answer"}}
  ]
}
</script></head><body></body></html>
"""

# Two objects in one @graph (Organization + WebSite).
GRAPH_MULTIPLE = """
<!doctype html><html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Organization", "name": "Graph Co", "url": "https://graph.example",
     "logo": "https://graph.example/l.png"},
    {"@type": "WebSite", "name": "Graph Site", "url": "https://graph.example"}
  ]
}
</script></head><body></body></html>
"""

# A JSON-LD array (two products) in a single script tag.
JSON_LD_ARRAY = """
<!doctype html><html><head>
<script type="application/ld+json">
[
  {"@type": "Product", "name": "A", "image": "https://s.example/a.jpg"},
  {"@type": "Product", "name": "B", "image": "https://s.example/b.jpg"}
]
</script></head><body></body></html>
"""

# Malformed JSON-LD (trailing comma / missing brace).
MALFORMED_JSON_LD = """
<!doctype html><html><head>
<script type="application/ld+json">
{"@type": "Organization", "name": "Broken", "url": "https://b.example",}
</script></head><body></body></html>
"""

# JSON-LD object with no @type at all.
NO_TYPE = """
<!doctype html><html><head>
<script type="application/ld+json">
{"@context": "https://schema.org", "name": "Typeless"}
</script></head><body></body></html>
"""

# Microdata Product (nested Offer).
MICRODATA_PRODUCT = """
<!doctype html><html><body>
<div itemscope itemtype="https://schema.org/Product">
  <span itemprop="name">Micro Widget</span>
  <img itemprop="image" src="https://m.example/w.jpg">
  <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
    <span itemprop="price">19.99</span>
    <meta itemprop="priceCurrency" content="USD">
    <link itemprop="availability" href="https://schema.org/InStock">
  </div>
</div>
</body></html>
"""

# RDFa LocalBusiness missing telephone.
RDFA_LOCALBUSINESS = """
<!doctype html><html><body vocab="https://schema.org/">
<div typeof="LocalBusiness">
  <span property="name">Corner Cafe</span>
  <span property="address">123 Main St</span>
</div>
</body></html>
"""

# A page with no structured data at all.
NO_STRUCTURED_DATA = """
<!doctype html><html><head><title>Plain</title></head>
<body><p>Nothing to see here.</p></body></html>
"""
