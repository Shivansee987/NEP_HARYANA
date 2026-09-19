"""
Unit Tests for College Double-Counting Protection (Section 24)
Verifies:
- Entity reuse across parameters/subcriteria is prevented:
  - Startup reuse
  - MoU reuse
  - Patent reuse
  - Internship / student activity reuse
  - Outreach / community activity reuse
- Proves raw inputs cannot bypass entity-key protections
"""
from datetime import date
from django.test import TestCase

from apps.scoring.domain import (
    AssessmentContext,
    AssessmentPeriod,
    AssetEntity,
    EvidenceDocument,
)
from apps.scoring.enums import (
    DoubleCountingRule,
    EvidenceState,
    FrameworkType,
    InstitutionType,
)
from apps.scoring.evaluators.double_counting import DoubleCountingValidator


class CollegeDoubleCountingTests(TestCase):

    def setUp(self):
        self.context = AssessmentContext(
            assessment_id="ASSESS-2026-COL-DC-001",
            institution_id="C-54321",
            institution_type=InstitutionType.COLLEGE,
            framework=FrameworkType.COLLEGE_2026,
            assessment_period=AssessmentPeriod(start_date=date(2025, 7, 1), end_date=date(2026, 6, 30)),
        )
        self.validator = DoubleCountingValidator()

    def test_startup_reuse_detected_by_validator(self):
        """Entity-key reuse for a startup entity is flagged as double-counting."""
        startup_entity = AssetEntity(
            entity_id="startup-001",
            entity_type="STARTUP",
            identifier_key="CIN-U72200HR2025PTC001",
            title="Karnal AgriTech Ventures",
        )

        # Register startup for C11.I
        valid, rejected, trace = self.validator.validate_entities(
            subcriterion_code="C11.I",
            entities=[startup_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(rejected), 0)

        # Attempt to reuse same startup CIN in another subcriterion/parameter
        valid2, rejected2, trace2 = self.validator.validate_entities(
            subcriterion_code="C11.II.b",
            entities=[startup_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid2), 0)
        self.assertEqual(len(rejected2), 1)
        self.assertEqual(rejected2[0].identifier_key, "CIN-U72200HR2025PTC001")
        self.assertEqual(len(trace2["duplicates_detected"]), 1)
        self.assertEqual(trace2["duplicates_detected"][0]["first_claimed_by"], "C11.I")

    def test_mou_reuse_detected_by_validator(self):
        """Entity-key reuse for an MoU entity is flagged as double-counting."""
        mou_entity = AssetEntity(
            entity_id="mou-101",
            entity_type="MOU",
            identifier_key="MOU-TCS-2025-001",
            title="TCS Industry Collaboration",
        )

        valid1, rejected1, _ = self.validator.validate_entities(
            subcriterion_code="C10.1",
            entities=[mou_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid1), 1)
        self.assertEqual(len(rejected1), 0)

        # Attempt to reuse the same MoU under C12.3
        valid2, rejected2, trace2 = self.validator.validate_entities(
            subcriterion_code="C12.3",
            entities=[mou_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid2), 0)
        self.assertEqual(len(rejected2), 1)
        self.assertEqual(trace2["duplicates_detected"][0]["first_claimed_by"], "C10.1")

    def test_patent_reuse_detected(self):
        """Patent application number cannot be claimed under both C19.I and C19.II if forbidden."""
        patent_entity = AssetEntity(
            entity_id="patent-01",
            entity_type="PATENT",
            identifier_key="PATENT-IN-2025-410023",
            title="IoT Sensor for Soil",
        )

        valid1, rejected1, _ = self.validator.validate_entities(
            subcriterion_code="C19.I",
            entities=[patent_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid1), 1)
        self.assertEqual(len(rejected1), 0)

        valid2, rejected2, trace2 = self.validator.validate_entities(
            subcriterion_code="C19.II",
            entities=[patent_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid2), 0)
        self.assertEqual(len(rejected2), 1)
        self.assertEqual(trace2["duplicates_detected"][0]["first_claimed_by"], "C19.I")

    def test_outreach_activity_reuse_detected(self):
        """Outreach activity cannot be reused in green campus/SDG criteria."""
        event_entity = AssetEntity(
            entity_id="event-01",
            entity_type="ACTIVITY",
            identifier_key="OUTREACH-SWACHHTA-2025-09",
            title="Cleanliness Drive",
        )

        valid1, rejected1, _ = self.validator.validate_entities(
            subcriterion_code="C17.1",
            entities=[event_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid1), 1)
        self.assertEqual(len(rejected1), 0)

        valid2, rejected2, trace2 = self.validator.validate_entities(
            subcriterion_code="C18.1",
            entities=[event_entity],
            rule=DoubleCountingRule.FORBIDDEN_REUSE,
        )
        self.assertEqual(len(valid2), 0)
        self.assertEqual(len(rejected2), 1)

    def test_raw_scalar_inputs_extract_entities_for_protection(self):
        """Proves raw scalar inputs with identifier keys are extracted to enforce entity protection."""
        raw = {"mou_id": "MOU-INFOSYS-2025-01", "other_field": 123}
        entities = DoubleCountingValidator.extract_entities_from_raw_inputs("C10.1", raw)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0].identifier_key, "MOU-INFOSYS-2025-01")
        self.assertEqual(entities[0].entity_type, "MOU")

        # Second extraction with same identifier key produces identical canonical identity
        raw2 = {"identifier_key": "MOU-INFOSYS-2025-01", "entity_type": "MOU"}
        entities2 = DoubleCountingValidator.extract_entities_from_raw_inputs("C12.3", raw2)
        self.assertEqual(len(entities2), 1)

        # Validator flags collision between the two extractions
        v1, r1, _ = self.validator.validate_entities("C10.1", entities, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v1), 1)

        v2, r2, _ = self.validator.validate_entities("C12.3", entities2, DoubleCountingRule.FORBIDDEN_REUSE)
        self.assertEqual(len(v2), 0)
        self.assertEqual(len(r2), 1)
