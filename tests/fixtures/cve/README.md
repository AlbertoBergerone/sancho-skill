# CVE enrichment fixtures

`responses/` contains hand-written API responses with the same **shape** as OSV.dev,
NVD API 2.0, the CISA KEV feed and FIRST EPSS. Identifiers (GHSA/CVE ids) refer to real,
well-known advisories, but scores and dates are **illustrative** and trimmed: do not use
them as vulnerability data. They exist so that `cve_enrich.py --replay` can be tested
offline and deterministically.

To refresh them with real data on a machine with network access:

    python skills/sancho/scripts/cve_enrich.py tests/fixtures/cve/inputs/package-lock.json \
      tests/fixtures/cve/inputs/requirements.txt tests/fixtures/cve/inputs/sbom.cdx.json \
      --record tests/fixtures/cve/responses --out /tmp/report.json

(then update the expected values in tests/validate.py).
