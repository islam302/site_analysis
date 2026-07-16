"""Fixed, human-friendly explanations for every metric shown in the report.

Each metric in the PDF gets a short plain-language note (EN + AR) so a
non-technical reader understands what the number means and which direction is
"good". These are curated and deterministic — the same wording every report.
"""
from __future__ import annotations

EXPLANATIONS = {
    "en": {
        # PageSpeed scores
        "performance": "Overall page-speed score (0–100). Higher is better.",
        "accessibility": "How usable the site is for people with disabilities "
        "(0–100). Higher is better.",
        "best_practices": "How well the site follows modern web & security best "
        "practices (0–100). Higher is better.",
        "seo": "How well the page is set up for search engines (0–100). Higher is better.",
        # Core Web Vitals
        "fcp": "Time until the first text or image appears on screen. Lower is better.",
        "lcp": "Time until the largest element (usually the hero image) is shown. "
        "Lower is better — aim for under 2.5s.",
        "tbt": "Total time the page can't respond to taps/clicks while loading. "
        "Lower is better.",
        "cls": "How much the layout unexpectedly shifts while loading. Lower is "
        "better — aim for under 0.1.",
        "si": "How quickly the page's content visually fills in. Lower is better.",
        # GTmetrix
        "grade": "GTmetrix's overall performance grade (A is best, F is worst).",
        "structure": "How well the page is built for performance (0–100). Higher is better.",
        "fully_loaded": "Time until the page finishes loading completely. Lower is better.",
        "page_size": "Total size of everything the page downloads. Smaller is faster.",
        "requests": "Number of files the page loads. Fewer is usually faster.",
        # WAVE accessibility
        "wcag": "The site's estimated WCAG accessibility conformance level.",
        "errors": "Accessibility errors that block some users. Lower is better — aim for 0.",
        "contrast": "Text with too little colour contrast against its background. "
        "Lower is better.",
        "alerts": "Possible accessibility problems worth reviewing.",
        "features": "Accessibility-friendly elements found on the page (positive).",
        "structural": "Structural elements (headings, lists) that organise the content.",
        # SSL / TLS
        "ssl_protocols": "Encryption protocols the server supports. TLS 1.2 and 1.3 "
        "are the safe ones.",
        "ssl_cert_expiry": "Days left before the security certificate expires. Renew "
        "before it does.",
        "ssl_trusted": "Whether browsers trust the site's certificate.",
        "ssl_vulns": "Known weaknesses in the encryption setup. There should be none.",
        # Broken links
        "links_total": "Number of links checked on the page.",
        "links_healthy": "Links that work correctly.",
        "links_broken": "Links that return an error. These should be fixed.",
        "links_redirects": "Links that forward to another address.",
        "links_timeouts": "Links that didn't respond in time.",
        # Structured data
        "sd_total": "Number of structured-data (Schema.org) objects found on the page.",
        "sd_valid": "Objects that are valid and match Schema.org rules.",
        "sd_rich": "Objects eligible to appear as rich results in Google.",
        "sd_errors": "Structured-data errors that block rich results. Fix these.",
        "sd_warnings": "Structured-data warnings worth addressing.",
        "sd_formats": "Which structured-data formats were detected on the page.",
    },
    "ar": {
        # PageSpeed scores
        "performance": "التقييم الإجمالي لسرعة أداء الصفحة (0–100). كلما زاد كان أفضل.",
        "accessibility": "مدى سهولة استخدام الموقع لذوي الاحتياجات الخاصة (0–100). "
        "كلما زاد كان أفضل.",
        "best_practices": "مدى اتباع الموقع لأفضل ممارسات الويب والأمان (0–100). "
        "كلما زاد كان أفضل.",
        "seo": "مدى تهيئة الصفحة لمحركات البحث (0–100). كلما زاد كان أفضل.",
        # Core Web Vitals
        "fcp": "الوقت حتى ظهور أول عنصر مرئي (نص أو صورة) على الشاشة. كلما قل كان أفضل.",
        "lcp": "الوقت حتى ظهور أكبر عنصر مرئي (غالباً صورة الواجهة). كلما قل كان أفضل — "
        "يُفضّل أقل من 2.5 ثانية.",
        "tbt": "إجمالي الوقت الذي لا تستطيع فيه الصفحة الاستجابة للنقر أثناء التحميل. "
        "كلما قل كان أفضل.",
        "cls": "مقدار تحرّك عناصر الصفحة بشكل مفاجئ أثناء التحميل. كلما قل كان أفضل، "
        "والأفضل أن يكون أقل من 0.1 نقطة.",
        "si": "مدى سرعة ظهور محتوى الصفحة بصرياً أثناء التحميل. كلما قل كان أفضل.",
        # GTmetrix
        "grade": "التقييم الإجمالي لأداء الصفحة من GTmetrix (A الأفضل و F الأسوأ).",
        "structure": "مدى جودة بناء الصفحة من ناحية الأداء (0–100). كلما زاد كان أفضل.",
        "fully_loaded": "الوقت حتى اكتمال تحميل الصفحة بالكامل. كلما قل كان أفضل.",
        "page_size": "الحجم الكلي لكل ما تحمّله الصفحة. كلما قل كان أسرع.",
        "requests": "عدد الملفات التي تحمّلها الصفحة. كلما قل كان أسرع غالباً.",
        # WAVE accessibility
        "wcag": "المستوى التقديري لمطابقة الموقع لمعايير الوصول WCAG.",
        "errors": "أخطاء الوصول التي تعيق بعض المستخدمين. كلما قل كان أفضل — يُفضّل صفر.",
        "contrast": "نصوص تباينها اللوني مع الخلفية ضعيف. كلما قل كان أفضل.",
        "alerts": "مشاكل وصول محتملة تستحق المراجعة.",
        "features": "عناصر تدعم الوصول موجودة في الصفحة (إيجابية).",
        "structural": "عناصر البنية (عناوين، قوائم) التي تنظّم المحتوى.",
        # SSL / TLS
        "ssl_protocols": "بروتوكولات التشفير التي يدعمها الخادم. والآمن منها إصدارا "
        "TLS 1.2 و1.3 فقط.",
        "ssl_cert_expiry": "الأيام المتبقية قبل انتهاء شهادة الأمان. جدّدها قبل انتهائها.",
        "ssl_trusted": "هل تثق المتصفحات بشهادة الموقع.",
        "ssl_vulns": "ثغرات معروفة في إعداد التشفير. يجب ألا توجد أي ثغرة.",
        # Broken links
        "links_total": "عدد الروابط التي تم فحصها في الصفحة.",
        "links_healthy": "الروابط التي تعمل بشكل سليم.",
        "links_broken": "الروابط التي تُرجع خطأ. يجب إصلاحها.",
        "links_redirects": "الروابط التي تحوّل إلى عنوان آخر.",
        "links_timeouts": "الروابط التي لم تستجب في الوقت المحدد.",
        # Structured data
        "sd_total": "عدد مخططات البيانات المنظمة (Schema.org) الموجودة في الصفحة.",
        "sd_valid": "المخططات الصحيحة والمطابقة لمعايير Schema.org.",
        "sd_rich": "المخططات المؤهلة للظهور كنتائج غنية في جوجل.",
        "sd_errors": "أخطاء في البيانات المنظمة تمنع النتائج الغنية. يجب إصلاحها.",
        "sd_warnings": "تحذيرات في البيانات المنظمة يُفضّل معالجتها.",
        "sd_formats": "صيغ البيانات المنظمة التي تم اكتشافها في الصفحة.",
    },
}


def get_explanations(lang: str) -> dict:
    return EXPLANATIONS["ar" if lang == "ar" else "en"]
