"""Unit test cho crawler — CHẠY OFFLINE (không gọi mạng).

Dùng fixture HTML nhúng JSON-LD; monkeypatch http_get để test map JSON-LD → job.schema
và các quy tắc lọc (hết hạn / tin cũ ≥ 30 ngày / không có adapter).
"""

import json
import sys
import unittest
from datetime import date
from pathlib import Path

CRAWLERS = Path(__file__).resolve().parents[1] / "crawlers"
sys.path.insert(0, str(CRAWLERS))

import base  # noqa: E402
import itviec  # noqa: E402


def _jd_html(date_posted="2026-09-01", valid_through="2026-10-09"):
    ld = {
        "@context": "https://schema.org",
        "@type": "JobPosting",
        "title": "Senior Python Developer",
        "datePosted": date_posted,
        "validThrough": valid_through,
        "employmentType": "FULL_TIME",
        "hiringOrganization": {"@type": "Organization", "name": "ACME Vietnam"},
        "jobLocation": [{"@type": "Place", "address": {
            "@type": "PostalAddress", "addressLocality": "Quận 1",
            "addressCountry": "VN"}}],
        "baseSalary": {"@type": "MonetaryAmount", "currency": "USD", "value": {
            "@type": "QuantitativeValue", "minValue": 2000, "maxValue": 3000,
            "unitText": "MONTH"}},
        "skills": ["Python", "FastAPI", "Python", "SQL"],
        "industry": "Information Technology",
        "experienceRequirements": {"@type": "OccupationalExperienceRequirements",
                                   "monthsOfExperience": 36},
        "description": "<p>" + " ".join(f"word{i}" for i in range(120)) + "</p>",
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head><body></body></html>'


class BaseHelperTests(unittest.TestCase):
    def test_find_jobposting_and_map(self):
        jp = base.find_jobposting(_jd_html())
        self.assertIsNotNone(jp)
        self.assertEqual(base.employment_type(jp["employmentType"]), "full-time")
        sal = base.salary_from_ld(jp["baseSalary"])
        self.assertEqual((sal["min"], sal["max"], sal["currency"], sal["period"]),
                         (2000.0, 3000.0, "USD", "month"))
        self.assertEqual(base.location_from_ld(jp["jobLocation"]), "Quận 1, VN")
        self.assertEqual(base.clean_skills(jp["skills"]), ["Python", "FastAPI", "SQL"])

    def test_truncate_words_caps_at_60(self):
        out = base.truncate_words(" ".join(f"w{i}" for i in range(120)), 60)
        self.assertLessEqual(len(out.split()), 61)  # 60 từ + ký tự "…"
        self.assertTrue(out.endswith("…"))

    def test_days_since_and_expired(self):
        today = date(2026, 9, 4)
        self.assertEqual(base.days_since("2026-08-05", today), 30)
        self.assertTrue(base.is_expired("2026-09-01", today))
        self.assertFalse(base.is_expired("2026-10-01", today))
        self.assertIsNone(base.days_since("unknown", today))

    def test_missing_fields_are_not_fabricated(self):
        sal = base.salary_from_ld(None)
        self.assertEqual(sal["currency"], "unknown")
        self.assertNotIn("min", sal)
        self.assertEqual(base.location_from_ld(None), "unknown")


class ItviecFetchTests(unittest.TestCase):
    def setUp(self):
        self._orig = itviec.http_get

    def tearDown(self):
        itviec.http_get = self._orig

    def test_fetch_one_maps_to_schema(self):
        itviec.http_get = lambda url, **kw: _jd_html()
        job = itviec.fetch_one("https://itviec.com/it-jobs/x-1", today=date(2026, 9, 4))
        self.assertEqual(job["source"], "itviec")
        self.assertEqual(job["company"], "ACME Vietnam")
        self.assertEqual(job["employment_type"], "full-time")
        self.assertEqual(job["requirements"]["min_years"], 3.0)
        self.assertIn("Python", job["requirements"]["must_have_skills"])
        self.assertLessEqual(len(job["description"].split()), 61)
        for req in ("id", "title", "company", "url", "source"):
            self.assertTrue(job[req])

    def test_expired_job_raises(self):
        itviec.http_get = lambda url, **kw: _jd_html(valid_through="2026-09-01")
        with self.assertRaises(base.FetchError):
            itviec.fetch_one("https://itviec.com/it-jobs/x-1", today=date(2026, 9, 4))

    def test_stale_job_raises(self):
        itviec.http_get = lambda url, **kw: _jd_html(date_posted="2026-07-01")
        with self.assertRaises(base.FetchError):
            itviec.fetch_one("https://itviec.com/it-jobs/x-1", today=date(2026, 9, 4))

    def test_no_jobposting_raises(self):
        itviec.http_get = lambda url, **kw: "<html><body>no ld</body></html>"
        with self.assertRaises(base.FetchError):
            itviec.fetch_one("https://itviec.com/it-jobs/x-1", today=date(2026, 9, 4))


class DispatcherTests(unittest.TestCase):
    def test_no_adapter_returns_none(self):
        sys.path.insert(0, str(CRAWLERS))
        import run  # noqa: E402
        self.assertIsNone(run._find_adapter("indeed.com"))
        self.assertIs(run._find_adapter("itviec.com"), itviec)
        self.assertIs(run._find_adapter("https://itviec.com/it-jobs"), itviec)


if __name__ == "__main__":
    unittest.main()
