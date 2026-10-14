/**
 * NEP Excellence Awards 2026 — Authoritative Rubrics & Scoring Option Registry
 * 
 * SOURCED VERBATIM FROM:
 * - College Parameters - NEP Excellence Awards 2026 (2).pdf (C1–C22)
 * - University Parameters - NEP Excellence Awards 2026 (1).pdf (U1–U20)
 * 
 * Strict Invariants:
 * - Every parameter code maps to its official rubric tiers and marks.
 * - Mutually exclusive options are classified as EXCLUSIVE_TIERS.
 * - Cumulative options are classified as CHECKLIST_ITEM.
 * - Count-based options are classified as COUNT_TIERS.
 * - Area selections are classified as PER_UNIT_AREAS.
 * - Grade choices are classified as GRADE_SELECT.
 */

export const RUBRIC_REGISTRY = {
  // ==========================================
  // COLLEGE FRAMEWORK (C1–C22)
  // ==========================================
  C1: {
    code: "C1",
    subcriteria: {
      "C1.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "achieved_targets_2024_25",
        denKey: "fixed_targets_2024_25",
        maxMarks: 6,
        options: [
          { id: "C1_T1", label: "I. Above 90%", threshold: "> 90%", marks: 6, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "C1_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 4, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "C1_T3", label: "III. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 2, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "C1_T4", label: "IV. 50% or below", threshold: "<= 50%", marks: 1, maxPct: 50, op: "lte", defaultNum: 40, defaultDen: 100 }
        ]
      }
    }
  },
  C2: {
    code: "C2",
    subcriteria: {
      "C2.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "students_completed",
        denKey: "eligible_students",
        maxMarks: 4,
        options: [
          { id: "C2_T1", label: "I. Above 90%", threshold: "> 90%", marks: 4, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "C2_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 3, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "C2_T3", label: "III. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 2, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "C2_T4", label: "IV. >25% and up to 50%", threshold: "> 25% and <= 50%", marks: 1, minPct: 25, maxPct: 50, op: "gt_lte", defaultNum: 35, defaultDen: 100 },
          { id: "C2_T5", label: "V. 25% or below", threshold: "<= 25%", marks: 0, maxPct: 25, op: "lte", defaultNum: 10, defaultDen: 100 }
        ]
      }
    }
  },
  C3: {
    code: "C3",
    subcriteria: {
      "C3.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "abc_registered_students",
        denKey: "total_enrolled_students",
        maxMarks: 4,
        options: [
          { id: "C3_T1", label: "I. Above 90%", threshold: "> 90%", marks: 4, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "C3_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 3, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "C3_T3", label: "III. >60% and up to 75%", threshold: "> 60% and <= 75%", marks: 2, minPct: 60, maxPct: 75, op: "gt_lte", defaultNum: 70, defaultDen: 100 },
          { id: "C3_T4", label: "IV. >50% and up to 60%", threshold: "> 50% and <= 60%", marks: 1, minPct: 50, maxPct: 60, op: "gt_lte", defaultNum: 55, defaultDen: 100 },
          { id: "C3_T5", label: "V. 50% or below", threshold: "<= 50%", marks: 0, maxPct: 50, op: "lte", defaultNum: 30, defaultDen: 100 }
        ]
      }
    }
  },
  C4: {
    code: "C4",
    subcriteria: {
      "C4.A": {
        type: "PER_UNIT_AREAS",
        fieldKey: "support_areas",
        unitMarks: 0.5,
        maxMarks: 2,
        options: [
          { id: "C4A_T1", label: "4 or more distinct supported areas", threshold: ">= 4 areas", marks: 2.0 },
          { id: "C4A_T2", label: "3 distinct supported areas", threshold: "3 areas", marks: 1.5 },
          { id: "C4A_T3", label: "2 distinct supported areas", threshold: "2 areas", marks: 1.0 },
          { id: "C4A_T4", label: "1 distinct supported area", threshold: "1 area", marks: 0.5 },
          { id: "C4A_T5", label: "0 supported areas", threshold: "0 areas", marks: 0.0 }
        ]
      },
      "C4.B": {
        type: "PER_UNIT_AREAS",
        fieldKey: "school_support_areas",
        gateKey: "schools_covered",
        gateMin: 5,
        unitMarks: 0.5,
        maxMarks: 2,
        options: [
          { id: "C4B_T1", label: ">= 5 schools covered AND 4+ areas", threshold: ">= 5 schools & 4+ areas", marks: 2.0 },
          { id: "C4B_T2", label: ">= 5 schools covered AND 3 areas", threshold: ">= 5 schools & 3 areas", marks: 1.5 },
          { id: "C4B_T3", label: ">= 5 schools covered AND 2 areas", threshold: ">= 5 schools & 2 areas", marks: 1.0 },
          { id: "C4B_T4", label: ">= 5 schools covered AND 1 area", threshold: ">= 5 schools & 1 area", marks: 0.5 },
          { id: "C4B_T5", label: "< 5 schools covered or 0 areas", threshold: "< 5 schools or 0 areas", marks: 0.0 }
        ]
      }
    }
  },
  C5: {
    code: "C5",
    subcriteria: {
      "C5.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "admitted_students",
        denKey: "sanctioned_intake",
        maxMarks: 2,
        options: [
          { id: "C5_T1", label: "I. 90% and above", threshold: ">= 90%", marks: 2, minPct: 90, op: "gte", defaultNum: 95, defaultDen: 100 },
          { id: "C5_T2", label: "II. Above 75% and less than 90%", threshold: "> 75% and < 90%", marks: 1, minPct: 75, maxPct: 90, op: "gt_lt", defaultNum: 82, defaultDen: 100 },
          { id: "C5_T3", label: "III. Below 75%", threshold: "< 75%", marks: 0, maxPct: 75, op: "lt", defaultNum: 60, defaultDen: 100 }
        ]
      }
    }
  },
  C6: {
    code: "C6",
    subcriteria: {
      "C6.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "certified_students",
        denKey: "total_enrolled_students",
        maxMarks: 6,
        options: [
          { id: "C6_T1", label: "I. Above 90%", threshold: "> 90%", marks: 6, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "C6_T2", label: "II. >80% and up to 90%", threshold: "> 80% and <= 90%", marks: 5, minPct: 80, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "C6_T3", label: "III. >70% and up to 80%", threshold: "> 70% and <= 80%", marks: 4, minPct: 70, maxPct: 80, op: "gt_lte", defaultNum: 75, defaultDen: 100 },
          { id: "C6_T4", label: "IV. >60% and up to 70%", threshold: "> 60% and <= 70%", marks: 3, minPct: 60, maxPct: 70, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "C6_T5", label: "V. >50% and up to 60%", threshold: "> 50% and <= 60%", marks: 2, minPct: 50, maxPct: 60, op: "gt_lte", defaultNum: 55, defaultDen: 100 },
          { id: "C6_T6", label: "VI. 50% or below", threshold: "<= 50%", marks: 1, maxPct: 50, op: "lte", defaultNum: 40, defaultDen: 100 }
        ]
      }
    }
  },
  C7: {
    code: "C7",
    subcriteria: {
      "C7.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "sedg_bridge_students",
        denKey: "total_sedg_students",
        maxMarks: 3,
        options: [
          { id: "C7_T1", label: "I. For 100% SEDG students", threshold: "100%", marks: 3, exactPct: 100, op: "eq", defaultNum: 100, defaultDen: 100 },
          { id: "C7_T2", label: "II. For 75% and above SEDG students", threshold: ">= 75% and < 100%", marks: 2, minPct: 75, maxPct: 100, op: "gte_lt", defaultNum: 80, defaultDen: 100 },
          { id: "C7_T3", label: "III. For 50% and above SEDG students", threshold: ">= 50% and < 75%", marks: 1, minPct: 50, maxPct: 75, op: "gte_lt", defaultNum: 60, defaultDen: 100 },
          { id: "C7_T4", label: "IV. Below 50%", threshold: "< 50%", marks: 0, maxPct: 50, op: "lt", defaultNum: 30, defaultDen: 100 }
        ]
      }
    }
  },
  C8: {
    code: "C8",
    subcriteria: {
      "C8.1": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 2,
        options: [
          { id: "C8_YES", label: "NEP-SARTHI nominated as per UGC Guidelines with office orders", threshold: "Yes", marks: 2 }
        ]
      }
    }
  },
  C9: {
    code: "C9",
    subcriteria: {
      "C9.I": {
        type: "EXCLUSIVE_TIERS",
        numKey: "participating_students",
        denKey: "eligible_students",
        maxMarks: 3,
        options: [
          { id: "C9_I_T1", label: "a. 100%", threshold: "100%", marks: 3, exactPct: 100, op: "eq", defaultNum: 100, defaultDen: 100 },
          { id: "C9_I_T2", label: "b. 75% and above", threshold: ">= 75% and < 100%", marks: 2, minPct: 75, maxPct: 100, op: "gte_lt", defaultNum: 80, defaultDen: 100 },
          { id: "C9_I_T3", label: "c. 50% and above", threshold: ">= 50% and < 75%", marks: 1, minPct: 50, maxPct: 75, op: "gte_lt", defaultNum: 60, defaultDen: 100 },
          { id: "C9_I_T4", label: "d. Below 50%", threshold: "< 50%", marks: 0, maxPct: 50, op: "lt", defaultNum: 30, defaultDen: 100 }
        ]
      },
      "C9.II": {
        type: "EXCLUSIVE_TIERS",
        numKey: "placed_students",
        denFromSibling: { subCode: "C9.I", key: "participating_students" },
        maxMarks: 3,
        options: [
          { id: "C9_II_T1", label: "a. 100%", threshold: "100%", marks: 3, exactPct: 100, op: "eq" },
          { id: "C9_II_T2", label: "b. 75% and above", threshold: ">= 75% and < 100%", marks: 2, minPct: 75, maxPct: 100, op: "gte_lt" },
          { id: "C9_II_T3", label: "c. 50% and above", threshold: ">= 50% and < 75%", marks: 1, minPct: 50, maxPct: 75, op: "gte_lt" },
          { id: "C9_II_T4", label: "d. Below 50%", threshold: "< 50%", marks: 0, maxPct: 50, op: "lt" }
        ]
      }
    }
  },
  C10: {
    code: "C10",
    subcriteria: {
      "C10.1": {
        type: "COUNT_TIERS",
        countKey: "active_mous_count",
        maxMarks: 5,
        options: [
          { id: "C10_T1", label: "I. Five or more active collaborations", threshold: ">= 5", marks: 5, minCount: 5 },
          { id: "C10_T2", label: "II. Four active collaborations", threshold: "4", marks: 4, exactCount: 4 },
          { id: "C10_T3", label: "III. Three active collaborations", threshold: "3", marks: 3, exactCount: 3 },
          { id: "C10_T4", label: "IV. Two active collaborations", threshold: "2", marks: 2, exactCount: 2 },
          { id: "C10_T5", label: "V. One active collaboration", threshold: "1", marks: 1, exactCount: 1 },
          { id: "C10_T6", label: "VI. No active collaboration", threshold: "0", marks: 0, exactCount: 0 }
        ]
      }
    }
  },
  C11: {
    code: "C11",
    subcriteria: {
      "C11.I": {
        type: "COUNT_TIERS",
        countKey: "ventures_count",
        maxMarks: 3,
        options: [
          { id: "C11_I_T1", label: "a. More than 10 ventures", threshold: "> 10", marks: 3, minCount: 11 },
          { id: "C11_I_T2", label: "b. 6 to 10 ventures", threshold: "6 to 10", marks: 2, minCount: 6, maxCount: 10 },
          { id: "C11_I_T3", label: "c. 1 to 5 ventures", threshold: "1 to 5", marks: 1, minCount: 1, maxCount: 5 },
          { id: "C11_I_T4", label: "d. 0 ventures", threshold: "0", marks: 0, exactCount: 0 }
        ]
      },
      "C11.II.a": {
        type: "CHECKLIST_ITEM",
        fieldKey: "cell_functional",
        maxMarks: 1,
        options: [
          { id: "C11_IIA", label: "Functional incubation/startup/entrepreneurship cell with annual activity report", threshold: "Yes", marks: 1 }
        ]
      },
      "C11.II.b": {
        type: "EXCLUSIVE_TIERS",
        numKey: "monetized_count",
        denFromSibling: { subCode: "C11.I", key: "ventures_count" },
        maxMarks: 1,
        options: [
          { id: "C11_IIB_YES", label: "50% or more ventures monetised/commercialised/receiving seed support", threshold: ">= 50%", marks: 1, minPct: 50, op: "gte" },
          { id: "C11_IIB_NO", label: "Less than 50% monetised or zero ventures", threshold: "< 50%", marks: 0, maxPct: 50, op: "lt" }
        ]
      }
    }
  },
  C12: {
    code: "C12",
    subcriteria: {
      "C12.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C12_1", label: "I. Alumni cell with updated alumni database", threshold: "Yes", marks: 1 }] },
      "C12.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C12_2", label: "II. Alumni annual report / reunion organised between July 2025 and June 2026", threshold: "Yes", marks: 1 }] },
      "C12.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C12_3", label: "III. At least five alumni invited as experts/mentors/guest speakers or felicitated", threshold: "Yes", marks: 1 }] },
      "C12.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C12_4", label: "IV. Five or more extension lectures by external experts", threshold: "Yes", marks: 1 }] },
      "C12.5": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C12_5", label: "V. Alumni/experts engaged for placement, internship, mentoring or curriculum inputs", threshold: "Yes", marks: 1 }] }
    }
  },
  C13: {
    code: "C13",
    subcriteria: {
      "C13.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "trained_faculty",
        denKey: "total_fulltime_faculty",
        maxMarks: 4,
        options: [
          { id: "C13_T1", label: "I. Above 80%", threshold: "> 80%", marks: 4, minPct: 80, op: "gt", defaultNum: 85, defaultDen: 100 },
          { id: "C13_T2", label: "II. >60% and up to 80%", threshold: "> 60% and <= 80%", marks: 3, minPct: 60, maxPct: 80, op: "gt_lte", defaultNum: 70, defaultDen: 100 },
          { id: "C13_T3", label: "III. >40% and up to 60%", threshold: "> 40% and <= 60%", marks: 2, minPct: 40, maxPct: 60, op: "gt_lte", defaultNum: 50, defaultDen: 100 },
          { id: "C13_T4", label: "IV. >20% and up to 40%", threshold: "> 20% and <= 40%", marks: 1, minPct: 20, maxPct: 40, op: "gt_lte", defaultNum: 30, defaultDen: 100 },
          { id: "C13_T5", label: "V. 20% or below", threshold: "<= 20%", marks: 0, maxPct: 20, op: "lte", defaultNum: 10, defaultDen: 100 }
        ]
      }
    }
  },
  C14: {
    code: "C14",
    subcriteria: {
      "C14.A": {
        type: "PER_UNIT_AREAS",
        countKey: "content_items",
        unitMarks: 0.5,
        maxMarks: 2,
        options: [
          { id: "C14A_T1", label: "4 or more learning materials developed (0.5 mark each)", threshold: ">= 4 items", marks: 2.0 },
          { id: "C14A_T2", label: "3 learning materials developed", threshold: "3 items", marks: 1.5 },
          { id: "C14A_T3", label: "2 learning materials developed", threshold: "2 items", marks: 1.0 },
          { id: "C14A_T4", label: "1 learning material developed", threshold: "1 item", marks: 0.5 },
          { id: "C14A_T5", label: "0 learning materials developed", threshold: "0 items", marks: 0.0 }
        ]
      },
      "C14.B": {
        type: "COUNT_TIERS",
        countKey: "iks_activities",
        maxMarks: 2,
        options: [
          { id: "C14B_T1", label: "Five or more IKS-related academic/co-curricular activities", threshold: ">= 5 activities", marks: 2, minCount: 5 },
          { id: "C14B_T2", label: "Fewer than 5 IKS activities conducted", threshold: "< 5 activities", marks: 0, maxCount: 4 }
        ]
      }
    }
  },
  C15: {
    code: "C15",
    subcriteria: {
      "C15.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C15_1", label: "I. Mental Health and Well-being Centre / Student Service Centre established", threshold: "Yes", marks: 1 }] },
      "C15.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C15_2", label: "II. Minimum two workshops on mental health and well-being for students", threshold: "Yes", marks: 1 }] },
      "C15.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C15_3", label: "III. Workshop on mental health/well-being for teaching and non-teaching staff", threshold: "Yes", marks: 1 }] },
      "C15.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C15_4", label: "IV. Annual activity calendar prepared as per UGC guidelines for fitness, sports, health", threshold: "Yes", marks: 1 }] },
      "C15.5": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C15_5", label: "V. Five or more sports / yoga / fitness activities conducted for students", threshold: "Yes", marks: 1 }] },
      "C15.6": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C15_6", label: "VI. Student participation in inter-college/university/state/national sports/yoga events", threshold: "Yes", marks: 1 }] }
    }
  },
  C16: {
    code: "C16",
    subcriteria: {
      "C16.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C16_1", label: "I. ICC and Women Cell constituted and displayed at prominent places", threshold: "Yes", marks: 1 }] },
      "C16.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C16_2", label: "II. Gender parity / safety billboards displayed in campus", threshold: "Yes", marks: 1 }] },
      "C16.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C16_3", label: "III. Gender Champion nominated and uploaded on SAKSHAM", threshold: "Yes", marks: 1 }] },
      "C16.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C16_4", label: "IV. Participation in SAKSHAM Gender Audit", threshold: "Yes", marks: 1 }] },
      "C16.5": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C16_5", label: "V. Workshop for students on gender sensitisation / SAKSHAM / Government initiatives", threshold: "Yes", marks: 1 }] }
    }
  },
  C17: {
    code: "C17",
    subcriteria: {
      "C17.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "participating_students",
        denKey: "total_enrolled_students",
        maxMarks: 5,
        options: [
          { id: "C17_T1", label: "I. Above 90%", threshold: "> 90%", marks: 5, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "C17_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 4, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "C17_T3", label: "III. >60% and up to 75%", threshold: "> 60% and <= 75%", marks: 3, minPct: 60, maxPct: 75, op: "gt_lte", defaultNum: 70, defaultDen: 100 },
          { id: "C17_T4", label: "IV. >50% and up to 60%", threshold: "> 50% and <= 60%", marks: 2, minPct: 50, maxPct: 60, op: "gt_lte", defaultNum: 55, defaultDen: 100 },
          { id: "C17_T5", label: "V. Up to 50%", threshold: "> 0% and <= 50%", marks: 1, minPct: 0.001, maxPct: 50, op: "gt_lte", defaultNum: 30, defaultDen: 100 },
          { id: "C17_T6", label: "VI. No activity", threshold: "0% / No participation", marks: 0, exactPct: 0, op: "eq", defaultNum: 0, defaultDen: 100 }
        ]
      }
    }
  },
  C18: {
    code: "C18",
    subcriteria: {
      "C18.1": {
        type: "COUNT_TIERS",
        countKey: "sdg_activities",
        maxMarks: 2,
        options: [
          { id: "C18_1_T1", label: "Five or more activities mapped with SDGs", threshold: ">= 5 activities", marks: 2, minCount: 5 },
          { id: "C18_1_T2", label: "Fewer than 5 activities mapped with SDGs", threshold: "< 5 activities", marks: 0, maxCount: 4 }
        ]
      },
      "C18.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C18_2", label: "Green campus / environmental practices (waste segregation, water/energy conservation, plastic-free)", threshold: "Yes", marks: 1 }] },
      "C18.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C18_3", label: "Student-led environment/sustainability club or eco-club functional", threshold: "Yes", marks: 1 }] },
      "C18.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C18_4", label: "Annual report / evidence of SDG mapping and outcomes", threshold: "Yes", marks: 1 }] }
    }
  },
  C19: {
    code: "C19",
    subcriteria: {
      "C19.I": {
        type: "COUNT_TIERS",
        countKey: "patents_filed",
        maxMarks: 2,
        options: [
          { id: "C19_I_T1", label: "4 or more patents filed (1 mark per 2 patents)", threshold: ">= 4 patents", marks: 2, minCount: 4 },
          { id: "C19_I_T2", label: "2 or 3 patents filed", threshold: "2 to 3 patents", marks: 1, minCount: 2, maxCount: 3 },
          { id: "C19_I_T3", label: "Fewer than 2 patents filed", threshold: "< 2 patents", marks: 0, maxCount: 1 }
        ]
      },
      "C19.II": {
        type: "COUNT_TIERS",
        countKey: "patents_granted",
        maxMarks: 2,
        options: [
          { id: "C19_II_T1", label: "2 or more patents granted (1 mark per patent)", threshold: ">= 2 patents", marks: 2, minCount: 2 },
          { id: "C19_II_T2", label: "1 patent granted", threshold: "1 patent", marks: 1, exactCount: 1 },
          { id: "C19_II_T3", label: "0 patents granted", threshold: "0 patents", marks: 0, exactCount: 0 }
        ]
      },
      "C19.III": {
        type: "COUNT_TIERS",
        countKey: "scopus_index",
        maxMarks: 2,
        isPolicyNotice: true,
        policyNoticeText: "Council Notice: Statutory metric for Scopus Index is currently undefined. Claiming a non-zero value blocks certification until defined.",
        options: [
          { id: "C19_III_T1", label: "a. 100 and above", threshold: ">= 100", marks: 2, minCount: 100 },
          { id: "C19_III_T2", label: "b. 50 and above", threshold: ">= 50 and < 100", marks: 1, minCount: 50, maxCount: 99 },
          { id: "C19_III_T3", label: "c. Below 50", threshold: "< 50", marks: 0, maxCount: 49 }
        ]
      }
    }
  },
  C20: {
    code: "C20",
    subcriteria: {
      "C20.1": {
        type: "GRADE_SELECT",
        fieldKey: "naac_grade",
        maxMarks: 2,
        options: [
          { id: "C20_A", label: "NAAC A++ / A+ / A grade", threshold: "A++, A+, A", marks: 2, values: ["A++", "A+", "A"] },
          { id: "C20_B", label: "NAAC B++ / B+ / B grade", threshold: "B++, B+, B", marks: 1, values: ["B++", "B+", "B"] },
          { id: "C20_C", label: "Grade C or Unaccredited", threshold: "C / Not Accredited", marks: 0, values: ["C", "NOT_ACCREDITED"] }
        ]
      },
      "C20.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C20_2", label: "II. Registered for NIRF 2026 or participated in NIRF / India Rankings", threshold: "Yes", marks: 1 }] },
      "C20.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C20_3", label: "III. AISHE data submitted for the latest cycle", threshold: "Yes", marks: 1 }] },
      "C20.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C20_4", label: "IV. IQAC annual quality assurance mechanism / AQAR prepared", threshold: "Yes", marks: 1 }] }
    }
  },
  C21: {
    code: "C21",
    subcriteria: {
      "C21.1": {
        type: "COUNT_TIERS",
        countKey: "activities_count",
        maxMarks: 2,
        options: [
          { id: "C21_1_T1", label: "I. Five or more activities", threshold: ">= 5", marks: 2, minCount: 5 },
          { id: "C21_1_T2", label: "II. Two to four activities", threshold: "2 to 4", marks: 1, minCount: 2, maxCount: 4 },
          { id: "C21_1_T3", label: "III. Exactly 1 activity (Uncovered in PDF; Policy BOUNDARY_C21_1_ACTIVITY)", threshold: "1", marks: 0, exactCount: 1 },
          { id: "C21_1_T4", label: "IV. No activity", threshold: "0", marks: 0, exactCount: 0 }
        ]
      },
      "C21.2": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 1,
        options: [
          { id: "C21_2", label: "Integration of ethics, constitutional values, civic duties or local culture in student activities/curriculum", threshold: "Yes", marks: 1 }
        ]
      }
    }
  },
  C22: {
    code: "C22",
    subcriteria: {
      "C22.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C22_1", label: "I. Structured student feedback collected and analysed for curriculum/teaching/services", threshold: "Yes", marks: 1 }] },
      "C22.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "C22_2", label: "II. Action Taken Report prepared and approved by competent authority/IQAC", threshold: "Yes", marks: 1 }] }
    }
  },

  // ==========================================
  // UNIVERSITY FRAMEWORK (U1–U20)
  // ==========================================
  U1: {
    code: "U1",
    subcriteria: {
      "U1.1": {
        type: "COUNT_TIERS",
        countKey: "programmes_count",
        maxMarks: 4,
        options: [
          { id: "U1_T1", label: "I. Above 10 programmes", threshold: "> 10", marks: 4, minCount: 11 },
          { id: "U1_T2", label: "II. >7 and up to 10 programmes", threshold: "> 7 and <= 10", marks: 3, minCount: 8, maxCount: 10 },
          { id: "U1_T3", label: "III. >4 and up to 7 programmes", threshold: "> 4 and <= 7", marks: 2, minCount: 5, maxCount: 7 },
          { id: "U1_T4", label: "IV. Up to 4 programmes", threshold: ">= 1 and <= 4", marks: 1, minCount: 1, maxCount: 4 },
          { id: "U1_T5", label: "V. No programme", threshold: "0", marks: 0, exactCount: 0 }
        ]
      }
    }
  },
  U2: {
    code: "U2",
    subcriteria: {
      "U2.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "indian_lang_programmes",
        denKey: "total_degree_programmes",
        maxMarks: 4,
        options: [
          { id: "U2_T1", label: "I. Above 75%", threshold: "> 75%", marks: 4, minPct: 75, op: "gt", defaultNum: 80, defaultDen: 100 },
          { id: "U2_T2", label: "II. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 3, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 60, defaultDen: 100 },
          { id: "U2_T3", label: "III. >25% and up to 50%", threshold: "> 25% and <= 50%", marks: 2, minPct: 25, maxPct: 50, op: "gt_lte", defaultNum: 35, defaultDen: 100 },
          { id: "U2_T4", label: "IV. Up to 25%", threshold: "> 0% and <= 25%", marks: 1, minPct: 0.001, maxPct: 25, op: "gt_lte", defaultNum: 15, defaultDen: 100 },
          { id: "U2_T5", label: "V. No such course", threshold: "0%", marks: 0, exactPct: 0, op: "eq", defaultNum: 0, defaultDen: 100 }
        ]
      }
    }
  },
  U3: {
    code: "U3",
    subcriteria: {
      "U3.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "iks_programmes",
        denKey: "total_degree_programmes",
        maxMarks: 4,
        options: [
          { id: "U3_T1", label: "I. Above 25%", threshold: "> 25%", marks: 4, minPct: 25, op: "gt", defaultNum: 30, defaultDen: 100 },
          { id: "U3_T2", label: "II. >15% and up to 25%", threshold: "> 15% and <= 25%", marks: 3, minPct: 15, maxPct: 25, op: "gt_lte", defaultNum: 20, defaultDen: 100 },
          { id: "U3_T3", label: "III. >5% and up to 15%", threshold: "> 5% and <= 15%", marks: 2, minPct: 5, maxPct: 15, op: "gt_lte", defaultNum: 10, defaultDen: 100 },
          { id: "U3_T4", label: "IV. Up to 5%", threshold: "> 0% and <= 5%", marks: 1, minPct: 0.001, maxPct: 5, op: "gt_lte", defaultNum: 3, defaultDen: 100 },
          { id: "U3_T5", label: "V. No integration", threshold: "0%", marks: 0, exactPct: 0, op: "eq", defaultNum: 0, defaultDen: 100 }
        ]
      }
    }
  },
  U4: {
    code: "U4",
    subcriteria: {
      "U4.A": {
        type: "EXCLUSIVE_TIERS",
        numKey: "achieved_targets_2024_25",
        denKey: "total_targets_2024_25",
        maxMarks: 3,
        options: [
          { id: "U4A_T1", label: "I. Above 90%", threshold: "> 90%", marks: 3, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "U4A_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 2, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "U4A_T3", label: "III. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 1, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "U4A_T4", label: "IV. 50% or below", threshold: "<= 50%", marks: 0, maxPct: 50, op: "lte", defaultNum: 40, defaultDen: 100 }
        ]
      },
      "U4.B": {
        type: "EXCLUSIVE_TIERS",
        numKey: "achieved_targets_2025_26",
        denKey: "total_targets_2025_26",
        maxMarks: 3,
        options: [
          { id: "U4B_T1", label: "I. Above 90%", threshold: "> 90%", marks: 3, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "U4B_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 2, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "U4B_T3", label: "III. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 1, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "U4B_T4", label: "IV. 50% or below", threshold: "<= 50%", marks: 0, maxPct: 50, op: "lte", defaultNum: 40, defaultDen: 100 }
        ]
      }
    }
  },
  U5: {
    code: "U5",
    subcriteria: {
      "U5.A": {
        type: "EXCLUSIVE_TIERS",
        numKey: "eligible_students",
        denKey: "total_final_year_students",
        maxMarks: 2,
        options: [
          { id: "U5A_T1", label: "I. Above 75%", threshold: "> 75%", marks: 2, minPct: 75, op: "gt", defaultNum: 80, defaultDen: 100 },
          { id: "U5A_T2", label: "II. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 1, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "U5A_T3", label: "III. Exactly 50.0% (Uncovered in PDF; Policy BOUNDARY_U5A_50)", threshold: "50.0%", marks: 0, exactPct: 50, op: "eq" },
          { id: "U5A_T4", label: "IV. <50%", threshold: "< 50%", marks: 0, maxPct: 50, op: "lt", defaultNum: 30, defaultDen: 100 }
        ]
      },
      "U5.B": {
        type: "EXCLUSIVE_TIERS",
        numKey: "placed_students",
        denFromSibling: { subCode: "U5.A", key: "eligible_students" },
        maxMarks: 2,
        options: [
          { id: "U5B_T1", label: "I. Above 75%", threshold: "> 75%", marks: 2, minPct: 75, op: "gt" },
          { id: "U5B_T2", label: "II. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 1, minPct: 50, maxPct: 75, op: "gt_lte" },
          { id: "U5B_T3", label: "III. >25% and up to 50%", threshold: "> 25% and <= 50%", marks: 0.5, minPct: 25, maxPct: 50, op: "gt_lte" },
          { id: "U5B_T4", label: "IV. <=25%", threshold: "<= 25%", marks: 0, maxPct: 25, op: "lte" }
        ]
      }
    }
  },
  U6: {
    code: "U6",
    subcriteria: {
      "U6.A": {
        type: "CHECKLIST_ITEM",
        fieldKey: "ordinance_notified",
        maxMarks: 4,
        options: [
          { id: "U6A_YES", label: "Amendment in Examination Ordinance for Assessing Learning Outcomes", threshold: "Yes", marks: 4 }
        ]
      },
      "U6.B": {
        type: "COUNT_TIERS",
        countKey: "tools_count",
        maxMarks: 4,
        options: [
          { id: "U6B_T1", label: "4 Interventions / tools implemented", threshold: ">= 4 tools", marks: 4, minCount: 4 },
          { id: "U6B_T2", label: "3 Interventions / tools implemented", threshold: "3 tools", marks: 3, exactCount: 3 },
          { id: "U6B_T3", label: "2 Interventions / tools implemented", threshold: "2 tools", marks: 2, exactCount: 2 },
          { id: "U6B_T4", label: "1 Intervention / tool implemented", threshold: "1 tool", marks: 1, exactCount: 1 },
          { id: "U6B_T5", label: "0 Interventions / tools implemented", threshold: "0 tools", marks: 0, exactCount: 0 }
        ]
      }
    }
  },
  U7: {
    code: "U7",
    subcriteria: {
      "U7.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U7_1", label: "I. PoP appointed as per applicable norms", threshold: "Yes", marks: 1 }] },
      "U7.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U7_2", label: "II. Complete course / module delivered by PoP", threshold: "Yes", marks: 1 }] },
      "U7.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U7_3", label: "III. Lab, studio, industry project, live project or mentoring activity conducted", threshold: "Yes", marks: 1 }] },
      "U7.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U7_4", label: "IV. Documented outcomes (student projects, prototypes, industry problem-solving)", threshold: "Yes", marks: 1 }] }
    }
  },
  U8: {
    code: "U8",
    subcriteria: {
      "U8.A": {
        type: "COUNT_TIERS",
        countKey: "startups_count",
        maxMarks: 4,
        options: [
          { id: "U8A_T1", label: "III. More than 10 startups", threshold: "> 10", marks: 4, minCount: 11 },
          { id: "U8A_T2", label: "II. 6-10 startups", threshold: "6 to 10", marks: 3, minCount: 6, maxCount: 10 },
          { id: "U8A_T3", label: "I. 1-5 startups", threshold: "1 to 5", marks: 2, minCount: 1, maxCount: 5 },
          { id: "U8A_T4", label: "0 startups", threshold: "0", marks: 0, exactCount: 0 }
        ]
      },
      "U8.B": {
        type: "EXCLUSIVE_TIERS",
        numKey: "monetized_count",
        denFromSibling: { subCode: "U8.A", key: "startups_count" },
        maxMarks: 2,
        options: [
          { id: "U8B_YES", label: "50% or more of reported startups monetised/commercialised/funded", threshold: ">= 50%", marks: 2, minPct: 50, op: "gte" },
          { id: "U8B_NO", label: "Less than 50% monetised or zero startups", threshold: "< 50%", marks: 0, maxPct: 50, op: "lt" }
        ]
      }
    }
  },
  U9: {
    code: "U9",
    subcriteria: {
      "U9.A": {
        type: "EXCLUSIVE_TIERS",
        numKey: "active_mous",
        denKey: "total_mous",
        maxMarks: 1,
        options: [
          { id: "U9A_YES", label: "Active collaboration percentage is > 75%", threshold: "> 75%", marks: 1, minPct: 75, op: "gt", defaultNum: 8, defaultDen: 10 },
          { id: "U9A_NO", label: "Active collaboration percentage is <= 75%", threshold: "<= 75%", marks: 0, maxPct: 75, op: "lte", defaultNum: 5, defaultDen: 10 }
        ]
      },
      "U9.B": {
        type: "COUNT_TIERS",
        countKey: "activities_count",
        maxMarks: 5,
        options: [
          { id: "U9B_T1", label: "I. 5 or more average activities", threshold: ">= 5", marks: 5, minCount: 5 },
          { id: "U9B_T2", label: "II. 4 average activities", threshold: "4", marks: 4, exactCount: 4 },
          { id: "U9B_T3", label: "III. 3 average activities", threshold: "3", marks: 3, exactCount: 3 },
          { id: "U9B_T4", label: "IV. 2 average activities", threshold: "2", marks: 2, exactCount: 2 },
          { id: "U9B_T5", label: "V. 1 average activity", threshold: "1", marks: 1, exactCount: 1 },
          { id: "U9B_T6", label: "0 average activities", threshold: "0", marks: 0, exactCount: 0 }
        ]
      }
    }
  },
  U10: {
    code: "U10",
    subcriteria: {
      "U10.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U10_1", label: "I. Alumni Society registered under Societies Act", threshold: "Yes", marks: 1 }] },
      "U10.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U10_2", label: "II. Updated alumni database maintained", threshold: "Yes", marks: 1 }] },
      "U10.3": {
        type: "CURRENCY_TIERS",
        fieldKey: "funding_amount",
        maxMarks: 2,
        options: [
          { id: "U10_3_T1", label: "a) >Rs.1 Crore received during evaluation period", threshold: "> Rs. 1,00,00,000", marks: 2, minVal: 10000001 },
          { id: "U10_3_T2", label: "b) Exactly Rs. 1 Crore (Uncovered in PDF; Policy BOUNDARY_U10_3_1CR)", threshold: "Rs. 1,00,00,000", marks: 0, exactVal: 10000000 },
          { id: "U10_3_T3", label: "c) <Rs.1 Crore received during evaluation period", threshold: "> 0 and < Rs. 1,00,00,000", marks: 1, minVal: 1, maxVal: 9999999 },
          { id: "U10_3_T4", label: "d) No Alumni Funding Received during evaluation period", threshold: "Rs. 0", marks: 0, exactVal: 0 }
        ]
      },
      "U10.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U10_4", label: "IV. At least 5 alumni invited as speakers/mentors or recognised", threshold: "Yes", marks: 1 }] }
    }
  },
  U11: {
    code: "U11",
    subcriteria: {
      "U11.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U11_1", label: "I. Gender parity display boards placed in campus", threshold: "Yes", marks: 1 }] },
      "U11.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U11_2", label: "II. Gender Champion nominated and uploaded on SAKSHAM", threshold: "Yes", marks: 1 }] },
      "U11.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U11_3", label: "III. Participation in SAKSHAM Gender Audit completed", threshold: "Yes", marks: 1 }] },
      "U11.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U11_4", label: "IV. Workshop for students on gender sensitisation / SAKSHAM", threshold: "Yes", marks: 1 }] }
    }
  },
  U12: {
    code: "U12",
    subcriteria: {
      "U12.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U12_1", label: "I. MHWBC and/or Student Service Centre established", threshold: "Yes", marks: 1 }] },
      "U12.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U12_2", label: "II. Annual activity calendar for sports, yoga, fitness, health prepared and implemented", threshold: "Yes", marks: 1 }] },
      "U12.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U12_3", label: "III. Minimum two student workshops on mental health, well-being, yoga, stress management", threshold: "Yes", marks: 1 }] },
      "U12.4": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U12_4", label: "IV. Workshop/orientation organised for staff on mental health/support", threshold: "Yes", marks: 1 }] },
      "U12.5": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U12_5", label: "V. Counselling/referral mechanism, student support records or annual report maintained", threshold: "Yes", marks: 1 }] }
    }
  },
  U13: {
    code: "U13",
    subcriteria: {
      "U13.1": {
        type: "EXCLUSIVE_TIERS",
        numKey: "regular_mooc_learners",
        denKey: "total_regular_learners",
        maxMarks: 6,
        options: [
          { id: "U13_T1", label: "I. Above 75%", threshold: "> 75%", marks: 6, minPct: 75, op: "gt", defaultNum: 80, defaultDen: 100 },
          { id: "U13_T2", label: "II. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 5, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 60, defaultDen: 100 },
          { id: "U13_T3", label: "III. >25% and up to 50%", threshold: "> 25% and <= 50%", marks: 3, minPct: 25, maxPct: 50, op: "gt_lte", defaultNum: 35, defaultDen: 100 },
          { id: "U13_T4", label: "IV. Up to 25%", threshold: "> 0% and <= 25%", marks: 2, minPct: 0.001, maxPct: 25, op: "gt_lte", defaultNum: 15, defaultDen: 100 },
          { id: "U13_T5", label: "V. No online/MOOC adoption", threshold: "0%", marks: 0, exactPct: 0, op: "eq", defaultNum: 0, defaultDen: 100 }
        ]
      }
    }
  },
  U14: {
    code: "U14",
    subcriteria: {
      "U14.A": {
        type: "EXCLUSIVE_TIERS",
        numKey: "multidisciplinary_programmes",
        denKey: "total_degree_programmes",
        maxMarks: 4,
        options: [
          { id: "U14A_T1", label: "I. Above 90%", threshold: "> 90%", marks: 4, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "U14A_T2", label: "II. >75% and up to 90%", threshold: "> 75% and <= 90%", marks: 3, minPct: 75, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "U14A_T3", label: "III. >50% and up to 75%", threshold: "> 50% and <= 75%", marks: 2, minPct: 50, maxPct: 75, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "U14A_T4", label: "IV. >25% and up to 50%", threshold: "> 25% and <= 50%", marks: 1, minPct: 25, maxPct: 50, op: "gt_lte", defaultNum: 35, defaultDen: 100 },
          { id: "U14A_T5", label: "V. 25% and below", threshold: "<= 25%", marks: 0, maxPct: 25, op: "lte", defaultNum: 15, defaultDen: 100 }
        ]
      },
      "U14.B": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 1,
        options: [
          { id: "U14_B", label: "Physical education/sports/yogasan embedded as AEC/VAC/NCC/NSS in all relevant programmes", threshold: "Yes", marks: 1 }
        ]
      },
      "U14.C": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 1,
        options: [
          { id: "U14_C", label: "Industry-aligned VAC/SEC courses embedded in programmes", threshold: "Yes", marks: 1 }
        ]
      }
    }
  },
  U15: {
    code: "U15",
    subcriteria: {
      "U15.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U15_1", label: "I. Multiple entry-exit framework notified and incorporated in ordinances", threshold: "Yes", marks: 1 }] },
      "U15.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U15_2", label: "II. Multiple entry-exit format for student application and certificate designed", threshold: "Yes", marks: 1 }] }
    }
  },
  U16: {
    code: "U16",
    subcriteria: {
      "U16.I": {
        type: "COUNT_TIERS",
        countKey: "patents_filed",
        maxMarks: 2,
        options: [
          { id: "U16_I_T1", label: "10 or more patents filed (1 mark per 5 patents)", threshold: ">= 10", marks: 2, minCount: 10 },
          { id: "U16_I_T2", label: "5 to 9 patents filed", threshold: "5 to 9", marks: 1, minCount: 5, maxCount: 9 },
          { id: "U16_I_T3", label: "Fewer than 5 patents filed", threshold: "< 5", marks: 0, maxCount: 4 }
        ]
      },
      "U16.II": {
        type: "COUNT_TIERS",
        countKey: "patents_granted",
        maxMarks: 2,
        options: [
          { id: "U16_II_T1", label: "2 or more patents granted/commercialised/licensed (1 mark each)", threshold: ">= 2", marks: 2, minCount: 2 },
          { id: "U16_II_T2", label: "1 patent granted/commercialised/licensed", threshold: "1", marks: 1, exactCount: 1 },
          { id: "U16_II_T3", label: "0 patents granted", threshold: "0", marks: 0, exactCount: 0 }
        ]
      },
      "U16.III": {
        type: "COUNT_TIERS",
        countKey: "scopus_index",
        maxMarks: 4,
        isPolicyNotice: true,
        policyNoticeText: "Council Notice: Statutory metric for Scopus Index is currently undefined. Claiming a non-zero value blocks certification until defined.",
        options: [
          { id: "U16_III_T1", label: "a. 400 and above", threshold: ">= 400", marks: 4, minCount: 400 },
          { id: "U16_III_T2", label: "b. 300 and above", threshold: ">= 300 and < 400", marks: 3, minCount: 300, maxCount: 399 },
          { id: "U16_III_T3", label: "c. 200 and above", threshold: ">= 200 and < 300", marks: 2, minCount: 200, maxCount: 299 },
          { id: "U16_III_T4", label: "d. 100 and above", threshold: ">= 100 and < 200", marks: 1, minCount: 100, maxCount: 199 },
          { id: "U16_III_T5", label: "Below 100", threshold: "< 100", marks: 0, maxCount: 99 }
        ]
      }
    }
  },
  U17: {
    code: "U17",
    subcriteria: {
      "U17.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U17_1", label: "I. Registered / submitted data for NIRF 2026 rankings", threshold: "Yes", marks: 1 }] },
      "U17.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U17_2", label: "II. Ranked in Top 100 or officially notified rank band in NIRF 2025", threshold: "Yes", marks: 1 }] }
    }
  },
  U18: {
    code: "U18",
    subcriteria: {
      "U18.1": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U18_1", label: "A. RPL guidelines/policy adopted by university in line with UGC/State guidelines", threshold: "Yes", marks: 1 }] },
      "U18.2": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 1, options: [{ id: "U18_2", label: "B. Awareness workshop for faculty/staff/students for RPL organised during evaluation year", threshold: "Yes", marks: 1 }] },
      "U18.3": { type: "CHECKLIST_ITEM", fieldKey: "verified", maxMarks: 2, options: [{ id: "U18_3", label: "C. RPL format for students circulated with guidelines", threshold: "Yes", marks: 2 }] }
    }
  },
  U19: {
    code: "U19",
    subcriteria: {
      "U19.A": {
        type: "EXCLUSIVE_TIERS",
        numKey: "obe_programmes",
        denKey: "total_degree_programmes",
        maxMarks: 6,
        options: [
          { id: "U19A_T1", label: "I. Above 90%", threshold: "> 90%", marks: 6, minPct: 90, op: "gt", defaultNum: 95, defaultDen: 100 },
          { id: "U19A_T2", label: "II. >80% and up to 90%", threshold: "> 80% and <= 90%", marks: 5, minPct: 80, maxPct: 90, op: "gt_lte", defaultNum: 85, defaultDen: 100 },
          { id: "U19A_T3", label: "III. >70% and up to 80%", threshold: "> 70% and <= 80%", marks: 4, minPct: 70, maxPct: 80, op: "gt_lte", defaultNum: 75, defaultDen: 100 },
          { id: "U19A_T4", label: "IV. >60% and up to 70%", threshold: "> 60% and <= 70%", marks: 3, minPct: 60, maxPct: 70, op: "gt_lte", defaultNum: 65, defaultDen: 100 },
          { id: "U19A_T5", label: "V. >50% and up to 60%", threshold: "> 50% and <= 60%", marks: 2, minPct: 50, maxPct: 60, op: "gt_lte", defaultNum: 55, defaultDen: 100 },
          { id: "U19A_T6", label: "VI. >25% and up to 50%", threshold: "> 25% and <= 50%", marks: 1, minPct: 25, maxPct: 50, op: "gt_lte", defaultNum: 35, defaultDen: 100 },
          { id: "U19A_T7", label: "VII. 25% or below", threshold: "<= 25%", marks: 0, maxPct: 25, op: "lte", defaultNum: 15, defaultDen: 100 }
        ]
      },
      "U19.B": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 2,
        options: [
          { id: "U19_B", label: "Whether examinations are conducted according to CO-PO of the Programmes", threshold: "Yes", marks: 2 }
        ]
      }
    }
  },
  U20: {
    code: "U20",
    subcriteria: {
      "U20.1": {
        type: "COUNT_TIERS",
        countKey: "activities_count",
        maxMarks: 2,
        options: [
          { id: "U20_1_T1", label: "I. 10 or more mapped activities", threshold: ">= 10", marks: 2, minCount: 10 },
          { id: "U20_1_T2", label: "II. 5 and above mapped activities", threshold: "5 to 9", marks: 1, minCount: 5, maxCount: 9 },
          { id: "U20_1_T3", label: "Fewer than 5 mapped activities", threshold: "< 5", marks: 0, maxCount: 4 }
        ]
      },
      "U20.2": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 2,
        options: [
          { id: "U20_2", label: "Curriculum mapping with SDG", threshold: "Yes", marks: 2 }
        ]
      },
      "U20.3": {
        type: "CHECKLIST_ITEM",
        fieldKey: "verified",
        maxMarks: 1,
        options: [
          { id: "U20_3", label: "Annual SDG activity report published with evidence of outcomes and SDG mapping", threshold: "Yes", marks: 1 }
        ]
      }
    }
  }
};

/**
 * Returns the active rubric option ID matching the current input values for a subcriterion.
 */
export function getActiveRubricOptionId(rubricSub, subVals = {}, allSubVals = {}) {
  if (!rubricSub || !rubricSub.options) return null;

  if (rubricSub.type === "EXCLUSIVE_TIERS") {
    let num = subVals[rubricSub.numKey];
    let den;
    if (rubricSub.denFromSibling) {
      den = (allSubVals[rubricSub.denFromSibling.subCode] || {})[rubricSub.denFromSibling.key];
    } else {
      den = subVals[rubricSub.denKey];
    }

    if (num === undefined || num === "" || den === undefined || den === "" || Number(den) <= 0) {
      return null;
    }
    const pct = (Number(num) / Number(den)) * 100;

    for (const opt of rubricSub.options) {
      if (opt.op === "gt" && pct > opt.minPct) return opt.id;
      if (opt.op === "gte" && pct >= opt.minPct) return opt.id;
      if (opt.op === "eq" && Math.abs(pct - opt.exactPct) < 0.001) return opt.id;
      if (opt.op === "gt_lte" && pct > opt.minPct && pct <= opt.maxPct) return opt.id;
      if (opt.op === "gte_lt" && pct >= opt.minPct && pct < opt.maxPct) return opt.id;
      if (opt.op === "gt_lt" && pct > opt.minPct && pct < opt.maxPct) return opt.id;
      if (opt.op === "lte" && pct <= opt.maxPct) return opt.id;
      if (opt.op === "lt" && pct < opt.maxPct) return opt.id;
    }
    return null;
  }

  if (rubricSub.type === "COUNT_TIERS") {
    const val = subVals[rubricSub.countKey];
    if (val === undefined || val === "" || val === null) return null;
    const count = Number(val);

    for (const opt of rubricSub.options) {
      if (opt.minCount !== undefined && opt.maxCount !== undefined) {
        if (count >= opt.minCount && count <= opt.maxCount) return opt.id;
      } else if (opt.minCount !== undefined) {
        if (count >= opt.minCount) return opt.id;
      } else if (opt.maxCount !== undefined) {
        if (count <= opt.maxCount) return opt.id;
      } else if (opt.exactCount !== undefined) {
        if (count === opt.exactCount) return opt.id;
      }
    }
    return null;
  }

  if (rubricSub.type === "CHECKLIST_ITEM") {
    const val = subVals[rubricSub.fieldKey];
    return val === true ? rubricSub.options[0]?.id : null;
  }

  if (rubricSub.type === "GRADE_SELECT") {
    const grade = subVals[rubricSub.fieldKey];
    if (!grade) return null;
    for (const opt of rubricSub.options) {
      if (opt.values && opt.values.includes(grade)) return opt.id;
    }
    return null;
  }

  if (rubricSub.type === "CURRENCY_TIERS") {
    const amt = subVals[rubricSub.fieldKey];
    if (amt === undefined || amt === "" || amt === null) return null;
    const numAmt = Number(amt);
    for (const opt of rubricSub.options) {
      if (opt.minVal !== undefined && opt.maxVal !== undefined) {
        if (numAmt >= opt.minVal && numAmt <= opt.maxVal) return opt.id;
      } else if (opt.minVal !== undefined) {
        if (numAmt >= opt.minVal) return opt.id;
      } else if (opt.exactVal !== undefined) {
        if (numAmt === opt.exactVal) return opt.id;
      }
    }
    return null;
  }

  return null;
}
