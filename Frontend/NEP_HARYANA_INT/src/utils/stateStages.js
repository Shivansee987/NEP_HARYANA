// Lifecycle stages returned by GET /api/v1/admin/institutions/ (see StateOverviewService on the backend).
export const STAGES = {
  NOT_STARTED:            { label: 'Not Started',            cls: 'bg-slate-100 text-slate-600 border-slate-200' },
  IN_PROGRESS:            { label: 'Filling In',             cls: 'bg-sky-50 text-sky-700 border-sky-200' },
  RETURNED:               { label: 'Returned',               cls: 'bg-orange-50 text-orange-700 border-orange-200' },
  SUBMITTED:              { label: 'Submitted',              cls: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  UNDER_REVIEW:           { label: 'Under Review',           cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  AWAITING_CERTIFICATION: { label: 'Awaiting Certification', cls: 'bg-violet-50 text-violet-700 border-violet-200' },
  CERTIFIED:              { label: 'Certified',              cls: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  REJECTED:               { label: 'Rejected',               cls: 'bg-red-50 text-red-700 border-red-200' },
};

export const formatScore = (score) => (score == null ? '—' : `${Number(score).toFixed(1)} / 100`);
