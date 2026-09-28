// Parameters definitions
export const PARAMETERS = [
  // Existing Parameters (Max 68)
  { id: 'p1', num: 1, name: 'Internship/Apprenticeship Embedded Degree Programmes', max: 4, type: 'existing', category: 'Academic' },
  { id: 'p2', num: 2, name: 'Courses offered in Indian Languages', max: 4, type: 'existing', category: 'Academic' },
  { id: 'p3', num: 3, name: 'Special Programmes in IKS', max: 4, type: 'existing', category: 'Academic' },
  { id: 'p4', num: 4, name: 'Targets achieved under IDP (2024-25 + 2025-26)', max: 6, type: 'existing', category: 'NEP Implementation' },
  { id: 'p5', num: 5, name: 'Accreditation Status (NAAC)', max: 8, type: 'existing', category: 'NEP Implementation' },
  { id: 'p6', num: 6, name: 'Academic Bank of Credits (ABC) Registered', max: 6, type: 'existing', category: 'Academic' },
  { id: 'p7', num: 7, name: 'Professor of Practice Appointed', max: 4, type: 'existing', category: 'NEP Implementation' },
  { id: 'p8', num: 8, name: 'Incubation/Startup Cell Performance', max: 4, type: 'existing', category: 'NEP Implementation' },
  { id: 'p9', num: 9, name: 'Academic/Research Collaboration with Foreign HEIs', max: 6, type: 'existing', category: 'Research' },
  { id: 'p10', num: 10, name: 'Alumni Connect Cell Functional', max: 4, type: 'existing', category: 'Welfare & Inclusion' },
  { id: 'p11', num: 11, name: 'Gender Parity Initiatives', max: 5, type: 'existing', category: 'Welfare & Inclusion' },
  { id: 'p12', num: 12, name: 'UGC Guidelines – Physical Fitness, Sports & Wellbeing', max: 5, type: 'existing', category: 'Welfare & Inclusion' },
  { id: 'p13', num: 13, name: 'Provision for Online Courses / MOOCs', max: 4, type: 'existing', category: 'Academic' },
  { id: 'p14', num: 14, name: 'Teacher Trained under MMTTC NEP Workshops', max: 4, type: 'existing', category: 'Welfare & Inclusion' },
  
  // New Parameters (Max 32)
  { id: 'p15', num: 15, name: 'Multidisciplinary Education', max: 8, type: 'new', category: 'Academic' },
  { id: 'p16', num: 16, name: 'Multiple Entry-Exit Operationalized', max: 2, type: 'new', category: 'Academic' },
  { id: 'p17', num: 17, name: 'Research Outcome – Patents Filed & Granted', max: 4, type: 'new', category: 'Research' },
  { id: 'p18', num: 18, name: 'Registration & Performance in NIRF', max: 2, type: 'new', category: 'Research' },
  { id: 'p19', num: 19, name: 'Outcome-Based Education (OBE) Implementation', max: 6, type: 'new', category: 'Academic' },
  { id: 'p20', num: 20, name: 'Utilization of Funds (Previous Financial Year)', max: 2, type: 'new', category: 'NEP Implementation' }
];

export const CATEGORIES = {
  Academic: { max: 38, params: ['p1', 'p2', 'p3', 'p6', 'p13', 'p15', 'p16', 'p19'] },
  Research: { max: 12, params: ['p9', 'p17', 'p18'] },
  'NEP Implementation': { max: 24, params: ['p4', 'p5', 'p7', 'p8', 'p20'] },
  'Welfare & Inclusion': { max: 18, params: ['p10', 'p11', 'p12', 'p14'] }
};

// Help helper to calculate total score
export const calculateTotalScore = (scores) => {
  return Object.values(scores).reduce((sum, val) => sum + (Number(val) || 0), 0);
};

// Help helper to get classification badge
export const getClassification = (score) => {
  if (score >= 91) return { name: 'Platinum', color: '#7C3AED', bg: 'bg-purple-100 text-purple-800 border-purple-300' };
  if (score >= 75) return { name: 'Gold', color: '#D97706', bg: 'bg-amber-100 text-amber-800 border-amber-300' };
  if (score >= 51) return { name: 'Silver', color: '#6B7280', bg: 'bg-slate-100 text-slate-800 border-slate-300' };
  return { name: 'No Award', color: '#EF4444', bg: 'bg-red-100 text-red-800 border-red-300' };
};
