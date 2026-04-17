"use client";

import { useState, useEffect } from "react";
import {
  fetchTables,
  fetchTableSchema,
  fetchTableData,
  createLLMProvider,
  updateLLMProvider,
  deleteLLMProvider,
  createLLMModel,
  updateLLMModel,
  deleteLLMModel,
} from "@/lib/api";
import type { TableSchema, TableDataResponse } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { Database, Loader2, AlertCircle } from "lucide-react";

export default function Home() {
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [schema, setSchema] = useState<TableSchema | null>(null);
  const [data, setData] = useState<TableDataResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentOffset, setCurrentOffset] = useState(0);

  // Fetch available tables on mount and set jobs as default
  useEffect(() => {
    const loadTables = async () => {
      try {
        const tableList = await fetchTables();
        setTables(tableList);

        // Set 'jobs' as default table if it exists
        if (tableList.includes("jobs")) {
          setSelectedTable("jobs");
        } else if (tableList.length > 0) {
          // Fallback to first table if jobs doesn't exist
          setSelectedTable(tableList[0]);
        }
      } catch (err) {
        setError(
          `Failed to load tables: ${err instanceof Error ? err.message : "Unknown error"}`
        );
      }
    };
    loadTables();
  }, []);

  // Load table data when selection changes
  useEffect(() => {
    if (!selectedTable) {
      setSchema(null);
      setData(null);
      setCurrentOffset(0);
      return;
    }

    const loadTableData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [schemaData, tableData] = await Promise.all([
          fetchTableSchema(selectedTable),
          fetchTableData(selectedTable, 50, currentOffset),
        ]);
        setSchema(schemaData);
        setData(tableData);
      } catch (err) {
        setError(
          `Failed to load table data: ${err instanceof Error ? err.message : "Unknown error"}`
        );
      } finally {
        setLoading(false);
      }
    };

    loadTableData();
  }, [selectedTable, currentOffset]);

  const handleTableChange = (table: string) => {
    setSelectedTable(table);
    setCurrentOffset(0);
  };

  const handlePageChange = (newOffset: number) => {
    setCurrentOffset(newOffset);
  };

  // Refresh table data
  const handleRefresh = async () => {
    if (!selectedTable) return;
    setLoading(true);
    setError(null);
    try {
      const tableData = await fetchTableData(selectedTable, 50, currentOffset);
      setData(tableData);
    } catch (err) {
      setError(
        `Failed to refresh data: ${err instanceof Error ? err.message : "Unknown error"}`
      );
    } finally {
      setLoading(false);
    }
  };

  // Save handler for editable tables
  const handleSave = async (rows: any[]) => {
    if (selectedTable === "llm_providers") {
      // Save LLM providers
      for (const row of rows) {
        if (row._isNew) {
          // Create new provider
          await createLLMProvider(row.llm_provider_name);
        } else if (row._isModified) {
          // Update existing provider
          await updateLLMProvider(row.llm_provider_id, row.llm_provider_name);
        }
      }
    } else if (selectedTable === "llm_models") {
      // Save LLM models
      for (const row of rows) {
        if (row._isNew) {
          // Create new model
          await createLLMModel(row.llm_model_name, parseInt(row.llm_provider_id));
        } else if (row._isModified) {
          // Update existing model
          const modelName = row.llm_model_name;
          const providerId = parseInt(row.llm_provider_id);
          await updateLLMModel(row.llm_model_id, modelName, providerId);
        }
      }
    }

    // Refresh data after save
    await handleRefresh();
  };

  // Delete handler for editable tables
  const handleDelete = async (id: number) => {
    if (selectedTable === "llm_providers") {
      await deleteLLMProvider(id);
    } else if (selectedTable === "llm_models") {
      await deleteLLMModel(id);
    }

    // Refresh data after delete
    await handleRefresh();
  };

  // Check if current table is editable
  const isEditable = selectedTable === "llm_providers" || selectedTable === "llm_models";

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Compact Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-600" />
              <h1 className="text-lg font-semibold text-gray-900">
                Database Admin
              </h1>
            </div>

            {/* Table Selector in Header */}
            <div className="flex items-center gap-3">
              <label
                htmlFor="table-select"
                className="text-sm font-medium text-gray-700"
              >
                Table:
              </label>
              <select
                id="table-select"
                value={selectedTable}
                onChange={(e) => handleTableChange(e.target.value)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              >
                {tables.map((table) => (
                  <option key={table} value={table}>
                    {table}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Compact */}
      <div className="container mx-auto px-4 py-3">
        {error && (
          <div className="flex items-center gap-2 p-3 mb-3 bg-red-50 border border-red-200 rounded-md text-red-800">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            <p className="text-sm">{error}</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-20 bg-white rounded-lg border border-gray-200">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <span className="ml-2 text-sm text-gray-600">Loading table data...</span>
          </div>
        )}

        {!selectedTable && !loading && !error && (
          <div className="text-center py-20 bg-white rounded-lg border border-gray-200">
            <Database className="h-12 w-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-600 text-sm">
              Select a table to view its data
            </p>
            <p className="text-gray-500 text-xs mt-1">
              {tables.length} tables available
            </p>
          </div>
        )}

        {!loading && !error && schema && data && (
          <DataTable
            schema={schema}
            data={data}
            onPageChange={handlePageChange}
            editable={isEditable}
            tableName={selectedTable}
            onSave={handleSave}
            onDelete={handleDelete}
            onRefresh={handleRefresh}
          />
        )}
      </div>
    </main>
  );
}
