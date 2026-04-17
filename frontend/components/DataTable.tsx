"use client";

import { useState, useRef, useEffect } from "react";
import { TableSchema, TableDataResponse } from "@/lib/api";
import { ChevronLeft, ChevronRight, ArrowUpDown, ArrowUp, ArrowDown, Filter, Edit, Plus, Save, X } from "lucide-react";

interface DataTableProps {
  schema: TableSchema;
  data: TableDataResponse;
  onPageChange: (offset: number) => void;
  // Edit mode props
  editable?: boolean;
  tableName?: string;
  onSave?: (rows: any[]) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
  onRefresh?: () => void;
}

type SortDirection = "asc" | "desc" | null;

interface EditableRow {
  [key: string]: any;
  _isNew?: boolean;
  _isModified?: boolean;
}

export function DataTable({
  schema,
  data,
  onPageChange,
  editable = false,
  tableName = "",
  onSave,
  onDelete,
  onRefresh
}: DataTableProps) {
  const currentPage = Math.floor(data.offset / data.limit) + 1;
  const totalPages = Math.ceil(data.total_count / data.limit);

  // Column widths state (dynamic resizing)
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const resizeStartX = useRef<number>(0);
  const resizeStartWidth = useRef<number>(0);

  // Sorting and filtering state
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [showFilterRow, setShowFilterRow] = useState(false);

  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [editableData, setEditableData] = useState<EditableRow[]>([]);
  const [originalData, setOriginalData] = useState<EditableRow[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [providers, setProviders] = useState<any[]>([]); // For llm_models dropdown

  // Initialize column widths
  useEffect(() => {
    const initialWidths: Record<string, number> = {};
    schema.columns.forEach((column) => {
      if (column.type.includes("TEXT")) initialWidths[column.name] = 300;
      else if (column.type.includes("TIMESTAMP")) initialWidths[column.name] = 180;
      else if (column.type.includes("VARCHAR")) initialWidths[column.name] = 150;
      else initialWidths[column.name] = 120;
    });
    setColumnWidths(initialWidths);
  }, [schema]);

  // Load providers for llm_models table
  useEffect(() => {
    if (tableName === "llm_models" && isEditMode) {
      fetch("/api/admin/llm-providers")
        .then(res => res.json())
        .then(data => setProviders(data))
        .catch(err => console.error("Failed to load providers:", err));
    }
  }, [tableName, isEditMode]);

  // Reset editable data when exiting edit mode or data changes
  useEffect(() => {
    if (!isEditMode) {
      setEditableData([]);
      setOriginalData([]);
    }
  }, [isEditMode]);

  // Note: Removed useEffect that was resetting editableData
  // Edit mode initialization now happens in handleEditClick and handleAddNewRow

  const handlePrevious = () => {
    if (data.offset > 0) {
      onPageChange(Math.max(0, data.offset - data.limit));
    }
  };

  const handleNext = () => {
    if (data.has_more) {
      onPageChange(data.offset + data.limit);
    }
  };

  // Column resize handlers
  const handleResizeStart = (columnName: string, e: React.MouseEvent) => {
    e.preventDefault();
    setResizingColumn(columnName);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = columnWidths[columnName] || 150;
  };

  useEffect(() => {
    const handleResizeMove = (e: MouseEvent) => {
      if (!resizingColumn) return;
      const diff = e.clientX - resizeStartX.current;
      const newWidth = Math.max(80, resizeStartWidth.current + diff);
      setColumnWidths((prev) => ({
        ...prev,
        [resizingColumn]: newWidth,
      }));
    };

    const handleResizeEnd = () => {
      setResizingColumn(null);
    };

    if (resizingColumn) {
      document.addEventListener("mousemove", handleResizeMove);
      document.addEventListener("mouseup", handleResizeEnd);
      return () => {
        document.removeEventListener("mousemove", handleResizeMove);
        document.removeEventListener("mouseup", handleResizeEnd);
      };
    }
  }, [resizingColumn]);

  // Sorting handler
  const handleSort = (columnName: string) => {
    if (sortColumn === columnName) {
      if (sortDirection === null) setSortDirection("asc");
      else if (sortDirection === "asc") setSortDirection("desc");
      else {
        setSortDirection(null);
        setSortColumn(null);
      }
    } else {
      setSortColumn(columnName);
      setSortDirection("asc");
    }
  };

  // Filter handler
  const handleFilterChange = (columnName: string, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [columnName]: value,
    }));
  };

  // Edit mode handlers
  const handleEditClick = () => {
    setIsEditMode(true);
    const dataCopy = JSON.parse(JSON.stringify(data.data));
    setEditableData(dataCopy);
    setOriginalData(JSON.parse(JSON.stringify(data.data)));
  };

  const handleCancelEdit = () => {
    setIsEditMode(false);
    setEditableData([]);
    setOriginalData([]);
  };

  const handleAddRow = () => {
    const newRow: EditableRow = { _isNew: true };
    schema.columns.forEach(col => {
      if (col.primary_key) {
        // Primary key will be auto-generated
        newRow[col.name] = "(auto)";
      } else {
        newRow[col.name] = "";
      }
    });
    // Add new row at the BOTTOM of the table
    setEditableData([...editableData, newRow]);
  };

  const handleAddNewRow = () => {
    // Enter edit mode and add a new row at the bottom
    const newRow: EditableRow = { _isNew: true };
    schema.columns.forEach(col => {
      if (col.primary_key) {
        newRow[col.name] = "(auto)";
      } else {
        newRow[col.name] = "";
      }
    });
    const dataCopy = JSON.parse(JSON.stringify(data.data));
    setEditableData([...dataCopy, newRow]);
    setOriginalData(JSON.parse(JSON.stringify(data.data)));
    setIsEditMode(true);
  };

  const handleCellChange = (rowIndex: number, columnName: string, value: any) => {
    const newData = [...editableData];
    newData[rowIndex][columnName] = value;

    // Mark as modified if not new
    if (!newData[rowIndex]._isNew) {
      newData[rowIndex]._isModified = true;
    }

    // Auto-populate provider_id for llm_models when provider_name changes
    if (tableName === "llm_models" && columnName === "llm_provider_name") {
      const provider = providers.find(p => p.llm_provider_name === value);
      if (provider) {
        newData[rowIndex]["llm_provider_id"] = provider.llm_provider_id;
      }
    }

    setEditableData(newData);
  };

  const hasChanges = () => {
    // Check if there are any new rows or modified rows
    return editableData.some(row => row._isNew || row._isModified);
  };

  const validate = (): string | null => {
    // Check required fields
    for (let i = 0; i < editableData.length; i++) {
      const row = editableData[i];
      for (const col of schema.columns) {
        if (!col.nullable && !col.primary_key) {
          const value = row[col.name];
          if (value === null || value === undefined || value === "") {
            return `Row ${i + 1}: ${col.name} is required`;
          }
        }
      }

      // Table-specific validation
      if (tableName === "llm_models") {
        // Check provider_name was selected (which auto-populates provider_id)
        if (!row.llm_provider_name || row.llm_provider_name === "") {
          return `Row ${i + 1}: Please select a provider`;
        }
        // Verify provider_id was auto-populated
        if (!row.llm_provider_id || row.llm_provider_id === "") {
          return `Row ${i + 1}: Provider ID not populated (internal error)`;
        }
        // Check if provider exists
        const providerExists = providers.some(p => p.llm_provider_name === row.llm_provider_name);
        if (!providerExists) {
          return `Row ${i + 1}: Selected provider does not exist in database`;
        }
      }
    }

    // Check for duplicates (model names, provider names)
    const nameColumn = tableName === "llm_providers" ? "llm_provider_name" :
                      tableName === "llm_models" ? "llm_model_name" : null;

    if (nameColumn) {
      const names = editableData.map(row => row[nameColumn]).filter(n => n);
      const duplicates = names.filter((name, index) => names.indexOf(name) !== index);
      if (duplicates.length > 0) {
        return `Duplicate names found: ${duplicates.join(", ")}`;
      }
    }

    return null;
  };

  const handleSave = async () => {
    // Validate
    const validationError = validate();
    if (validationError) {
      alert(validationError);
      return;
    }

    if (!onSave) return;

    setIsSaving(true);
    try {
      // Filter only new or modified rows
      const rowsToSave = editableData.filter(row => row._isNew || row._isModified);
      await onSave(rowsToSave);
      setIsEditMode(false);
      setEditableData([]);
      setOriginalData([]);
      if (onRefresh) onRefresh();
    } catch (error) {
      alert(`Save failed: ${error instanceof Error ? error.message : "Unknown error"}`);
    } finally {
      setIsSaving(false);
    }
  };

  // Apply client-side sorting and filtering
  const getProcessedData = () => {
    const dataToProcess = isEditMode ? editableData : data.data;
    let processedData = [...dataToProcess];

    // Apply filters
    Object.entries(filters).forEach(([column, filterValue]) => {
      if (filterValue) {
        processedData = processedData.filter((row) => {
          const cellValue = String(row[column] || "").toLowerCase();
          return cellValue.includes(filterValue.toLowerCase());
        });
      }
    });

    // Apply sorting
    if (sortColumn && sortDirection) {
      processedData.sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];

        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        const aStr = String(aVal);
        const bStr = String(bVal);

        const comparison = aStr.localeCompare(bStr, undefined, { numeric: true });
        return sortDirection === "asc" ? comparison : -comparison;
      });
    }

    return processedData;
  };

  const processedData = getProcessedData();

  // Format cell value for display
  const formatCellValue = (value: any): string => {
    if (value === null || value === undefined) {
      return "";
    }
    if (typeof value === "object") {
      return JSON.stringify(value);
    }
    if (typeof value === "boolean") {
      return value ? "✓" : "✗";
    }
    const str = String(value);
    if (str.length > 100) {
      return str.substring(0, 100) + "...";
    }
    return str;
  };

  // Get sort icon for column
  const getSortIcon = (columnName: string) => {
    if (sortColumn !== columnName) {
      return <ArrowUpDown className="h-3 w-3 text-gray-400" />;
    }
    if (sortDirection === "asc") {
      return <ArrowUp className="h-3 w-3 text-blue-600" />;
    }
    if (sortDirection === "desc") {
      return <ArrowDown className="h-3 w-3 text-blue-600" />;
    }
    return <ArrowUpDown className="h-3 w-3 text-gray-400" />;
  };

  // Render cell - editable or readonly
  const renderCell = (row: EditableRow, rowIndex: number, column: any) => {
    const value = row[column.name];
    const isPrimaryKey = column.primary_key;

    // Determine if field is non-editable
    // Primary keys are always non-editable
    // llm_provider_id in llm_models is non-editable (auto-populated from provider name)
    const isNonEditable = isPrimaryKey ||
                          (tableName === "llm_models" && column.name === "llm_provider_id");

    // Not in edit mode - show readonly
    if (!isEditMode) {
      return (
        <div
          className="overflow-hidden text-ellipsis whitespace-nowrap"
          title={formatCellValue(value)}
        >
          {formatCellValue(value)}
        </div>
      );
    }

    // In edit mode - non-editable fields show with grey background
    if (isNonEditable) {
      return (
        <div
          className="overflow-hidden text-ellipsis whitespace-nowrap px-2 py-1 bg-gray-100 rounded text-gray-600"
          title={formatCellValue(value)}
        >
          {isPrimaryKey && row._isNew ? "(auto)" : formatCellValue(value)}
        </div>
      );
    }

    // Special handling for llm_provider_name in llm_models (DROPDOWN)
    if (tableName === "llm_models" && column.name === "llm_provider_name") {
      return (
        <select
          value={value || ""}
          onChange={(e) => handleCellChange(rowIndex, column.name, e.target.value)}
          className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">Select provider...</option>
          {providers.map(provider => (
            <option key={provider.llm_provider_id} value={provider.llm_provider_name}>
              {provider.llm_provider_name}
            </option>
          ))}
        </select>
      );
    }

    // Regular text input for all other editable fields
    return (
      <input
        type="text"
        value={value || ""}
        onChange={(e) => handleCellChange(rowIndex, column.name, e.target.value)}
        className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        placeholder={column.nullable ? "Optional" : "Required"}
      />
    );
  };

  return (
    <div className="space-y-3">
      {/* Table Info & Controls - Compact header */}
      <div className="flex items-center justify-between text-xs text-gray-600 px-1">
        <div className="flex items-center gap-4">
          {/* Edit and Add buttons (only for editable tables) */}
          {editable && !isEditMode && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleEditClick}
                className="inline-flex items-center gap-1 px-2 py-1 bg-blue-600 text-white rounded text-xs font-medium hover:bg-blue-700 transition-colors"
              >
                <Edit className="h-3 w-3" />
                Edit
              </button>
              <button
                onClick={handleAddNewRow}
                className="inline-flex items-center gap-1 px-2 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 transition-colors"
              >
                <Plus className="h-3 w-3" />
                Add
              </button>
            </div>
          )}

          {/* Save, Cancel, and Add Row buttons (when in edit mode) */}
          {isEditMode && (
            <div className="flex items-center gap-2">
              <button
                onClick={handleAddRow}
                className="inline-flex items-center gap-1 px-2 py-1 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 transition-colors"
              >
                <Plus className="h-3 w-3" />
                Add Row
              </button>
              <button
                onClick={handleSave}
                disabled={!hasChanges() || isSaving}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
                  !hasChanges() || isSaving
                    ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                    : "bg-blue-600 text-white hover:bg-blue-700"
                }`}
              >
                <Save className="h-3 w-3" />
                {isSaving ? "Saving..." : "Save"}
              </button>
              <button
                onClick={handleCancelEdit}
                disabled={isSaving}
                className="inline-flex items-center gap-1 px-2 py-1 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
              >
                <X className="h-3 w-3" />
                Cancel
              </button>
            </div>
          )}

          <span className="text-sm font-medium text-gray-700">Table:</span>

          <span>
            <span className="font-semibold text-gray-900">
              {data.total_count.toLocaleString()}
            </span>{" "}
            rows {processedData.length !== (isEditMode ? editableData : data.data).length && (
              <span className="text-blue-600">({processedData.length} filtered)</span>
            )}
          </span>
          <span className="text-gray-400">
            Page {currentPage} of {totalPages || 1}
          </span>
          <button
            onClick={() => setShowFilterRow(!showFilterRow)}
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium transition-colors ${
              showFilterRow ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            <Filter className="h-3 w-3" />
            {showFilterRow ? "Hide Filters" : "Show Filters"}
          </button>
        </div>

        {/* Pagination Controls - Compact */}
        <div className="flex items-center gap-2">
          <button
            onClick={handlePrevious}
            disabled={data.offset === 0 || isEditMode}
            className="inline-flex items-center gap-1 px-2 py-1 border border-gray-300 rounded text-xs font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="h-3 w-3" />
            Prev
          </button>

          <span className="text-xs text-gray-600">
            {data.offset + 1}-{Math.min(data.offset + data.limit, data.total_count)}
          </span>

          <button
            onClick={handleNext}
            disabled={!data.has_more || isEditMode}
            className="inline-flex items-center gap-1 px-2 py-1 border border-gray-300 rounded text-xs font-medium text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
            <ChevronRight className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Table Container - Fixed height with vertical scroll */}
      <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
        <div className="overflow-auto max-h-[calc(100vh-280px)]">
          <table className="min-w-full divide-y divide-gray-200">
            {/* Sticky Header */}
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                {schema.columns.map((column) => (
                  <th
                    key={column.name}
                    className="px-3 py-1.5 text-left text-xs font-semibold text-gray-700 border-b border-gray-200 relative group"
                    style={{
                      position: "sticky",
                      top: 0,
                      width: columnWidths[column.name] || 150,
                      minWidth: columnWidths[column.name] || 150,
                      maxWidth: columnWidths[column.name] || 150,
                    }}
                  >
                    <div className="flex items-center gap-1.5 justify-between">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <span className={`truncate ${!column.nullable ? 'text-blue-600 font-semibold' : ''}`}>
                          {column.name}
                        </span>
                        {column.primary_key && (
                          <span className="inline-flex items-center px-1 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700 flex-shrink-0">
                            PK
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleSort(column.name)}
                        className="hover:bg-gray-200 rounded p-0.5 transition-colors flex-shrink-0"
                        title="Click to sort"
                      >
                        {getSortIcon(column.name)}
                      </button>
                    </div>
                    <div className="text-[10px] text-gray-400 font-normal mt-0.5 truncate">
                      {column.type}
                    </div>

                    {/* Resize handle */}
                    <div
                      className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-500 group-hover:bg-gray-300 transition-colors"
                      onMouseDown={(e) => handleResizeStart(column.name, e)}
                      style={{ userSelect: "none" }}
                    />
                  </th>
                ))}
              </tr>

              {/* Filter Row */}
              {showFilterRow && (
                <tr className="bg-white sticky top-[52px] z-10 border-b border-gray-200">
                  {schema.columns.map((column) => (
                    <th
                      key={`filter-${column.name}`}
                      className="px-2 py-1"
                      style={{
                        width: columnWidths[column.name] || 150,
                        minWidth: columnWidths[column.name] || 150,
                        maxWidth: columnWidths[column.name] || 150,
                      }}
                    >
                      <input
                        type="text"
                        placeholder={`Filter ${column.name}...`}
                        value={filters[column.name] || ""}
                        onChange={(e) => handleFilterChange(column.name, e.target.value)}
                        className="w-full px-2 py-0.5 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </th>
                  ))}
                </tr>
              )}
            </thead>

            {/* Table Body - Compact rows */}
            <tbody className="bg-white divide-y divide-gray-100">
              {processedData.length === 0 ? (
                <tr>
                  <td
                    colSpan={schema.columns.length}
                    className="px-3 py-8 text-center text-sm text-gray-500"
                  >
                    {tableName === "llm_models" && isEditMode && processedData.length === 0 && providers.length === 0
                      ? "No providers registered yet. Please add providers first."
                      : Object.keys(filters).some(k => filters[k])
                      ? "No matching rows found"
                      : "No data available"}
                  </td>
                </tr>
              ) : (
                processedData.map((row, rowIndex) => (
                  <tr
                    key={rowIndex}
                    className={`transition-colors ${
                      row._isNew
                        ? "bg-green-50 hover:bg-green-100"
                        : row._isModified
                        ? "bg-yellow-50 hover:bg-yellow-100"
                        : "hover:bg-blue-50/50"
                    }`}
                  >
                    {schema.columns.map((column) => (
                      <td
                        key={column.name}
                        className="px-3 py-1.5 text-xs text-gray-900 border-r border-gray-100 last:border-r-0"
                        style={{
                          width: columnWidths[column.name] || 150,
                          minWidth: columnWidths[column.name] || 150,
                          maxWidth: columnWidths[column.name] || 150,
                        }}
                      >
                        {renderCell(row, rowIndex, column)}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer info */}
      <div className="text-[11px] text-gray-500 px-1">
        Showing {data.offset + 1} to{" "}
        {Math.min(data.offset + data.limit, data.total_count)} of{" "}
        {data.total_count} rows
        {processedData.length !== (isEditMode ? editableData : data.data).length && (
          <span className="text-blue-600 ml-2">
            ({processedData.length} visible after filtering)
          </span>
        )}
        {isEditMode && (
          <span className="text-orange-600 ml-2 font-medium">
            • EDIT MODE ACTIVE
          </span>
        )}
      </div>
    </div>
  );
}
