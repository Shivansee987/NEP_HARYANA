import React from 'react';
import { HelpCircle, BookOpen, Shield, ShieldCheck, Mail, Phone, ExternalLink } from 'lucide-react';
import hshecLogo from '../../assets/hshec_logo.jpeg';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-slate-200/60 rounded-t-3xl mt-8 shadow-[0_-8px_30px_rgb(0,0,0,0.02)]">
      {/* Top Footer Section */}
      <div className="max-w-7xl mx-auto px-8 pt-12 pb-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-8 border-b border-slate-100">
          
          {/* Brand/About Section (5 cols) */}
          <div className="md:col-span-5 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-12 h-12 rounded-xl bg-white border border-slate-200/80 flex items-center justify-center shadow-sm p-1.5 overflow-hidden">
                <img src={hshecLogo} alt="HSHEC Logo" className="w-full h-full object-contain" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-800 tracking-tight leading-none">
                  Haryana State Higher Education Council
                </h3>
                <span className="text-[10px] text-blue-600 font-bold uppercase tracking-wider block mt-1">
                  Government of Haryana • NEP Excellence Awards
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed max-w-sm">
              The official portal for monitoring and evaluating higher education standards across institutions in Haryana in alignment with the National Education Policy.
            </p>
            <div className="flex items-center space-x-4 pt-1">
              <a
                href="mailto:info@hshec.gov.in"
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-blue-600 transition-colors"
              >
                <Mail className="w-3.5 h-3.5" />
                <span>info@hshec.gov.in</span>
              </a>
              <a
                href="tel:+911234567890"
                className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-blue-600 transition-colors"
              >
                <Phone className="w-3.5 h-3.5" />
                <span>+91-1234-567-890</span>
              </a>
            </div>
          </div>

          {/* Quick Navigation Column (3 cols) */}
          <div className="md:col-span-3 space-y-3">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              Evaluation Console
            </h4>
            <ul className="space-y-2 text-xs font-semibold text-slate-600">
              <li>
                <a href="/admin" className="hover:text-blue-600 transition-colors">
                  Overview Dashboard
                </a>
              </li>
              <li>
                <a href="/admin/institutions?stage=SUBMITTED" className="hover:text-blue-600 transition-colors">
                  Submitted Assessments
                </a>
              </li>
              <li>
                <a href="/admin/institutions" className="hover:text-blue-600 transition-colors">
                  Institutions
                </a>
              </li>
              <li>
                <a href="/admin/reports" className="hover:text-blue-600 transition-colors">
                  Reports
                </a>
              </li>
            </ul>
          </div>

          {/* Resources & Support Column (4 cols) */}
          <div className="md:col-span-4 space-y-3">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              Resources & Governance
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <ul className="space-y-2 text-xs font-semibold text-slate-600">
                <li>
                  <a href="#" onClick={(e) => e.preventDefault()} className="flex items-center gap-1 hover:text-blue-600 transition-colors">
                    <BookOpen className="w-3.5 h-3.5 text-slate-400" />
                    <span>NEP Policy</span>
                  </a>
                </li>
                <li>
                  <a href="#" onClick={(e) => e.preventDefault()} className="flex items-center gap-1 hover:text-blue-600 transition-colors">
                    <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
                    <span>Support Desk</span>
                  </a>
                </li>
                <li>
                  <a href="#" onClick={(e) => e.preventDefault()} className="flex items-center gap-1 hover:text-blue-600 transition-colors">
                    <Shield className="w-3.5 h-3.5 text-slate-400" />
                    <span>Security Audit</span>
                  </a>
                </li>
              </ul>
              <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl space-y-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">
                  Quick Access
                </span>
                <a
                  href="https://hshec.org"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1 text-[11px] font-semibold text-blue-600 hover:text-indigo-600 transition-colors"
                >
                  <span>Main Council Website</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>

        </div>

        {/* Bottom Footer Section */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-6">
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-3 text-center sm:text-left">
            <span className="text-[9px] font-bold text-blue-600 tracking-wider uppercase bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-full">
              Official Admin Portal
            </span>
            <p className="text-[11px] font-medium text-slate-400">
              © {currentYear} Haryana State Higher Education Council. All rights reserved.
            </p>
          </div>

          <div className="flex items-center gap-4 text-xs font-semibold text-slate-500">
            <div className="flex items-center gap-1.5 text-slate-400 bg-slate-50 border border-slate-100 rounded-full px-3 py-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-bold text-slate-600">v2.4.0 (Stable Build)</span>
            </div>
            <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-blue-600 transition-colors">
              Privacy Policy
            </a>
            <span className="text-slate-200">|</span>
            <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-blue-600 transition-colors">
              Terms of Service
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
