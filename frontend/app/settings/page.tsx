"use client";

import { useState, useEffect } from "react";
import {
  getSetting,
  upsertSetting,
  type Setting,
  type LLMModel,
} from "@/lib/api";
import { Settings as SettingsIcon, Save, Loader2, AlertCircle, CheckCircle } from "lucide-react";

export default function SettingsPage() {
  const [atsModelId, setAtsModelId] = useState<number | null>(null);
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load settings and models on mount
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        // Fetch all LLM models
        const response = await fetch("/api/admin/llm-models");
        if (!response.ok) {
          throw new Error(`Failed to fetch models: ${response.statusText}`);
        }
        const modelsData: LLMModel[] = await response.json();
        setModels(modelsData);

        // Fetch ATS model setting
        const atsSetting = await getSetting("ats_matching_model");
        if (atsSetting && atsSetting.setting_value.llm_model_id) {
          setAtsModelId(atsSetting.setting_value.llm_model_id);
        }
      } catch (err) {
        setError(
          `Failed to load settings: ${err instanceof Error ? err.message : "Unknown error"}`
        );
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleSave = async () => {
    if (atsModelId === null) {
      setError("Please select an ATS matching model");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await upsertSetting("ats_matching_model", {
        llm_model_id: atsModelId,
      });
      setSuccessMessage("Settings saved successfully!");

      // Clear success message after 3 seconds
      setTimeout(() => {
        setSuccessMessage(null);
      }, 3000);
    } catch (err) {
      setError(
        `Failed to save settings: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center gap-2">
            <SettingsIcon className="h-5 w-5 text-blue-600" />
            <h1 className="text-lg font-semibold text-gray-900">Settings</h1>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6 max-w-4xl">
        {/* Error Alert */}
        {error && (
          <div className="flex items-center gap-2 p-3 mb-4 bg-red-50 border border-red-200 rounded-md text-red-800">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Success Alert */}
        {successMessage && (
          <div className="flex items-center gap-2 p-3 mb-4 bg-green-50 border border-green-200 rounded-md text-green-800">
            <CheckCircle className="h-4 w-4 flex-shrink-0" />
            <p className="text-sm">{successMessage}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-20 bg-white rounded-lg border border-gray-200">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <span className="ml-2 text-sm text-gray-600">Loading settings...</span>
          </div>
        )}

        {/* Settings Form */}
        {!loading && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-4">
                LLM Configuration
              </h2>

              {/* ATS Matching Model Selector */}
              <div className="mb-6">
                <label
                  htmlFor="ats-model"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  ATS Matching Model
                </label>
                <p className="text-xs text-gray-500 mb-3">
                  Select the LLM model to use for ATS (Applicant Tracking System) matching and job description analysis.
                </p>
                <select
                  id="ats-model"
                  value={atsModelId ?? ""}
                  onChange={(e) => setAtsModelId(parseInt(e.target.value))}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
                  disabled={models.length === 0}
                >
                  <option value="">Select a model...</option>
                  {models.map((model) => (
                    <option key={model.llm_model_id} value={model.llm_model_id}>
                      {model.llm_provider_name} - {model.llm_model_name}
                    </option>
                  ))}
                </select>
                {models.length === 0 && (
                  <p className="text-xs text-amber-600 mt-2">
                    No LLM models available. Please add models in the Database Admin page first.
                  </p>
                )}
              </div>

              {/* Future Settings Placeholder */}
              <div className="border-t border-gray-200 pt-6">
                <p className="text-xs text-gray-500 italic">
                  Additional configuration options will be added here in the future.
                </p>
              </div>
            </div>

            {/* Save Button Footer */}
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 rounded-b-lg">
              <div className="flex items-center justify-end">
                <button
                  onClick={handleSave}
                  disabled={saving || atsModelId === null}
                  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4" />
                      Save Settings
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
