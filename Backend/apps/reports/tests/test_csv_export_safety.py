"""
S-18 (security review 2026-10-21): text cells in the CSV export cannot start a spreadsheet formula, and quoting is
always correct, whatever the institution or parameter text contains.
"""
import csv
import io
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.reports.services import ReportingService


def _report(name, title, reasons):
    return {
        "assessment": {"assessment_id": "ASSESS-1"},
        "framework": "COLLEGE_2026",
        "institution": {"name": name, "aishe_code": "C-1"},
        "period": {"academic_year": "2025-26"},
        "lifecycle": {"status": "SUBMITTED"},
        "scoring": {"scoring_status": "PROVISIONAL", "final_certified_total": None},
        "parameters": [{
            "parameter_code": "C1", "parameter_title": title, "max_marks": 5, "submitted": True,
            "final_score": None, "raw_score": 2, "evidence_coverage_state": "COMPLETE",
            "resolution_status": "CALCULABLE", "blocking_reasons": reasons,
        }],
    }


class CsvExportSafetyTests(SimpleTestCase):
    def _rows(self, report):
        with patch.object(ReportingService, 'get_assessment_report', return_value=report):
            data = ReportingService.export_csv("ASSESS-1", user=None)
        return list(csv.reader(io.StringIO(data)))

    def test_formula_prefixes_are_neutralised(self):
        rows = self._rows(_report('=HYPERLINK("http://evil.example","Open")', "+SUM(1,2)", ["@cmd", "-2+3"]))
        header, row = rows[0], rows[1]
        cells = dict(zip(header, row))
        self.assertEqual(cells["Institution Name"], "'=HYPERLINK(\"http://evil.example\",\"Open\")")
        self.assertEqual(cells["Parameter Title"], "'+SUM(1,2)")
        self.assertTrue(cells["Blocking Reasons"].startswith("'@cmd"))

    def test_commas_quotes_and_newlines_stay_in_one_cell(self):
        rows = self._rows(_report('Govt College, "Model"\nSector 14', "Title", []))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), len(rows[0]))
        self.assertEqual(dict(zip(rows[0], rows[1]))["Institution Name"], 'Govt College, "Model"\nSector 14')
