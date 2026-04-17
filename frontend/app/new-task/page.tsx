"use client";

import { useState, useEffect } from "react";
import { Plus, AlertCircle, CheckCircle2, Loader2, User } from "lucide-react";
import { fetchProfiles, bulkCreateJobs, Profile, BulkJobsResponse } from "@/lib/api";

export default function NewTaskPage() {
  const [urls, setUrls] = useState("");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<number | null>(null);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [response, setResponse] = useState<BulkJobsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch profiles on mount
  useEffect(() => {
    const loadProfiles = async () => {
      try {
        const data = await fetchProfiles();
        setProfiles(data);

        // Set default profile (first one)
        if (data.length > 0) {
          setSelectedProfileId(data[0].profile_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load profiles");
      } finally {
        setIsLoadingProfiles(false);
      }
    };

    loadProfiles();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setResponse(null);

    try {
      // Validate profile selection
      if (selectedProfileId === null) {
        setError("Please select a profile");
        setIsSubmitting(false);
        return;
      }

      // Parse URLs (one per line)
      const urlList = urls
        .split("\n")
        .map((url) => url.trim())
        .filter((url) => url.length > 0);

      if (urlList.length === 0) {
        setError("Please enter at least one URL");
        setIsSubmitting(false);
        return;
      }

      // Submit to backend
      const data = await bulkCreateJobs({
        urls: urlList,
        profile_id: selectedProfileId,
      });

      setResponse(data);

      // Clear form if all succeeded
      if (data.summary.created > 0 && data.summary.failed === 0) {
        setUrls("");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-6">
        <div className="max-w-4xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-2xl font-semibold text-gray-900 mb-2">
              Add New Jobs
            </h1>
            <p className="text-sm text-gray-600">
              Submit job URLs to create new records in the database. Jobs will
              be processed through the lifecycle orchestrator with status{" "}
              <code className="px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-xs font-mono">
                new_url
              </code>
            </p>
          </div>

          {/* Form */}
          <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
            <form onSubmit={handleSubmit}>
              {/* Profile Selection */}
              <div className="mb-6">
                <label
                  htmlFor="profile"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    Select Profile
                  </div>
                </label>
                {isLoadingProfiles ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading profiles...
                  </div>
                ) : profiles.length === 0 ? (
                  <div className="text-sm text-red-600">
                    No profiles found. Please create a profile first.
                  </div>
                ) : (
                  <select
                    id="profile"
                    value={selectedProfileId ?? ""}
                    onChange={(e) => setSelectedProfileId(Number(e.target.value))}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    disabled={isSubmitting}
                    required
                  >
                    {profiles.map((profile) => (
                      <option key={profile.profile_id} value={profile.profile_id}>
                        {profile.first_name} {profile.last_name} ({profile.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* URL Textarea */}
              <label
                htmlFor="urls"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Job URLs (one per line)
              </label>
              <textarea
                id="urls"
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
                placeholder="https://example.com/job/1&#10;https://example.com/job/2&#10;https://example.com/job/3"
                rows={10}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                disabled={isSubmitting}
              />
              <div className="mt-4 flex items-center justify-between">
                <p className="text-xs text-gray-500">
                  Enter job posting URLs, one per line
                </p>
                <button
                  type="submit"
                  disabled={isSubmitting || !urls.trim() || selectedProfileId === null || isLoadingProfiles}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Creating Jobs...
                    </>
                  ) : (
                    <>
                      <Plus className="h-4 w-4" />
                      Create Jobs
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-medium text-red-900 mb-1">
                    Error
                  </h3>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Success Summary */}
          {response && (
            <div className="space-y-4">
              {/* Summary Card */}
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <div className="flex items-start gap-3 mb-4">
                  <CheckCircle2 className="h-6 w-6 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Submission Complete
                    </h3>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <div className="text-2xl font-bold text-gray-900">
                          {response.summary.total_submitted}
                        </div>
                        <div className="text-xs text-gray-600">Submitted</div>
                      </div>
                      <div className="bg-green-50 rounded-lg p-3">
                        <div className="text-2xl font-bold text-green-700">
                          {response.summary.created}
                        </div>
                        <div className="text-xs text-green-700">Created</div>
                      </div>
                      <div className="bg-red-50 rounded-lg p-3">
                        <div className="text-2xl font-bold text-red-700">
                          {response.summary.failed}
                        </div>
                        <div className="text-xs text-red-700">Failed</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Created Jobs */}
              {response.created.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">
                    Created Jobs ({response.created.length})
                  </h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {response.created.map((job) => (
                      <div
                        key={job.id}
                        className="flex items-center gap-3 p-3 bg-green-50 rounded-lg border border-green-200"
                      >
                        <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-mono text-gray-900 truncate">
                            {job.url}
                          </p>
                        </div>
                        <span className="text-xs font-medium text-green-700 bg-green-100 px-2 py-1 rounded">
                          ID: {job.id}
                        </span>
                        <span className="text-xs font-medium text-blue-700 bg-blue-100 px-2 py-1 rounded">
                          {job.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Failed Jobs */}
              {response.failed.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-6">
                  <h4 className="text-sm font-semibold text-gray-900 mb-3">
                    Failed Jobs ({response.failed.length})
                  </h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {response.failed.map((job, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-red-50 rounded-lg border border-red-200"
                      >
                        <div className="flex items-start gap-3">
                          <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-mono text-gray-900 truncate mb-1">
                              {job.url}
                            </p>
                            <p className="text-xs text-red-700">{job.reason}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
