import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../../api/apiClient";
import InfoIcon from '@mui/icons-material/Info';


type UploadProjectModalProps = {
  open: boolean;
  onClose: () => void;
  onUploadSuccess?: () => void;
};

const ALLOWED_EXTENSIONS = [".zip", ".gz", ".7z", ".tar.gz"];

function hasAllowedExtension(fileName: string): boolean {
  const lower = fileName.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function UploadProjectModal({
  open,
  onClose,
  onUploadSuccess,
}: UploadProjectModalProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [configuredGithub, setConfiguredGithub] = useState<string>("");
  const [hasConsent, setHasConsent] = useState<boolean | null>(null);

  const fileValidationError = useMemo(() => {
    if (!selectedFile) return null;
    if (!hasAllowedExtension(selectedFile.name)) {
      return `Unsupported file type. Allowed formats: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }
    return null;
  }, [selectedFile]);

  useEffect(() => {
    if (!open) return;

    let alive = true;

    async function loadUserConfig() {
      try {
        setIsLoadingConfig(true);

        const res = await api.getUserConfig();

        if (!alive) return;

        setConfiguredGithub(res?.github?.trim?.() ?? "");
        setHasConsent(res?.consent ?? false);
      } catch {
        if (!alive) return;

        setConfiguredGithub("");
        setHasConsent(false);
      } finally {
        if (alive) setIsLoadingConfig(false);
      }
    }

    loadUserConfig();

    return () => {
      alive = false;
    };
  }, [open]);

  if (!open) return null;

  function resetState() {
    setSelectedFile(null);
    setIsDragging(false);
    setIsLoadingConfig(false);
    setIsUploading(false);
    setUploadError(null);
    setUploadSuccess(null);
    setConfiguredGithub("");
    setHasConsent(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleClose() {
    if (isUploading || isLoadingConfig) return;
    resetState();
    onClose();
  }

  function handleChooseFile() {
    if (isUploading || isLoadingConfig) return;
    inputRef.current?.click();
  }

  function handleSelectedFile(file: File | null) {
    setUploadError(null);
    setUploadSuccess(null);
    setSelectedFile(file);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    handleSelectedFile(file);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (isUploading) return;
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    if (isUploading) return;

    setIsDragging(false);
    const file = e.dataTransfer.files?.[0] ?? null;
    handleSelectedFile(file);
  }

  function handleRemoveFile() {
    if (isUploading) return;
    setSelectedFile(null);
    setUploadError(null);
    setUploadSuccess(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  async function handleUpload() {
  setUploadError(null);
  setUploadSuccess(null);

  if (!selectedFile) {
    setUploadError("Please select a project archive before uploading.");
    return;
  }

  if (fileValidationError) {
    setUploadError(fileValidationError);
    return;
  }

  const fileToUpload = selectedFile;

  setIsUploading(true);
  resetState();
  onClose();
  onUploadSuccess?.();

  try {
    await api.uploadProject({
      file: fileToUpload,
    });
  } catch (error: any) {
    console.error(error);
  } finally {
    setIsUploading(false);
  }
}

  return (
    <div
      onClick={handleClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0, 0, 0, 0.68)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 760,
          background: "var(--bg-surface)",
          border: "1px solid var(--border)",
          borderRadius: 18,
          padding: 24,
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h2 style={{ margin: 0 }}>Upload Project</h2>

          <button
            onClick={handleClose}
            disabled={isUploading || isLoadingConfig}
            style={{
              border: "none",
              background: "transparent",
              color: isUploading || isLoadingConfig ? "#777" : "#444",
              fontSize: 20,
              cursor:
                isUploading || isLoadingConfig ? "not-allowed" : "pointer",
            }}
            aria-label="Close upload modal"
          >
            ×
          </button>
        </div>

        <input
          data-testid="upload-input"
          ref={inputRef}
          type="file"
          accept=".zip,.gz,.7z,.tar.gz"
          onChange={handleFileChange}
          disabled={isUploading || isLoadingConfig}
          style={{ display: "none" }}
        />

        <div
          onClick={handleChooseFile}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            border: `2px dashed ${isDragging ? "#6b7280" : "var(--border-strong)"}`,
            borderRadius: 16,
            padding: "48px 24px",
            textAlign: "center",
            background: isDragging ? "#f0f4ff" : "var(--bg-surface)",
            marginBottom: 16,
            cursor: isUploading || isLoadingConfig ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
            opacity: isUploading || isLoadingConfig ? 0.7 : 1,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 12 }}>📁</div>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>
            Upload or Drag and Drop
          </div>
          <div style={{ color: "var(--text-muted)", fontSize: 14 }}>
            Supported formats: .zip, .gz, .7z, .tar.gz
          </div>
        </div>

        {selectedFile && (
          <div
            style={{
              border: "1px solid var(--border)",
              borderRadius: 12,
              padding: 14,
              background: "var(--bg-surface)",
              marginBottom: 16,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{selectedFile.name}</div>
              <div style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>
                {formatFileSize(selectedFile.size)}
              </div>
            </div>

            <button
              onClick={handleRemoveFile}
              disabled={isUploading || isLoadingConfig}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "transparent",
                color: isUploading || isLoadingConfig ? "#777" : "#444",
                cursor:
                  isUploading || isLoadingConfig ? "not-allowed" : "pointer",
              }}
            >
              Remove
            </button>
          </div>
        )}

        {!isLoadingConfig && hasConsent === false && (
          <div
            style={{
              display: "flex",
              gap: 10,
              alignItems: "flex-start",
              background: "var(--danger-bg)",
              border: "1px solid #7a3a1a",
              borderRadius: 12,
              padding: 14,
              marginBottom: 16,
              color: "#ffb07a",
            }}
          >
            <span style={{ fontSize: 18, flexShrink: 0 }}>⚠️</span>
            <div style={{ fontSize: 14, lineHeight: 1.5 }}>
              You must complete your profile before uploading a project. Open{" "}
              <strong>Profile</strong> (top-right of the app) and save your
              preferences, including accepting the data consent, then try again.
            </div>
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            padding: "12px 14px",
            marginBottom: 16,
            color: "#bdbdbd", />
          <div style={{ fontSize: 14, lineHeight: 1.5 }}>
            {isLoadingConfig
              ? "Loading saved settings..."
              : configuredGithub
              ? `Analyzing with configured GitHub user "${configuredGithub}".`
              : "You do not have a GitHub profile configured yet. Some project mining features may be limited until user settings are completed."}
          </div>
        </div>

        {fileValidationError && (
          <div
            style={{
              marginBottom: 12,
              color: "var(--danger-text)",
              fontSize: 14,
            }}
          >
            {fileValidationError}
          </div>
        )}

        {uploadError && (
          <div
            style={{
              marginBottom: 12,
              color: "var(--danger-text)",
              fontSize: 14,
            }}
          >
            {uploadError}
          </div>
        )}

        {uploadSuccess && (
          <div
            style={{
              marginBottom: 12,
              color: "#16a34a",
              fontSize: 14,
            }}
          >
            {uploadSuccess}
          </div>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            marginTop: 8,
          }}
        >
          <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
            {isLoadingConfig
              ? "Loading saved settings..."
              : isUploading
              ? "Analyzing Project..."
              : selectedFile
              ? "Ready to Analyze."
              : "No file selected."}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "flex-end",
              gap: 12,
            }}
          >
            <button
              onClick={handleClose}
              disabled={isUploading || isLoadingConfig}
              style={{
                padding: "10px 14px",
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 10,
                color: isUploading || isLoadingConfig ? "#777" : "#444",
                cursor:
                  isUploading || isLoadingConfig ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>

            <button
              onClick={handleUpload}
              disabled={
                !selectedFile ||
                !!fileValidationError ||
                isUploading ||
                isLoadingConfig ||
                hasConsent === false
              }
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                border: "none",
                background:
                  !selectedFile ||
                  fileValidationError ||
                  isUploading ||
                  isLoadingConfig ||
                  hasConsent === false
                    ? "#202020"
                    : "#2b2b2b",
                color: "#fff",
                opacity:
                  !selectedFile ||
                  fileValidationError ||
                  isUploading ||
                  isLoadingConfig ||
                  hasConsent === false
                    ? 0.6
                    : 1,
                cursor:
                  !selectedFile ||
                  fileValidationError ||
                  isUploading ||
                  isLoadingConfig ||
                  hasConsent === false
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              {isUploading ? "Analyzing..." : "Start Mining"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}