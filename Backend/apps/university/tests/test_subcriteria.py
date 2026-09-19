"""Category B Tests: University Multi-Subcriterion Parameters.

Verifies:
- U4 IDP targets: U4.A (3m), U4.B (3m)
- U5 Placement: U5.A (2m), U5.B (2m)
- U6 Academic reforms: U6.A (4m), U6.B (4m)
- U7 PoP engagement: U7.1 to U7.4 (1m each)
- U8 Incubation/Startups: U8.A (4m), U8.B (2m)
- U9 Foreign HEI: U9.A (1m), U9.B (5m)
- U10 Alumni connect: U10.1 (1m), U10.2 (1m), U10.3 (2m), U10.4 (1m)
- U11 Gender parity: U11.1 to U11.4 (1m each)
- U12 Physical fitness: U12.1 to U12.5 (1m each)
- U13 MOOCs: U13.1 (6m)
- U14 Multidisciplinary: U14.A (4m), U14.B (1m), U14.C (1m)
- U15 Multiple entry-exit: U15.1 (1m), U15.2 (1m)
- U16 Research patents: U16.I (2m), U16.II (2m), U16.III (4m unresolved)
- U17 NIRF: U17.1 (1m), U17.2 (1m)
- U18 RPL: U18.1 (1m), U18.2 (1m), U18.3 (2m)
- U19 OBE: U19.A (6m), U19.B (2m)
- U20 SDGs: U20.1 (2m), U20.2 (2m), U20.3 (1m) (inconsistency preserved)
"""

from decimal import Decimal
from django.test import SimpleTestCase

from apps.university.registry import get_university_parameter
from apps.scoring.rules.definitions import UNIVERSITY_PARAMETERS


class UniversityMultiSubcriterionTests(SimpleTestCase):
    """Test all multi-subcriterion parameters and their exact weights."""

    def test_u4_idp_subcriteria(self):
        p = get_university_parameter("U4")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("6.0"))
        sub_codes = list(p["subcriteria"].keys())
        self.assertIn("U4.A", sub_codes)
        self.assertIn("U4.B", sub_codes)

    def test_u5_placement_subcriteria(self):
        p = get_university_parameter("U5")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("4.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U5.A"], Decimal("2.0"))
        self.assertEqual(sub_dict["U5.B"], Decimal("2.0"))

    def test_u6_academic_reforms_subcriteria(self):
        p = get_university_parameter("U6")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("8.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U6.A"], Decimal("4.0"))
        self.assertEqual(sub_dict["U6.B"], Decimal("4.0"))

    def test_u7_pop_engagement_subcriteria(self):
        p = get_university_parameter("U7")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("4.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        for code in ["U7.1", "U7.2", "U7.3", "U7.4"]:
            self.assertEqual(sub_dict[code], Decimal("1.0"))

    def test_u8_incubation_subcriteria(self):
        p = get_university_parameter("U8")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("6.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U8.A"], Decimal("4.0"))
        self.assertEqual(sub_dict["U8.B"], Decimal("2.0"))

    def test_u9_foreign_collaboration_subcriteria(self):
        p = get_university_parameter("U9")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("6.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U9.A"], Decimal("1.0"))
        self.assertEqual(sub_dict["U9.B"], Decimal("5.0"))

    def test_u10_alumni_connect_subcriteria(self):
        p = get_university_parameter("U10")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("5.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U10.1"], Decimal("1.0"))
        self.assertEqual(sub_dict["U10.2"], Decimal("1.0"))
        self.assertEqual(sub_dict["U10.3"], Decimal("2.0"))
        self.assertEqual(sub_dict["U10.4"], Decimal("1.0"))

    def test_u11_gender_parity_subcriteria(self):
        p = get_university_parameter("U11")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("4.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        for code in ["U11.1", "U11.2", "U11.3", "U11.4"]:
            self.assertEqual(sub_dict[code], Decimal("1.0"))

    def test_u12_wellbeing_subcriteria(self):
        p = get_university_parameter("U12")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("5.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        for code in ["U12.1", "U12.2", "U12.3", "U12.4", "U12.5"]:
            self.assertEqual(sub_dict[code], Decimal("1.0"))

    def test_u14_multidisciplinary_subcriteria(self):
        p = get_university_parameter("U14")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("6.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U14.A"], Decimal("4.0"))
        self.assertEqual(sub_dict["U14.B"], Decimal("1.0"))
        self.assertEqual(sub_dict["U14.C"], Decimal("1.0"))

    def test_u15_multiple_entry_exit_subcriteria(self):
        p = get_university_parameter("U15")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("2.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U15.1"], Decimal("1.0"))
        self.assertEqual(sub_dict["U15.2"], Decimal("1.0"))

    def test_u16_patents_and_unresolved_scopus(self):
        p = get_university_parameter("U16")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("8.0"))
        raw_u16 = UNIVERSITY_PARAMETERS["U16"]
        self.assertEqual(raw_u16["subcriteria"]["U16.I"]["max_score"], 2.0)
        self.assertEqual(raw_u16["subcriteria"]["U16.II"]["max_score"], 2.0)
        self.assertEqual(raw_u16["subcriteria"]["U16.III"]["max_score"], 4.0)
        self.assertEqual(raw_u16["subcriteria"]["U16.III"]["resolution_status"], "UNRESOLVED_RULE")

    def test_u17_nirf_subcriteria(self):
        p = get_university_parameter("U17")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("2.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U17.1"], Decimal("1.0"))
        self.assertEqual(sub_dict["U17.2"], Decimal("1.0"))

    def test_u18_rpl_subcriteria(self):
        p = get_university_parameter("U18")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("4.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U18.1"], Decimal("1.0"))
        self.assertEqual(sub_dict["U18.2"], Decimal("1.0"))
        self.assertEqual(sub_dict["U18.3"], Decimal("2.0"))

    def test_u19_obe_subcriteria(self):
        p = get_university_parameter("U19")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("8.0"))
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U19.A"], Decimal("6.0"))
        self.assertEqual(sub_dict["U19.B"], Decimal("2.0"))

    def test_u20_sdgs_source_inconsistency_preserved(self):
        p = get_university_parameter("U20")
        self.assertEqual(Decimal(str(p["max_marks"])), Decimal("4.0"))
        raw_u20 = UNIVERSITY_PARAMETERS["U20"]
        self.assertEqual(raw_u20["resolution_status"], "SOURCE_INCONSISTENCY")
        sub_dict = {k: Decimal(str(v["max_score"])) for k, v in p["subcriteria"].items()}
        self.assertEqual(sub_dict["U20.1"], Decimal("2.0"))
        self.assertEqual(sub_dict["U20.2"], Decimal("2.0"))
        self.assertEqual(sub_dict["U20.3"], Decimal("1.0"))
        self.assertEqual(sum(sub_dict.values()), Decimal("5.0"))
