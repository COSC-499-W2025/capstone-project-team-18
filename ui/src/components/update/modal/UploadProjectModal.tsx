import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../../api/apiClient";

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
  const [configuredEmail, setConfiguredEmail] = useState<string>("");
  const [configuredGithub, setConfiguredGithub] = useState<string>("");

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

        setConfiguredEmail(res?.user_email?.trim?.() ?? "");
        setConfiguredGithub(res?.github?.trim?.() ?? "");
      } catch {
        if (!alive) return;

        setConfiguredEmail("");
        setConfiguredGithub("");
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
    setConfiguredEmail("");
    setConfiguredGithub("");
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

    try {
      setIsUploading(true);

      const response = await api.uploadProject({
        file: selectedFile,
        email: configuredEmail || undefined,
      });

      setUploadSuccess(
        response?.message
          ? `${response.message}${response.portfolio_name ? `: ${response.portfolio_name}` : ""}`
          : `Project Analyzed successfully: ${selectedFile.name}`
      );

      onUploadSuccess?.();
    } catch (error: any) {
      setUploadError(error?.message ?? "Upload failed.");
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
          background: "#1b1b1b",
          border: "1px solid #2a2a2a",
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
              color: isUploading || isLoadingConfig ? "#666" : "#ccc",
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
            border: `2px dashed ${isDragging ? "#6b7280" : "#3a3a3a"}`,
            borderRadius: 16,
            padding: "48px 24px",
            textAlign: "center",
            background: isDragging ? "#1d1d1d" : "#151515",
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
          <div style={{ color: "#999", fontSize: 14 }}>
            Supported formats: .zip, .gz, .7z, .tar.gz
          </div>
        </div>

        {selectedFile && (
          <div
            style={{
              border: "1px solid #2a2a2a",
              borderRadius: 12,
              padding: 14,
              background: "#151515",
              marginBottom: 16,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{selectedFile.name}</div>
              <div style={{ color: "#999", fontSize: 13, marginTop: 4 }}>
                {formatFileSize(selectedFile.size)}
              </div>
            </div>

            <button
              onClick={handleRemoveFile}
              disabled={isUploading || isLoadingConfig}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #2a2a2a",
                background: "transparent",
                color: isUploading || isLoadingConfig ? "#666" : "#ddd",
                cursor:
                  isUploading || isLoadingConfig ? "not-allowed" : "pointer",
              }}
            >
              Remove
            </button>
          </div>
        )}

        <div
          style={{
            display: "flex",
            gap: 10,
            alignItems: "flex-start",
            background: "#141414",
            border: "1px solid #2a2a2a",
            borderRadius: 12,
            padding: 14,
            marginBottom: 16,
            color: "#bdbdbd",
          }}
        >
          <span style={{ fontSize: 18 }}>ℹ️</span>
          <div style={{ fontSize: 14, lineHeight: 1.5 }}>
            {isLoadingConfig
              ? "Loading saved settings..."
              : configuredGithub
              ? `Analyzing with configured GitHub user "${configuredGithub}"${
                  configuredEmail ? ` and email "${configuredEmail}"` : ""
                }.`
              : "You do not have a GitHub profile configured yet. Some project mining features may be limited until user settings are completed."}
          </div>
        </div>

        {fileValidationError && (
          <div
            style={{
              marginBottom: 12,
              color: "#ff8a8a",
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
              color: "#ff8a8a",
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
              color: "#8ad6a2",
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
          <div style={{ color: "#999", fontSize: 13 }}>
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
                border: "1px solid #2a2a2a",
                borderRadius: 10,
                color: isUploading || isLoadingConfig ? "#666" : "#ddd",
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
                isLoadingConfig
              }
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                border: "none",
                background:
                  !selectedFile ||
                  fileValidationError ||
                  isUploading ||
                  isLoadingConfig
                    ? "#202020"
                    : "#2b2b2b",
                color: "#fff",
                opacity:
                  !selectedFile ||
                  fileValidationError ||
                  isUploading ||
                  isLoadingConfig
                    ? 0.6
                    : 1,
                cursor:
                  !selectedFile ||
                  fileValidationError ||
                  isUploading ||
                  isLoadingConfig
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              {isUploading ? "Analzing..." : "Start Mining"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}