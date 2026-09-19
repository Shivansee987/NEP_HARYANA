import { Outlet } from "react-router-dom";

/**
 * UniversityLayout — Seamless wrapper delegating layout to the University Workspace,
 * matching the College Dashboard's full-height persistent sidebar and clean aesthetics.
 */
const UniversityLayout = () => {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
};

export default UniversityLayout;
