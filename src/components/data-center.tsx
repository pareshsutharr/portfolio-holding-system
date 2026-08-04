"use client";

import {
  AlertTriangle,
  Check,
  ChevronDown,
  Clock,
  FileSpreadsheet,
  Folder,
  LoaderCircle,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { authFetch } from "@/lib/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL
  ?? (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");

type FileInfo = { name: string; size_bytes: number; modified_at: string };

type Frequency = "fixed" | "daily" | "quarterly" | "yearly" | "monthly" | "undecided";

type Category = {
  key: string;
  label: string;
  description: string;
  frequency: Frequency;
  kind: "single_file" | "file_folder";
  extensions: string[];
  consumers: string;
  file?: FileInfo | null;
  synced_paths?: string[];
  files?: FileInfo[];
  file_count?: number;
  total_size_bytes?: number;
};

const FREQUENCY_GROUPS: { key: Frequency; title: string; blurb: string }[] = [
  { key: "fixed", title: "Fixed reference data", blurb: "Rarely changes — update only when the underlying master list changes." },
  { key: "daily", title: "Daily", blurb: "Must be refreshed every trading day." },
  { key: "quarterly", title: "Quarterly", blurb: "Refresh once a quarter." },
  { key: "yearly", title: "Yearly", blurb: "Refresh once a year, typically from factsheets." },
  { key: "monthly", title: "Monthly / ad-hoc", blurb: "Historical imports, refreshed as new months land." },
  { key: "undecided", title: "Not yet scheduled", blurb: "Cadence hasn't been decided yet." },
];

const FREQUENCY_BADGE: Record<Frequency, string> = {
  fixed: "bg-[#f2f5f2] text-[#65736f]",
  daily: "bg-[#ecf4f3] text-[#2a655e]",
  quarterly: "bg-[#fbefdf] text-[#b5752d]",
  yearly: "bg-[#e8f0ef] text-[#173337]",
  monthly: "bg-[#f9e7e5] text-[#a34f4a]",
  undecided: "border-dashed border-[#cfd8d5] text-muted-text",
};

const formatBytes = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const formatDate = (iso: string) =>
  new Date(iso).toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

export function DataCenter() {
  const [categories, setCategories] = useState<Category[] | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [pendingKey, setPendingKey] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ category: Category; filename?: string } | null>(null);
  const [toast, setToast] = useState("");

  const fetchCategories = useCallback(() => {
    authFetch(`${API_URL}/api/data-center`)
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail ?? "Could not load data center");
        return payload as { categories: Category[] };
      })
      .then((payload) => setCategories(payload.categories))
      .catch((caught) => setError(caught instanceof Error ? caught.message : "Could not load data center"))
      .finally(() => setLoading(false));
  }, []);

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    fetchCategories();
  }, [fetchCategories]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  function patchCategory(updated: Category) {
    setCategories((prev) => (prev ? prev.map((item) => (item.key === updated.key ? updated : item)) : prev));
  }

  async function uploadSingle(category: Category, file: File) {
    setPendingKey(category.key);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await authFetch(`${API_URL}/api/data-center/${category.key}/file`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed");
      patchCategory(payload as Category);
      setToast(`${category.label} updated`);
    } catch (caught) {
      setToast(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setPendingKey(null);
    }
  }

  async function addFolderFile(category: Category, file: File) {
    setPendingKey(category.key);
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await authFetch(`${API_URL}/api/data-center/${category.key}/files`, { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Upload failed");
      patchCategory(payload as Category);
      setToast(`${file.name} added to ${category.label}`);
    } catch (caught) {
      setToast(caught instanceof Error ? caught.message : "Upload failed");
    } finally {
      setPendingKey(null);
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    const { category, filename } = deleteTarget;
    setPendingKey(category.key);
    setDeleteTarget(null);
    try {
      const url = filename
        ? `${API_URL}/api/data-center/${category.key}/files/${encodeURIComponent(filename)}`
        : `${API_URL}/api/data-center/${category.key}/file`;
      const response = await authFetch(url, { method: "DELETE" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Delete failed");
      patchCategory(payload as Category);
      setToast(filename ? `${filename} deleted` : `${category.label} deleted`);
    } catch (caught) {
      setToast(caught instanceof Error ? caught.message : "Delete failed");
    } finally {
      setPendingKey(null);
    }
  }

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3200);
    return () => clearTimeout(timer);
  }, [toast]);

  return (
    <div className="mx-auto max-w-[1100px] px-4 py-8 md:px-8 md:py-9">
      <section className="mb-7 flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="mb-1.5 text-[9px] font-extrabold tracking-[1.5px] text-[#89938f] uppercase">Workspace</p>
          <h1 className="text-[28px] font-bold leading-tight text-[#173337] md:text-[30px]">Data center</h1>
          <p className="mt-1.5 max-w-xl text-[13px] text-muted-text">
            Every source file the analysis engine reads from disk, grouped by how often it needs refreshing. Uploads
            replace the live file the pipeline uses; deletes are backed up first.
          </p>
        </div>
        <Button variant="outline" className="h-10 gap-2 rounded-lg px-4 text-[12px] font-bold" onClick={load}>
          <RefreshCw size={15} className={loading ? "animate-spin" : ""} /> Refresh
        </Button>
      </section>

      {loading && !categories && (
        <Card className="flex items-center justify-center gap-2 rounded-[13px] p-12 text-sm text-muted-text">
          <LoaderCircle size={16} className="animate-spin" /> Loading data center…
        </Card>
      )}

      {!loading && error && (
        <Card className="flex flex-col items-center gap-2 rounded-[13px] p-12 text-center">
          <AlertTriangle size={22} className="text-rose" />
          <p className="text-sm font-semibold text-[#173337]">Couldn&apos;t reach the analysis service</p>
          <p className="max-w-sm text-xs text-muted-text">{error}</p>
        </Card>
      )}

      {categories && (
        <div className="flex flex-col gap-8">
          {FREQUENCY_GROUPS.map((group) => {
            const items = categories.filter((category) => category.frequency === group.key);
            if (items.length === 0) return null;
            return (
              <section key={group.key}>
                <div className="mb-3 flex items-baseline gap-2.5">
                  <h2 className="text-[15px] font-bold text-[#173337]">{group.title}</h2>
                  <Badge variant="outline" className={cn("rounded-full border-transparent px-2 py-0.5 text-[9px]", FREQUENCY_BADGE[group.key])}>
                    {items.length}
                  </Badge>
                  <span className="text-[11px] text-muted-text">{group.blurb}</span>
                </div>
                <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
                  {items.map((category) => (
                    <CategoryCard
                      key={category.key}
                      category={category}
                      busy={pendingKey === category.key}
                      onUploadSingle={(file) => uploadSingle(category, file)}
                      onAddFolderFile={(file) => addFolderFile(category, file)}
                      onDeleteSingle={() => setDeleteTarget({ category })}
                      onDeleteFolderFile={(filename) => setDeleteTarget({ category, filename })}
                    />
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      )}

      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete {deleteTarget?.filename ?? deleteTarget?.category.label}?</DialogTitle>
            <DialogDescription>
              {deleteTarget?.category.consumers && (
                <>
                  Used by <strong>{deleteTarget.category.consumers}</strong>.{" "}
                </>
              )}
              A backup is kept under <code>runtime/data-center-backups</code>, but the pipeline won&apos;t be able to
              read this data until it&apos;s replaced.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              <Trash2 size={15} /> Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {toast && (
        <div className="fixed bottom-6 right-6 z-[60] rounded-lg bg-[#173c3e] px-4 py-3 text-[12px] font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

function CategoryCard({
  category,
  busy,
  onUploadSingle,
  onAddFolderFile,
  onDeleteSingle,
  onDeleteFolderFile,
}: {
  category: Category;
  busy: boolean;
  onUploadSingle: (file: File) => void;
  onAddFolderFile: (file: File) => void;
  onDeleteSingle: () => void;
  onDeleteFolderFile: (filename: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className="rounded-[13px] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-[13px] font-bold text-[#173337]">{category.label}</p>
          <p className="mt-0.5 text-[11px] text-muted-text">{category.description}</p>
          {category.consumers && (
            <p className="mt-1 truncate text-[9px] text-[#9aa5a2]">Used by {category.consumers}</p>
          )}
        </div>
        {busy && <LoaderCircle size={15} className="mt-1 shrink-0 animate-spin text-muted-text" />}
      </div>

      {category.kind === "single_file" ? (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-lg border border-[#edf0ed] bg-[#f9fbf8] px-3 py-2.5">
          {category.file ? (
            <div className="flex min-w-0 items-center gap-2">
              <FileSpreadsheet size={16} className="shrink-0 text-teal" />
              <div className="min-w-0">
                <p className="truncate text-[11px] font-semibold text-[#173337]">{category.file.name}</p>
                <p className="flex items-center gap-1 text-[9px] text-muted-text">
                  {formatBytes(category.file.size_bytes)} · <Clock size={10} /> {formatDate(category.file.modified_at)}
                </p>
              </div>
            </div>
          ) : (
            <p className="flex items-center gap-1.5 text-[11px] text-[#a34f4a]">
              <AlertTriangle size={13} /> No file uploaded
            </p>
          )}
          <div className="flex shrink-0 items-center gap-1.5">
            <input
              ref={inputRef}
              type="file"
              hidden
              accept={category.extensions.join(",")}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onUploadSingle(file);
                event.target.value = "";
              }}
            />
            <Button size="sm" variant="outline" className="gap-1.5" disabled={busy} onClick={() => inputRef.current?.click()}>
              <UploadCloud size={13} /> {category.file ? "Replace" : "Upload"}
            </Button>
            {category.file && (
              <Button size="icon-sm" variant="outline" disabled={busy} onClick={onDeleteSingle} aria-label={`Delete ${category.label}`}>
                <Trash2 size={13} />
              </Button>
            )}
          </div>
          {category.synced_paths && category.synced_paths.length > 1 && (
            <span className="sr-only">Kept in sync across {category.synced_paths.length} locations</span>
          )}
        </div>
      ) : (
        <FolderContents
          category={category}
          expanded={expanded}
          setExpanded={setExpanded}
          busy={busy}
          onAddFile={onAddFolderFile}
          onDeleteFile={onDeleteFolderFile}
        />
      )}

      {category.synced_paths && category.synced_paths.length > 1 && (
        <p className="mt-2 flex items-center gap-1 text-[9px] text-[#89938f]">
          <Check size={10} className="text-green" /> Kept in sync across {category.synced_paths.length} locations
        </p>
      )}
    </Card>
  );
}

function FolderContents({
  category,
  expanded,
  setExpanded,
  busy,
  onAddFile,
  onDeleteFile,
}: {
  category: Category;
  expanded: boolean;
  setExpanded: (value: boolean) => void;
  busy: boolean;
  onAddFile: (file: File) => void;
  onDeleteFile: (filename: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const files = category.files ?? [];

  return (
    <div className="mt-3 rounded-lg border border-[#edf0ed] bg-[#f9fbf8]">
      <Collapsible open={expanded} onOpenChange={setExpanded}>
        <div className="flex items-center justify-between gap-3 px-3 py-2.5">
          <CollapsibleTrigger className="flex min-w-0 items-center gap-2 text-left">
            <Folder size={16} className="shrink-0 text-teal" />
            <div className="min-w-0">
              <p className="truncate text-[11px] font-semibold text-[#173337]">
                {category.file_count} file{category.file_count === 1 ? "" : "s"}
              </p>
              <p className="text-[9px] text-muted-text">{formatBytes(category.total_size_bytes ?? 0)} total</p>
            </div>
            <ChevronDown size={14} className={cn("ml-1 shrink-0 text-muted-text transition-transform", expanded && "rotate-180")} />
          </CollapsibleTrigger>
          <div className="flex shrink-0 items-center gap-1.5">
            <input
              ref={inputRef}
              type="file"
              hidden
              accept={category.extensions.join(",")}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onAddFile(file);
                event.target.value = "";
              }}
            />
            <Button size="sm" variant="outline" className="gap-1.5" disabled={busy} onClick={() => inputRef.current?.click()}>
              <Plus size={13} /> Add file
            </Button>
          </div>
        </div>
        <CollapsibleContent>
          <div className="max-h-64 overflow-y-auto border-t border-[#edf0ed]">
            {files.length === 0 ? (
              <p className="px-3 py-4 text-center text-[11px] text-muted-text">No files yet.</p>
            ) : (
              files.map((file) => (
                <div key={file.name} className="flex items-center justify-between gap-2 border-b border-[#edf0ed] px-3 py-2 last:border-b-0">
                  <div className="flex min-w-0 items-center gap-2">
                    <FileSpreadsheet size={13} className="shrink-0 text-[#84908c]" />
                    <div className="min-w-0">
                      <p className="truncate text-[10px] font-medium text-[#173337]">{file.name}</p>
                      <p className="text-[9px] text-muted-text">
                        {formatBytes(file.size_bytes)} · {formatDate(file.modified_at)}
                      </p>
                    </div>
                  </div>
                  <Button
                    size="icon-sm"
                    variant="ghost"
                    disabled={busy}
                    onClick={() => onDeleteFile(file.name)}
                    aria-label={`Delete ${file.name}`}
                  >
                    <Trash2 size={12} />
                  </Button>
                </div>
              ))
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
