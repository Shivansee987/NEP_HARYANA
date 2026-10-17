/**
 * Landing page for Empowered Committee members and chairs.
 *
 * The Empowered Committee review stage (Screening -> Empowered -> Certification) has not been approved as a
 * workflow rule yet, so the backend grants these roles no review actions. This page states that plainly instead
 * of showing an empty or looping console; it offers no actions of its own (FIN-05).
 */
import { useNavigate } from "react-router-dom";
import { Clock, LogOut, ShieldCheck } from "lucide-react";
import { useAuth } from "../../context/AuthContext.jsx";

const EmpoweredCommitteeHome = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const roleLabel = user?.role === "empowered_committee_chair" ? "Empowered Committee Chair" : "Empowered Committee Member";

  const handleLogout = async () => {
    await logout();
    navigate("/auth/admin/login", { replace: true });
  };

  return (
    <main className="min-h-screen bg-[#faf6f2] flex items-center justify-center p-6">
      <section className="bg-white max-w-xl w-full rounded-2xl border border-[#ebdcd0] shadow-sm p-8 space-y-5">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-[#600b0b]" />
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{roleLabel}</p>
            <h1 className="text-lg font-bold text-slate-900">{user?.full_name || "Welcome"}</h1>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900 flex gap-3">
          <Clock className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="space-y-2">
            <p className="font-bold">The Empowered Committee stage is not active yet.</p>
            <p className="text-xs leading-relaxed">
              HSHEC has not yet approved the rules for the Empowered Committee review stage, so there are no
              assessments for you to act on. Screening Committee reviews and certification continue under the
              current rules. You will be able to use this console once the stage is approved and enabled.
            </p>
          </div>
        </div>
        <button type="button" onClick={handleLogout}
          className="inline-flex items-center gap-2 text-xs font-bold text-slate-700 border border-slate-200 hover:bg-slate-50 rounded-lg px-3 py-2">
          <LogOut className="w-4 h-4" /> Sign out
        </button>
      </section>
    </main>
  );
};

export default EmpoweredCommitteeHome;
