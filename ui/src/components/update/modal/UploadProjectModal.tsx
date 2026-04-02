import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../../api/apiClient";
import InfoIcon from '@mui/icons-material/Info';
import FolderIcon from '@mui/icons-material/Folder';


type UploadProjectModalProps = {
  open: boolean;
  onClose: () => void;
  onUploadSuccess?: (file: File) => void;
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
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoadingConfig, setIsLoadingConfig] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
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

        if (!res?.consent) {
          onClose();
          navigate("/profile", { state: { consentRequired: true } });
          return;
        }

        setConfiguredGithub(res?.github?.trim?.() ?? "");
        setHasConsent(true);
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

  if (!open || hasConsent !== true) return null;

  function resetState() {
    setSelectedFile(null);
    setIsDragging(false);
    setIsLoadingConfig(false);
    setUploadError(null);
    setConfiguredGithub("");
    setHasConsent(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleClose() {
    if (isLoadingConfig) return;
    resetState();
    onClose();
  }

  function handleChooseFile() {
    if (isLoadingConfig) return;
    inputRef.current?.click();
  }

  function handleSelectedFile(file: File | null) {
    setUploadError(null);
    setSelectedFile(file);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    handleSelectedFile(file);
  }

  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0] ?? null;
    handleSelectedFile(file);
  }

  function handleRemoveFile() {
    setSelectedFile(null);
    setUploadError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }

  function handleUpload() {
    setUploadError(null);

    if (!selectedFile) {
      setUploadError("Please select a project archive before uploading.");
      return;
    }

    if (fileValidationError) {
      setUploadError(fileValidationError);
      return;
    }

    if (hasConsent === false) {
      resetState();
      onClose();
      navigate("/profile", { state: { consentRequired: true } });
      return;
    }

    const fileToUpload = selectedFile;
    resetState();
    onClose();
    onUploadSuccess?.(fileToUpload);
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
            disabled={isLoadingConfig}
            style={{
              border: "none",
              background: "transparent",
              color: isLoadingConfig ? "#777" : "#444",
              fontSize: 20,
              cursor: isLoadingConfig ? "not-allowed" : "pointer",
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
          disabled={isLoadingConfig}
          style={{ display: "none" }}
        />

        <div
          onClick={handleChooseFile}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            border: `2px dashed ${isDragging ? "#6b7280" : "#0055B7"}`,
            borderRadius: 16,
            padding: "48px 24px",
            textAlign: "center",
            background: isDragging ? "#f0f4ff" : "var(--bg-surface)",
            marginBottom: 16,
            cursor: isLoadingConfig ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
            opacity: isLoadingConfig ? 0.7 : 1,
          }}
        >
          <div style={{ fontSize: 32, marginBottom: 12 }}>
            <FolderIcon style={{ fontSize: 32 }} />
          </div>
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
              disabled={isLoadingConfig}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid var(--border)",
                background: "transparent",
                color: isLoadingConfig ? "#777" : "#444",
                cursor: isLoadingConfig ? "not-allowed" : "pointer",
              }}
            >
              Remove
            </button>
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
            color: "var(--text-secondary)",
          }}
        >
          <InfoIcon style={{ fontSize: 18, flexShrink: 0, color: "var(--accent)" }} />
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
              disabled={isLoadingConfig}
              style={{
                padding: "10px 14px",
                background: "transparent",
                border: "1px solid var(--border)",
                borderRadius: 10,
                color: isLoadingConfig ? "#777" : "#444",
                cursor: isLoadingConfig ? "not-allowed" : "pointer",
              }}
            >
              Cancel
            </button>

            <button
              onClick={handleUpload}
              disabled={!selectedFile || !!fileValidationError || isLoadingConfig}
              style={{
                padding: "10px 16px",
                borderRadius: 10,
                border: "none",
                background:
                  !selectedFile || fileValidationError || isLoadingConfig
                    ? "#202020"
                    : "#0055B7",
                color: "#fff",
                opacity: !selectedFile || fileValidationError || isLoadingConfig ? 0.6 : 1,
                cursor:
                  !selectedFile || fileValidationError || isLoadingConfig
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              Start Mining
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
