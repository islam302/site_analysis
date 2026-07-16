"""Turn a combined report's findings into actionable recommendations (EN/AR).

A small rules engine: each tool's result is checked against thresholds and a
prioritised, localised list of "how to improve / what to fix" items is produced.
"""
from __future__ import annotations

REC = {
    "en": {
        "intro": "As a software company, here is how we can improve the experience "
        "and fix the issues found:",
        "perf_poor": "Performance is poor ({score}/100): enable gzip/brotli "
        "compression, remove unused CSS/JS, and serve assets via a CDN.",
        "perf_mid": "Improve performance ({score}/100): defer non-critical "
        "JavaScript and optimise/compress images.",
        "lcp": "Largest Contentful Paint is slow ({v}s): preload the hero image "
        "and cut render-blocking resources.",
        "tbt": "Reduce Total Blocking Time ({v}ms): split long JavaScript tasks "
        "and defer third-party scripts.",
        "cls": "Reduce layout shift (CLS {v}): set explicit width/height on "
        "images, ads, and embeds.",
        "seo": "Improve SEO ({score}/100): add meta descriptions, descriptive "
        "titles, and structured data.",
        "bp": "Follow best practices ({score}/100): serve every resource over "
        "HTTPS and update outdated libraries.",
        "a11y_errors": "Fix {n} accessibility error(s) to reach WCAG compliance "
        "(missing labels, alt text, etc.).",
        "a11y_contrast": "Fix {n} colour-contrast issue(s): use a contrast ratio "
        "of at least 4.5:1 for text.",
        "ssl_grade": "Harden SSL/TLS: disable the old TLS 1.0/1.1 protocols and "
        "keep only TLS 1.2/1.3 (current grade {grade}).",
        "ssl_expiry": "Renew the SSL certificate — it expires in {n} days.",
        "ssl_vuln": "Address the detected SSL vulnerabilities immediately: {vulns}.",
        "links": "Fix {n} broken link(s) — they hurt user experience and SEO.",
        "sd_missing": "Add structured data (Schema.org / JSON-LD): none was found. "
        "It unlocks rich results (ratings, FAQs, breadcrumbs) in Google.",
        "sd_errors": "Fix {n} structured-data error(s) so search engines can parse "
        "your Schema.org markup correctly.",
        "sd_rich": "Complete your structured data: no schema is rich-result "
        "eligible yet. Add the fields Google requires (e.g. image, offers, author).",
        "all_good": "The site is in great shape. Keep monitoring performance, "
        "accessibility, security, links, and structured data regularly.",
    },
    "ar": {
        "intro": "كشركة برمجيات، إليك كيف يمكننا تحسين التجربة وإصلاح المشاكل المكتشفة:",
        "perf_poor": "الأداء ضعيف ({score}/100): فعّل ضغط gzip/brotli، واحذف ملفات "
        "CSS/JS غير المستخدمة، واستخدم شبكة CDN.",
        "perf_mid": "حسّن الأداء ({score}/100): أجّل تحميل الـ JavaScript غير الضروري "
        "وحسّن واضغط الصور.",
        "lcp": "أكبر رسم للمحتوى بطيء ({v} ثانية): حمّل صورة الواجهة مسبقاً (preload) "
        "وقلّل الموارد المعطّلة للعرض.",
        "tbt": "قلّل إجمالي وقت الحجب ({v} مللي ثانية): قسّم مهام الـ JavaScript الطويلة "
        "وأجّل السكربتات الخارجية.",
        "cls": "قلّل إزاحة التخطيط (CLS {v}): حدّد الأبعاد (width/height) للصور والإعلانات.",
        "seo": "حسّن الـ SEO ({score}/100): أضف وصفاً (meta description) وعناوين واضحة "
        "وبيانات منظّمة (structured data).",
        "bp": "اتبع أفضل الممارسات ({score}/100): قدّم كل الموارد عبر HTTPS وحدّث "
        "المكتبات القديمة.",
        "a11y_errors": "أصلح {n} خطأ في إمكانية الوصول لتحقيق مطابقة WCAG "
        "(عناوين ونصوص بديلة مفقودة، إلخ).",
        "a11y_contrast": "أصلح {n} مشكلة تباين لوني: استخدم نسبة تباين 4.5:1 على الأقل "
        "للنصوص.",
        "ssl_grade": "عزّز أمان SSL/TLS: عطّل بروتوكولات TLS 1.0/1.1 القديمة وأبقِ "
        "TLS 1.2/1.3 فقط (التقييم الحالي {grade}).",
        "ssl_expiry": "جدّد شهادة SSL — تنتهي خلال {n} يوم.",
        "ssl_vuln": "عالج ثغرات SSL المكتشفة فوراً: {vulns}.",
        "links": "أصلح {n} رابط مكسور — تؤثر سلباً على تجربة المستخدم و SEO.",
        "sd_missing": "أضف بيانات منظمة (Schema.org / JSON-LD): لم يتم العثور على أي منها. "
        "فهي تتيح النتائج الغنية (التقييمات، الأسئلة الشائعة، مسار التنقل) في جوجل.",
        "sd_errors": "أصلح {n} خطأ في البيانات المنظمة حتى تتمكن محركات البحث من قراءة "
        "ترميز Schema.org بشكل صحيح.",
        "sd_rich": "أكمل بياناتك المنظمة: لا يوجد مخطط مؤهل للنتائج الغنية بعد. أضف الحقول "
        "التي يطلبها جوجل (مثل الصورة، العروض، المؤلف).",
        "all_good": "الموقع في حالة ممتازة! استمر في المتابعة الدورية للأداء وإمكانية "
        "الوصول والأمان والروابط والبيانات المنظمة.",
    },
}


def build_recommendations(report: dict, lang: str = "en") -> list[str]:
    """Return an ordered, localised list of recommendation strings."""
    tr = REC["ar" if lang == "ar" else "en"]
    recs: list[str] = []

    ps = report.get("pagespeed", {})
    if ps.get("status") == "ok":
        d = ps["data"]
        perf = d.get("performance_score")
        if perf is not None and perf < 50:
            recs.append(tr["perf_poor"].format(score=perf))
        elif perf is not None and perf < 90:
            recs.append(tr["perf_mid"].format(score=perf))
        lcp = d.get("largest_contentful_paint")
        if lcp and lcp > 2.5:
            recs.append(tr["lcp"].format(v=lcp))
        tbt = d.get("total_blocking_time")
        if tbt and tbt > 200:
            recs.append(tr["tbt"].format(v=tbt))
        cls = d.get("cumulative_layout_shift")
        if cls and cls > 0.1:
            recs.append(tr["cls"].format(v=cls))
        seo = d.get("seo_score")
        if seo is not None and seo < 90:
            recs.append(tr["seo"].format(score=seo))
        bp = d.get("best_practices_score")
        if bp is not None and bp < 90:
            recs.append(tr["bp"].format(score=bp))

    wave = report.get("accessibility", {})
    if wave.get("status") == "ok":
        d = wave["data"]
        if d.get("total_errors", 0) > 0:
            recs.append(tr["a11y_errors"].format(n=d["total_errors"]))
        if d.get("total_contrast_errors", 0) > 0:
            recs.append(tr["a11y_contrast"].format(n=d["total_contrast_errors"]))

    ssl = report.get("ssl", {})
    if ssl.get("status") == "ok":
        d = ssl["data"]
        grade = (d.get("grade") or "").upper()
        if grade and grade not in ("A+", "A"):
            recs.append(tr["ssl_grade"].format(grade=d.get("grade")))
        expires = d.get("cert_expires_in_days")
        if expires is not None and expires < 30:
            recs.append(tr["ssl_expiry"].format(n=expires))
        vulns = [k for k, v in (d.get("vulnerabilities") or {}).items() if v]
        if vulns:
            recs.append(tr["ssl_vuln"].format(vulns=", ".join(vulns)))

    links = report.get("links", {})
    if links.get("status") == "ok":
        broken = links["data"].get("broken", 0)
        if broken > 0:
            recs.append(tr["links"].format(n=broken))

    sd = report.get("structured_data", {})
    if sd.get("status") == "ok":
        d = sd["data"]
        if d.get("total_schemas", 0) == 0:
            recs.append(tr["sd_missing"])
        else:
            if d.get("total_errors", 0) > 0:
                recs.append(tr["sd_errors"].format(n=d["total_errors"]))
            if d.get("rich_result_eligible", 0) == 0:
                recs.append(tr["sd_rich"])

    if not recs:
        recs.append(tr["all_good"])
    return recs


def recommendations_intro(lang: str = "en") -> str:
    return REC["ar" if lang == "ar" else "en"]["intro"]
