import React, { useState, useEffect } from "react";
import {
  Settings as SettingsIcon,
  Sun,
  Moon,
  Sliders,
  CheckCircle2,
  Save,
  Palette,
} from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import {
  useSettings,
  useUpdateSettings,
} from "../../services/settingsService";
import { LoadingState } from "../../components/shared/LoadingState";

export const Settings: React.FC = () => {
  const { isDark, setTheme } = useTheme();

  const { data: settingsData, isLoading: settingsLoading } = useSettings();
  const updateSettingsMutation = useUpdateSettings();

  const [confidenceThreshold, setConfidenceThreshold] = useState<number>(75);
  const [autoEscalateThreshold, setAutoEscalateThreshold] = useState<number>(90);
  const [savedNotice, setSavedNotice] = useState(false);

  useEffect(() => {
    if (settingsData?.confidence_threshold !== undefined) {
      const val = Math.round(settingsData.confidence_threshold * 100);
      setConfidenceThreshold(val);
    }
  }, [settingsData]);

  const handleToggleTheme = (mode: "light" | "dark") => {
    setTheme(mode);
  };

  const handleSaveSettings = () => {
    updateSettingsMutation.mutate(
      {
        confidence_threshold: confidenceThreshold / 100,
      },
      {
        onSuccess: () => {
          setSavedNotice(true);
          setTimeout(() => setSavedNotice(false), 3500);
        },
      }
    );
  };

  if (settingsLoading) {
    return <LoadingState message="Loading system configuration and sensitivity parameters..." />;
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <SettingsIcon className="w-5 h-5 text-slate-700 dark:text-slate-300" />
              Settings & Preferences
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Configure interface appearance, surveillance sensitivity thresholds, and automated compliance review parameters
          </p>
        </div>

        {savedNotice && (
          <div className="px-3 py-1.5 rounded bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-mono flex items-center gap-1.5 shadow-sm">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            <span>Parameters saved to Cloud SQL</span>
          </div>
        )}
      </div>

      {/* Section 1: Interface Appearance & Contrast */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Palette className="w-4 h-4 text-blue-500" />
            Interface Appearance & Contrast
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Select high-legibility theme mode for regulatory audit review and case triage
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => handleToggleTheme("light")}
            className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3.5 cursor-pointer ${
              !isDark
                ? "border-blue-600 bg-blue-50/50 dark:border-blue-400 ring-2 ring-blue-600/20 shadow-sm"
                : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
            }`}
          >
            <div className={`p-2 rounded-lg ${!isDark ? "bg-amber-100 text-amber-600" : "bg-slate-100 dark:bg-slate-800 text-slate-400"}`}>
              <Sun className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Light Audit Mode (Default)
              </p>
              <span className="text-xs text-slate-500 mt-0.5 block">
                Restrained off-white slate background with high-contrast typography
              </span>
            </div>
          </button>

          <button
            type="button"
            onClick={() => handleToggleTheme("dark")}
            className={`p-4 rounded-xl border text-left transition-all flex items-start gap-3.5 cursor-pointer ${
              isDark
                ? "border-blue-500 bg-slate-950 dark:border-blue-500 ring-2 ring-blue-500/20 shadow-sm"
                : "border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700"
            }`}
          >
            <div className={`p-2 rounded-lg ${isDark ? "bg-blue-950 text-blue-400 border border-blue-800" : "bg-slate-100 text-slate-400"}`}>
              <Moon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Dark Mode
              </p>
              <span className="text-xs text-slate-500 mt-0.5 block">
                Low-fatigue dark slate base for extended investigative sessions
              </span>
            </div>
          </button>
        </div>
      </div>

      {/* Section 2: Surveillance Sensitivity & Confidence Thresholds */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
        <div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Sliders className="w-4 h-4 text-indigo-500" />
            Surveillance Sensitivity & Confidence Thresholds
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Calibrate detection thresholds below which findings dynamically route to manual human review
          </p>
        </div>

        {/* Slider 1 */}
        <div className="space-y-2.5 p-4 rounded-lg bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              Minimum Case Flagging Confidence Floor:
            </span>
            <span className="font-mono font-bold text-sm text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/60 px-2 py-0.5 rounded border border-blue-200 dark:border-blue-900">
              {confidenceThreshold}%
            </span>
          </div>
          <input
            type="range"
            min={50}
            max={98}
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
            className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
          />
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block">
            Acoustic extractions scoring below {confidenceThreshold}% are tagged with <span className="font-semibold text-amber-600 dark:text-amber-400">NEEDS HUMAN REVIEW</span>.
          </span>
        </div>

        {/* Slider 2 */}
        <div className="space-y-2.5 p-4 rounded-lg bg-slate-50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700 dark:text-slate-300">
              Automated CCO Escalation Threshold (HIGH Severity):
            </span>
            <span className="font-mono font-bold text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/60 px-2 py-0.5 rounded border border-red-200 dark:border-red-900">
              {autoEscalateThreshold}%
            </span>
          </div>
          <input
            type="range"
            min={75}
            max={99}
            value={autoEscalateThreshold}
            onChange={(e) => setAutoEscalateThreshold(Number(e.target.value))}
            className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-red-600"
          />
          <span className="text-[11px] text-slate-500 dark:text-slate-400 block">
            Findings with severity <span className="font-semibold text-red-600 dark:text-red-400">HIGH</span> and confidence &ge; {autoEscalateThreshold}% trigger priority surveillance dispatch.
          </span>
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={handleSaveSettings}
            disabled={updateSettingsMutation.isPending}
            className="px-4 py-2 bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 rounded-lg text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-800 dark:hover:bg-slate-200 transition-colors shadow-sm cursor-pointer disabled:opacity-50"
          >
            <Save className="w-3.5 h-3.5" />
            {updateSettingsMutation.isPending ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>
    </div>
  );
};
