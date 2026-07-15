import EmptyState from "../EmptyState/EmptyState";
import styles from "./charts.module.css";

const PALETTE = ["#2563eb", "#16a34a", "#d97706", "#7c3aed", "#dc2626", "#0891b2"];

export default function DonutChart({ title, subtitle, data = [] }) {
  const items = Array.isArray(data) ? data.filter((d) => Number(d.count) > 0) : [];
  const total = items.reduce((sum, d) => sum + (Number(d.count) || 0), 0);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;

  let offset = 0;
  const segments = items.map((item, index) => {
    const value = Number(item.count) || 0;
    const pct = total > 0 ? value / total : 0;
    const dash = pct * circumference;
    const segment = {
      ...item,
      dash,
      offset,
      color: PALETTE[index % PALETTE.length],
    };
    offset += dash;
    return segment;
  });

  return (
    <div className={styles.card}>
      {title && <h3 className={styles.title}>{title}</h3>}
      {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
      <div className={styles.body}>
        {items.length === 0 ? (
          <EmptyState
            title="No tier data"
            description="College tier distribution will appear after scoring is completed."
            icon="chart"
          />
        ) : (
          <div className={styles.donutWrap}>
            <svg className={styles.donut} viewBox="0 0 120 120">
              <circle className={styles.donutBg} cx="60" cy="60" r={radius} />
              {segments.map((seg) => (
                <circle
                  key={seg.label ?? seg.range ?? seg.status}
                  className={styles.donutSegment}
                  cx="60"
                  cy="60"
                  r={radius}
                  stroke={seg.color}
                  strokeDasharray={`${seg.dash} ${circumference - seg.dash}`}
                  strokeDashoffset={-seg.offset}
                />
              ))}
            </svg>
            <div className={styles.legend}>
              {segments.map((seg) => (
                <div key={seg.label ?? seg.range ?? seg.status} className={styles.legendItem}>
                  <span className={styles.legendDot} style={{ background: seg.color }} />
                  <span>
                    {seg.label ?? seg.range ?? seg.status}: {seg.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
