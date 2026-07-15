import BarChart from "../../../components/admin/charts/BarChart";
import DonutChart from "../../../components/admin/charts/DonutChart";
import TrendChart from "../../../components/admin/charts/TrendChart";
import StatsCard from "../../../components/admin/StatsCard/StatsCard";
import InstitutionList from "../../../components/admin/InstitutionList/InstitutionList";
import LoadingState from "../../../components/admin/LoadingState/LoadingState";
import styles from "../AdminDashboard.module.css";

export default function AnalyticsSection({ analytics, stats, loading, error }) {
  if (loading) {
    return <LoadingState message="Loading analytics..." />;
  }

  const awardData = Object.entries(analytics?.award_distribution || stats?.award_distribution || {}).map(
    ([label, count]) => ({ label, count }),
  );

  const topInstitutions = (analytics?.top_institutions || []).map((inst) => ({
    college_id: inst.aishe_code,
    name: inst.institution_name,
    aishe_code: inst.aishe_code,
    has_application: true,
    application_status: "submitted",
    percentage: inst.percentage,
    award_category: inst.award_category,
  }));

  return (
    <>
      {error && <div className={styles.errorBanner}>{error}</div>}

      <div className={styles.kpiGrid}>
        <StatsCard
          label="Total Submissions"
          value={stats?.submitted_applications ?? 0}
          accent="green"
        />
        <StatsCard
          label="Registered Principals"
          value={stats?.registered_principals ?? 0}
          accent="blue"
        />
        <StatsCard
          label="Average Score"
          value={
            stats?.average_score_percentage != null
              ? `${stats.average_score_percentage}%`
              : "—"
          }
          accent="purple"
        />
        <StatsCard
          label="Active Applications"
          value={
            (stats?.in_progress_applications ?? 0) + (stats?.draft_applications ?? 0)
          }
          accent="amber"
        />
      </div>

      <div className={styles.chartsGridThree}>
        <BarChart
          title="Score Ranges"
          subtitle="Distribution of institution scores"
          data={(analytics?.score_distribution || []).map((d) => ({
            label: d.range,
            count: d.count,
          }))}
          labelKey="label"
          valueKey="count"
          colorIndex={1}
        />
        <DonutChart
          title="College Tier Distribution"
          subtitle="Distribution of institutions by tier"
          data={awardData}
        />
        <TrendChart
          title="Submission Trend"
          subtitle="Monthly application starts"
          data={analytics?.submission_trend || []}
        />
      </div>

      <div className={styles.sectionCard}>
        <h3>Top Performing Institutions</h3>
        <InstitutionList institutions={topInstitutions} compact />
      </div>
    </>
  );
}
