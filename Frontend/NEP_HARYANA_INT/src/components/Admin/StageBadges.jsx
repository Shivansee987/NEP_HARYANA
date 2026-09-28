import { STAGES } from '../../utils/stateStages';

export const StageBadge = ({ stage }) => {
  const s = STAGES[stage] || STAGES.UNDER_REVIEW;
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border whitespace-nowrap ${s.cls}`}>
      {s.label}
    </span>
  );
};

export const TypeBadge = ({ type }) => (
  <span
    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border whitespace-nowrap ${
      type === 'UNIVERSITY'
        ? 'bg-[#fbf5ee] text-[#8a6a3f] border-[#ebdcd0]'
        : 'bg-[#eaded2]/60 text-[#600b0b] border-[#ebdcd0]'
    }`}
  >
    {type === 'UNIVERSITY' ? 'University' : 'College'}
  </span>
);
