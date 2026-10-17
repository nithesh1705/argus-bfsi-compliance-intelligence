import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { LogOut, X } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../context/ThemeContext";

export const LogoutModal: React.FC = () => {
  const { isLogoutModalOpen, closeLogoutModal, logout } = useAuth();
  const { isDark } = useTheme();
  const navigate = useNavigate();

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isLogoutModalOpen) {
        closeLogoutModal();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isLogoutModalOpen, closeLogoutModal]);

  if (!isLogoutModalOpen) return null;

  const handleConfirm = async () => {
    closeLogoutModal();
    await logout();
    navigate("/login");
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="logout-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 dark:bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={closeLogoutModal}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-sm rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/90 dark:border-slate-800 shadow-2xl p-6 text-center animate-in zoom-in-95 duration-200"
      >
        {/* Close Button */}
        <button
          type="button"
          onClick={closeLogoutModal}
          aria-label="Close"
          className="absolute top-3.5 right-3.5 p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Cute Mascot Owl Illustration */}
        <div className="w-20 h-20 mx-auto mb-3 flex items-center justify-center">
          <svg
            viewBox="0 0 100 100"
            className="w-full h-full drop-shadow-md select-none"
            aria-hidden="true"
          >
            <defs>
              <linearGradient id="cuteOwlBody" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={isDark ? "#475569" : "#64748B"} />
                <stop offset="100%" stopColor={isDark ? "#1E293B" : "#334155"} />
              </linearGradient>
              <radialGradient id="cuteOwlEyes" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#FEF08A" />
                <stop offset="60%" stopColor="#F59E0B" />
                <stop offset="100%" stopColor="#D97706" />
              </radialGradient>
            </defs>

            {/* Ear Tuft Feathers */}
            <path
              d="M 28 32 Q 22 18 36 26"
              fill="none"
              stroke={isDark ? "#475569" : "#64748B"}
              strokeWidth="4"
              strokeLinecap="round"
            />
            <path
              d="M 72 32 Q 78 18 64 26"
              fill="none"
              stroke={isDark ? "#475569" : "#64748B"}
              strokeWidth="4"
              strokeLinecap="round"
            />

            {/* Round Chubby Body */}
            <ellipse
              cx="50"
              cy="58"
              rx="32"
              ry="30"
              fill="url(#cuteOwlBody)"
              stroke={isDark ? "#334155" : "#475569"}
              strokeWidth="2"
            />

            {/* Tummy Plate */}
            <ellipse
              cx="50"
              cy="64"
              rx="20"
              ry="18"
              fill={isDark ? "#0F172A" : "#F1F5F9"}
            />
            {/* Tummy feather chevron marks */}
            <path
              d="M 44 60 Q 50 63 56 60 M 45 67 Q 50 70 55 67"
              fill="none"
              stroke={isDark ? "#334155" : "#94A3B8"}
              strokeWidth="1.8"
              strokeLinecap="round"
            />

            {/* Waving Wing on Left */}
            <path
              d="M 20 54 Q 10 42 16 34 Q 22 38 23 48"
              fill={isDark ? "#334155" : "#475569"}
              stroke={isDark ? "#475569" : "#64748B"}
              strokeWidth="1.5"
            />
            {/* Resting Wing on Right */}
            <path
              d="M 78 50 Q 86 60 76 74"
              fill="none"
              stroke={isDark ? "#475569" : "#64748B"}
              strokeWidth="3.5"
              strokeLinecap="round"
            />

            {/* Big Cute Expressive Eyes */}
            {/* Left Eye */}
            <circle cx="38" cy="42" r="10" fill="#0F172A" stroke={isDark ? "#334155" : "#CBD5E1"} strokeWidth="1.5" />
            <circle cx="38" cy="42" r="7.5" fill="url(#cuteOwlEyes)" />
            <circle cx="38" cy="42" r="4.5" fill="#090E17" />
            <circle cx="40.5" cy="39.5" r="2" fill="#FFFFFF" />

            {/* Right Eye (Sad/Questioning Tilt) */}
            <circle cx="62" cy="42" r="10" fill="#0F172A" stroke={isDark ? "#334155" : "#CBD5E1"} strokeWidth="1.5" />
            <circle cx="62" cy="42" r="7.5" fill="url(#cuteOwlEyes)" />
            <circle cx="62" cy="42" r="4.5" fill="#090E17" />
            <circle cx="64.5" cy="39.5" r="2" fill="#FFFFFF" />

            {/* Cute Orange Beak */}
            <polygon points="46,47 54,47 50,54" fill="#F59E0B" />

            {/* Tiny Talons */}
            <path
              d="M 40 87 Q 42 91 44 87 M 56 87 Q 58 91 60 87"
              fill="none"
              stroke="#F59E0B"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </svg>
        </div>

        {/* Title & Description */}
        <h3
          id="logout-modal-title"
          className="text-base font-bold text-slate-900 dark:text-slate-100 mb-1"
        >
          Sign out of ARGUS?
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-6 leading-relaxed">
          Are you sure you want to end your compliance session? You will be returned to the login screen.
        </p>

        {/* Action Buttons: Yes / No */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={closeLogoutModal}
            className="flex-1 py-2.5 px-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700/80 transition-colors cursor-pointer"
          >
            No, Stay
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-xs font-semibold text-white shadow-sm hover:shadow transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
          >
            <LogOut className="w-3.5 h-3.5 shrink-0" />
            <span>Yes, Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
};
