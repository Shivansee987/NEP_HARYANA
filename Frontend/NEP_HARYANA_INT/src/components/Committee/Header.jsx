import { Calendar } from 'lucide-react';
import { useAuth } from '../../context/AuthContext.jsx';

const Header = ({ title }) => {
  const { user } = useAuth();
  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  const name = user?.fullName || user?.full_name || "Committee Officer";
  const role = user?.role === 'committee_chair' ? 'Committee Chair' : 'Screening Committee';

  const getInitials = (nameStr) => {
    if (!nameStr) return "CO";
    const parts = nameStr.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return nameStr.substring(0, 2).toUpperCase();
  };

  const initials = getInitials(name);

  return (
    <header className="h-16 bg-white border-b border-slate-200/80 flex items-center justify-between px-8 fixed top-0 right-0 left-20 peer-hover:left-64 z-10 shadow-sm shadow-slate-100 transition-all duration-300 ease-in-out">
      <div className="flex items-center space-x-4">
        <h2 className="text-xl font-bold text-slate-800 tracking-tight">{title}</h2>
      </div>

      <div className="flex items-center space-x-6">
        {/* Date Display */}
        <div className="hidden md:flex items-center text-xs font-semibold text-slate-500 bg-slate-50 border border-slate-200/60 rounded-full py-1.5 px-3.5 space-x-2">
          <Calendar className="w-4 h-4 text-slate-400" />
          <span>{today}</span>
        </div>

        {/* User profile dropdown */}
        <div className="flex items-center space-x-3 border-l border-slate-200 pl-6">
          <div className="w-9 h-9 rounded-lg bg-orange-100 border border-orange-200 flex items-center justify-center text-orange-600 font-bold text-sm">
            {initials}
          </div>
          <div className="hidden lg:block text-left">
            <span className="block text-xs font-bold text-slate-800 leading-tight">{name}</span>
            <span className="block text-[10px] text-slate-400 font-semibold leading-none">{role}</span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
