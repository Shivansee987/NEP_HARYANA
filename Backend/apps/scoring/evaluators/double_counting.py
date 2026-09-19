"""
NEP Excellence Awards 2026 - Double-Counting & Asset Reuse Evaluator
Distinguishes document-level reuse from underlying real-world activity/entity duplication.
"""
from typing import Any, Dict, List, Optional, Set, Tuple

from apps.scoring.domain import AssetEntity, EvidenceDocument
from apps.scoring.enums import DoubleCountingRule


class DoubleCountingValidator:
    """
    Stateful validator tracking entities and evidence documents across an entire assessment evaluation pass.
    """
    def __init__(self):
        # Maps canonical entity key -> first subcriterion code that claimed it
        self._claimed_entities: Dict[str, str] = {}
        # Tracks document file IDs and which subcriteria referenced them
        self._referenced_documents: Dict[str, List[str]] = {}
        # Records of detected conflicts
        self.conflicts: List[Dict[str, Any]] = []

    def record_document_reference(self, doc_id: str, subcriterion_code: str) -> None:
        """
        Records document usage. Under PERMITTED_REUSE, multiple criteria may legitimately
        reference the same master documentary file (e.g. Annual Report).
        """
        self._referenced_documents.setdefault(doc_id, []).append(subcriterion_code)

    @staticmethod
    def extract_entities_from_raw_inputs(
        subcriterion_code: str,
        raw_inputs: Dict[str, Any],
        default_entity_type: Optional[str] = None
    ) -> List[AssetEntity]:
        """
        Extracts AssetEntity instances from raw scalar/dictionary inputs if underlying output
        identifiers are provided (e.g. patent_id, startup_id, entity_key, identifiers list).
        Does NOT synthesize entities for pure scalar measurements (e.g. percentages or counts without output identity).
        """
        if not raw_inputs or not isinstance(raw_inputs, dict):
            return []

        extracted: List[AssetEntity] = []
        seen_keys: Set[str] = set()

        def _infer_type(key_name: str, explicit_type: Optional[str] = None) -> str:
            if explicit_type:
                return explicit_type.upper()
            if default_entity_type:
                return default_entity_type.upper()
            k = key_name.lower()
            if "patent" in k:
                return "PATENT"
            if "startup" in k or "venture" in k:
                return "STARTUP"
            if "mou" in k:
                return "MOU"
            if "programme" in k or "program" in k or "degree" in k:
                return "PROGRAMME"
            if "activity" in k:
                return "ACTIVITY"
            return "OUTPUT"

        def _add_entity(ent_type: str, ident: str):
            ident_clean = str(ident).strip()
            if not ident_clean:
                return
            # Check if ident already includes canonical prefix TYPE::KEY
            if "::" in ident_clean:
                parts = ident_clean.split("::", 1)
                final_type = parts[0].strip().upper()
                final_ident = parts[1].strip()
            else:
                final_type = ent_type.upper()
                final_ident = ident_clean

            dedup_key = f"{final_type}::{final_ident.upper()}"
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                extracted.append(
                    AssetEntity(
                        entity_id=f"raw_{subcriterion_code}_{len(extracted)+1}",
                        entity_type=final_type,
                        identifier_key=final_ident,
                        title=f"Extracted from raw input in {subcriterion_code}"
                    )
                )

        explicit_type = raw_inputs.get("entity_type")

        # 1. Check direct entity key/keys
        for k in ["entity_key", "identifier_key", "entity_id", "patent_id", "patent_number", "startup_id", "mou_id", "programme_id", "output_id"]:
            val = raw_inputs.get(k)
            if val and isinstance(val, (str, int)):
                _add_entity(_infer_type(k, explicit_type), str(val))

        # 2. Check plural/list fields
        for k in ["entity_keys", "identifier_keys", "entities", "identifiers", "patent_ids", "patent_numbers", "patents", "startup_ids", "startups", "mou_ids", "mous", "programme_ids", "programmes", "activity_ids", "activities", "output_ids", "outputs"]:
            val = raw_inputs.get(k)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        _add_entity(_infer_type(k, explicit_type), item)
                    elif isinstance(item, dict):
                        itype = item.get("entity_type") or _infer_type(k, explicit_type)
                        ikey = item.get("identifier_key") or item.get("entity_id") or item.get("id")
                        if ikey:
                            _add_entity(itype, str(ikey))
                    elif isinstance(item, AssetEntity):
                        _add_entity(item.entity_type, item.identifier_key)

        return extracted

    def validate_entities(
        self,
        subcriterion_code: str,
        entities: List[AssetEntity],
        rule: DoubleCountingRule
    ) -> Tuple[List[AssetEntity], List[AssetEntity], Dict[str, Any]]:
        """
        Validates a list of real-world entities for a subcriterion.
        
        Returns:
            (valid_entities, duplicate_rejected_entities, trace)
        """
        trace: Dict[str, Any] = {
            "subcriterion_code": subcriterion_code,
            "rule": rule.value if isinstance(rule, DoubleCountingRule) else rule,
            "total_entities_submitted": len(entities),
            "duplicates_detected": [],
        }

        if rule == DoubleCountingRule.REQUIRES_FRAMEWORK_EXCEPTION:
            # Authorized multi-aspect reuse (e.g. U14 multidisciplinary embedding sports/industry VAC)
            trace["note"] = "Framework exception applies: entity reuse authorized."
            return entities, [], trace

        valid_entities: List[AssetEntity] = []
        rejected_entities: List[AssetEntity] = []

        for entity in entities:
            canonical_key = f"{entity.entity_type.upper()}::{entity.identifier_key.strip().upper()}"
            
            if rule == DoubleCountingRule.FORBIDDEN_REUSE:
                if canonical_key in self._claimed_entities:
                    first_claimer = self._claimed_entities[canonical_key]
                    first_param = first_claimer.split(".")[0] if "." in first_claimer else first_claimer
                    rej_param = subcriterion_code.split(".")[0] if "." in subcriterion_code else subcriterion_code
                    conflict_record = {
                        "entity_key": canonical_key,
                        "entity_id": entity.entity_id,
                        "first_claimed_by": first_claimer,
                        "rejected_in": subcriterion_code,
                        "first_claimed_parameter": first_param,
                        "affected_parameter": rej_param,
                        "reason": f"Prohibited double-counting: Entity {canonical_key} already claimed under {first_claimer}",
                        "score_consequence": "Entity rejected from subcriterion count; score adjusted based on remaining valid entities.",
                        "resulting_state": "REJECTED_DUPLICATE",
                    }
                    self.conflicts.append(conflict_record)
                    trace["duplicates_detected"].append(conflict_record)
                    rejected_entities.append(entity)
                    continue

                # Register first claim
                self._claimed_entities[canonical_key] = subcriterion_code

            valid_entities.append(entity)

        trace["valid_entities_count"] = len(valid_entities)
        trace["rejected_entities_count"] = len(rejected_entities)
        return valid_entities, rejected_entities, trace

    def validate_subcriterion_input(
        self,
        subcriterion_code: str,
        sub_input: Optional[Any],
        rule: DoubleCountingRule,
        default_entity_type: Optional[str] = None
    ) -> Tuple[List[AssetEntity], List[AssetEntity], Dict[str, Any]]:
        """
        Validates both structured AssetEntity objects and any raw scalar entity references
        submitted on sub_input, ensuring outputs cannot bypass double-counting checks.
        """
        if not sub_input:
            return [], [], {"subcriterion_code": subcriterion_code, "total_entities_submitted": 0, "duplicates_detected": []}

        all_entities: List[AssetEntity] = []
        seen_keys: Set[str] = set()

        # 1. Explicit domain AssetEntity objects
        if hasattr(sub_input, "entities") and sub_input.entities:
            for ent in sub_input.entities:
                if isinstance(ent, AssetEntity):
                    ckey = f"{ent.entity_type.upper()}::{ent.identifier_key.strip().upper()}"
                    if ckey not in seen_keys:
                        seen_keys.add(ckey)
                        all_entities.append(ent)

        # 2. Extract references from raw_inputs (closes P2-04 scalar bypass)
        if hasattr(sub_input, "raw_inputs") and sub_input.raw_inputs:
            raw_ents = self.extract_entities_from_raw_inputs(
                subcriterion_code, sub_input.raw_inputs, default_entity_type=default_entity_type
            )
            for rent in raw_ents:
                ckey = f"{rent.entity_type.upper()}::{rent.identifier_key.strip().upper()}"
                if ckey not in seen_keys:
                    seen_keys.add(ckey)
                    all_entities.append(rent)

        if not all_entities:
            return [], [], {"subcriterion_code": subcriterion_code, "total_entities_submitted": 0, "duplicates_detected": []}

        return self.validate_entities(subcriterion_code, all_entities, rule)
