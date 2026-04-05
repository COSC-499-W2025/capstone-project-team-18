import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import WavingHandIcon from "@mui/icons-material/WavingHand";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PersonIcon from "@mui/icons-material/Person";
import GitHubIcon from "@mui/icons-material/GitHub";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import DescriptionIcon from "@mui/icons-material/Description";
import WebIcon from "@mui/icons-material/Web";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import FolderIcon from "@mui/icons-material/Folder";
import type { SvgIconProps } from "@mui/material";

const TOUR_KEY = "tour_completed";
const PAD = 12; // padding around the spotlight cutout
const TOOLTIP_W = 320; // max tooltip width
const TOOLTIP_H_EST = 250; // estimated tooltip height for placement logic
const EDGE = 20; // minimum gap between tooltip and viewport edge

// Z-index layers
const BACKDROP_Z = 9989; // blocks all page interaction; provides dark overlay
const SPOT_Z = 9990;     // spotlight cutout (box-shadow technique, pointer-events:none)
const TOOLTIP_Z = 9995;  // tour tooltip card

type TourStep = {
  /** Exact path this step lives on, OR a path prefix when pathMatch is "startsWith" */
  path: string;
  /** How to match location.pathname against `path`. Default: "exact" */
  pathMatch?: "exact" | "startsWith";
  /** Called when the tour needs to navigate to this step's page (overrides `path`). */
  navigateTo?: () => string;
  selector: string | null; // null = centered welcome card
  title: string;
  description: string;
  pulse?: boolean; // show pulsing ring (important action buttons)
  /** If the selector is never found, navigate here and retry before skipping. */
  fallbackPath?: string;
  Icon: React.ComponentType<SvgIconProps>;
};

const steps: TourStep[] = [
  {
    path: "/",
    selector: null,
    title: "Welcome to Digital Artifact Miner!",
    description:
      "Let's take a guided tour of the app. We'll walk you through each section step by step, and show you the key features along the way!",
    Icon: WavingHandIcon,
  },
  {
    path: "/",
    selector: '[data-tour="nav-bar"]',
    title: "Navigation Bar",
    description:
      "Use this navigation bar to move between the major sections of the app.",
    Icon: DashboardIcon,
  },
  {
    path: "/",
    selector: '[data-tour="dashboard-grid"]',
    title: "Your Dashboard",
    description:
      "The Dashboard gives you an overview of all your projects, resumes, and portfolios. You can click on any item here to view details or make edits.",
    Icon: DashboardIcon,
  },
  {
    path: "/",
    selector: '[data-tour="upload-project-btn"]',
    title: "Upload a Project",
    description:
      "Use this button to upload a project. You can upload a ZIP file of your coding projects and the app will automatically analyze it for skills, technologies, contributions, and other insights!",
    Icon: CloudUploadIcon,
    pulse: true,
  },
  {
    path: "/profile",
    selector: '[data-tour="profile-info"]',
    title: "Your Profile Information",
    description:
      "This is where you can fill in your name, education history, awards, and skills. This information is used to personalize all generated resumes and portfolios.",
    Icon: PersonIcon,
  },
  {
    path: "/profile",
    selector: '[data-tour="github-connect"]',
    title: "Connect GitHub",
    description:
      "Connect your GitHub account to automatically deploy your portfolio to a GitHub Pages site for others to view!",
    Icon: GitHubIcon,
    pulse: true,
  },
  {
    path: "/profile",
    selector: '[data-tour="consent-section"]',
    title: "Data & AI Consent",
    description:
      "We require explicit consent to analyze any of your data. You may also enable an optional AI-assisted analysis for deeper insights and additional features.",
    Icon: PersonIcon,
  },
  {
    path: "/projects",
    selector: '[data-tour="projects-header"]',
    title: "Projects Page",
    description:
      "All your projects will appear here. Select a project to view its full analysis including the skills detected, technologies used, and contributions summarized.",
    Icon: FolderIcon,
  },
  {
    path: "/resumes",
    selector: '[data-tour="create-resume-btn"]',
    title: "Create a Resume",
    description:
      "You can generate a resume from your project data. Select which projects to include and get a tailored resume.",
    Icon: DescriptionIcon,
    pulse: true,
  },
  {
    // Always use the tour example resume — avoids API loading delays on real pages.
    path: "/resume/tour",
    navigateTo: () => "/resume/tour",
    selector: '[data-tour="export-pdf-btn"]',
    title: "Export as PDF",
    description:
      "The PDF export provides a polished, submission-ready version of your resume, formatted and ready for job applications without any additional edits.",
    Icon: DescriptionIcon,
    pulse: true,
  },
  {
    path: "/resume/tour",
    navigateTo: () => "/resume/tour",
    selector: '[data-tour="export-docx-btn"]',
    title: "Export as Word Document",
    description:
      "For those who prefer a more familiar tool, the .docx export provides the flexibility to further refine and expand their resume in Microsoft Word.",
    Icon: DescriptionIcon,
  },
  {
    path: "/portfolios",
    selector: '[data-tour="create-portfolio-btn"]',
    title: "Create & Deploy a Portfolio",
    description:
      "Build a portfolio website to show off your work. You can provide a summary about yourself, showcase your favorite projects, and more. \
      When you're ready to share, you can deploy the website via GitHub Pages (requires a connected GitHub account), or download the portfolio locally.",
    Icon: WebIcon,
    pulse: true,
  },
  {
    path: "/portfolios",
    selector: null,
    title: "You're All Set!",
    description:
      "That's the full tour. Set up your profile, upload your projects, then generate resumes and portfolios tailored to each opportunity!",
    Icon: RocketLaunchIcon,
  },
];

export function hasTourBeenCompleted(): boolean {
  return localStorage.getItem(TOUR_KEY) === "true";
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

export default function WalkthroughTour({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  // Stable ref so the tryFind polling can call the latest goNext without a stale closure
  const goNextRef = useRef<() => void>(() => {});

  const current = steps[step];
  const isLast = step === steps.length - 1;
  const isCentered = current.selector === null;
  const showSpotlight = !isCentered && targetRect !== null;
  // Dark backdrop during navigation and centered steps; transparent when spotlight is up
  const darkBackdrop = isCentered || (!isCentered && targetRect === null);

  function finish() {
    localStorage.setItem(TOUR_KEY, "true");
    navigate("/");
    onClose();
  }

  function goNext() {
    if (isLast) {
      finish();
    } else {
      setTargetRect(null);
      setStep((s) => s + 1);
    }
  }

  function goBack() {
    if (step > 0) {
      setTargetRect(null);
      setStep((s) => s - 1);
    }
  }

  // Keep the ref in sync every render
  useEffect(() => { goNextRef.current = goNext; });

  // Navigate to step's page, then poll until the target element appears.
  // If the element is never found (e.g. no resume exists yet), auto-advance.
  useEffect(() => {
    const { path, pathMatch = "exact", navigateTo, selector, fallbackPath } = steps[step];

    const pathOk = pathMatch === "startsWith"
      ? location.pathname.startsWith(path)
      : location.pathname === path;

    if (!pathOk) {
      setTargetRect(null);
      navigate(navigateTo ? navigateTo() : path);
      return;
    }

    if (!selector) {
      setTargetRect(null);
      return;
    }

    let attempts = 0;
    let timeoutId: ReturnType<typeof setTimeout>;

    function tryFind() {
      const el = document.querySelector(selector!);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        // Wait for scroll to settle before measuring
        setTimeout(() => {
          setTargetRect(el.getBoundingClientRect());
        }, 300);
      } else if (attempts < 20) {
        attempts++;
        timeoutId = setTimeout(tryFind, 150);
      } else if (fallbackPath && location.pathname !== fallbackPath) {
        // Element not found on original page — try the fallback path (e.g. tour example resume)
        navigate(fallbackPath);
      } else {
        // Element still not found even on fallback — skip step
        goNextRef.current();
      }
    }

    timeoutId = setTimeout(tryFind, 150);
    return () => clearTimeout(timeoutId);
  }, [step, location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep the spotlight rect current while the step is displayed
  useEffect(() => {
    const { selector } = current;
    if (!selector) return;

    function update() {
      const el = document.querySelector(selector!);
      if (el) setTargetRect(el.getBoundingClientRect());
    }

    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [step]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Tooltip position ─────────────────────────────────────────────────────
  // Uses clientWidth/clientHeight (excludes scrollbars and OS chrome) to
  // avoid clipping in Electron. Prefers the side with more room.
  type TooltipPos = { top: number; left: number; width: number; maxHeight: number };

  function getTooltipPos(rect: DOMRect): TooltipPos {
    const W = document.documentElement.clientWidth;
    const H = document.documentElement.clientHeight;
    const width = Math.min(TOOLTIP_W, W - EDGE * 2);
    const spotCenterX = rect.left + rect.width / 2;
    const left = clamp(spotCenterX - width / 2, EDGE, W - width - EDGE);

    // Give the tooltip the full viewport height so content never needs to scroll.
    // Prefer the side with more room; if neither fits, clamp into viewport.
    const maxHeight = H - EDGE * 2;
    const gapAbove = rect.top - PAD - 8 - EDGE;
    const gapBelow = H - rect.bottom - PAD - 8 - EDGE;

    let top: number;
    if (gapBelow >= TOOLTIP_H_EST || gapBelow >= gapAbove) {
      top = rect.bottom + PAD + 8;
    } else {
      top = rect.top - PAD - 8 - TOOLTIP_H_EST;
    }
    // Clamp so tooltip always stays within the viewport (may overlap spotlight)
    top = clamp(top, EDGE, H - TOOLTIP_H_EST - EDGE);

    return { top, left, width, maxHeight };
  }

  const tooltipPos = targetRect ? getTooltipPos(targetRect) : null;
  const { Icon } = current;

  // ─── Shared nav controls ───────────────────────────────────────────────────
  function NavControls() {
    return (
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button
          onClick={finish}
          style={{
            background: "transparent",
            border: "none",
            color: "var(--text-muted)",
            fontSize: 13,
            cursor: "pointer",
            padding: "4px 0",
          }}
        >
          Skip tour
        </button>
        <div style={{ display: "flex", gap: 8 }}>
          {step > 0 && (
            <button
              onClick={goBack}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "transparent",
                color: "var(--text-primary)",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Back
            </button>
          )}
          <button
            onClick={goNext}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border: "none",
              background: "var(--btn-primary)",
              color: "#fff",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isLast ? "Done!" : "Next →"}
          </button>
        </div>
      </div>
    );
  }

  // ─── Progress bar ──────────────────────────────────────────────────────────
  function ProgressBar() {
    return (
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {steps.map((_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 3,
              borderRadius: 99,
              background: i <= step ? "var(--btn-primary)" : "var(--border)",
              transition: "background 0.2s ease",
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <>
      <style>{`
        @keyframes tour-pulse {
          0%   { box-shadow: 0 0 0 9999px rgba(0,0,0,0.65), 0 0 0 0   rgba(0,84,166,0.5); }
          60%  { box-shadow: 0 0 0 9999px rgba(0,0,0,0.65), 0 0 0 8px rgba(0,84,166,0);   }
          100% { box-shadow: 0 0 0 9999px rgba(0,0,0,0.65), 0 0 0 0   rgba(0,84,166,0.5); }
        }
        @keyframes tour-fadein {
          from { opacity: 0; }
          to   { opacity: 1; }
        }
      `}</style>

      {/*
        ── Universal backdrop ──────────────────────────────────────────────────
        Always rendered. Blocks ALL page interaction so nothing behind the tour
        can be accidentally clicked or typed into.
        • Dark + flex  → centered card steps (welcome / finish)
        • Dark + block → navigating between pages (smooth transition)
        • Transparent  → spotlight active (spotlight's box-shadow is the overlay)
      */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          zIndex: BACKDROP_Z,
          background: darkBackdrop ? "rgba(0,0,0,0.65)" : "transparent",
          display: isCentered ? "flex" : "block",
          alignItems: "center",
          justifyContent: "center",
          padding: isCentered ? 24 : 0,
        }}
      >
        {/* ── Centered card (welcome / finish steps) ── */}
        {isCentered && (
          <div
            style={{
              width: "100%",
              maxWidth: 460,
              background: "var(--bg-surface)",
              borderRadius: 20,
              padding: "32px 36px",
              boxShadow: "0 24px 64px rgba(0,0,0,0.4)",
              border: "1px solid var(--border)",
              animation: "tour-fadein 0.2s ease",
            }}
          >
            <ProgressBar />

            <div style={{ display: "flex", justifyContent: "center", marginBottom: 18 }}>
              <div
                style={{
                  width: 68,
                  height: 68,
                  borderRadius: "50%",
                  background: "var(--accent-subtle, #e8f0fe)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon style={{ fontSize: 34, color: "var(--btn-primary)" }} />
              </div>
            </div>

            <h2
              style={{
                margin: "0 0 10px",
                fontSize: 21,
                fontWeight: 700,
                textAlign: "center",
                color: "var(--text-primary)",
              }}
            >
              {current.title}
            </h2>
            <p
              style={{
                margin: "0 0 28px",
                color: "var(--text-secondary)",
                fontSize: 14,
                lineHeight: 1.65,
                textAlign: "center",
                whiteSpace: "pre-line",
              }}
            >
              {current.description}
            </p>

            <div style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center", marginBottom: 18 }}>
              {step + 1} of {steps.length}
            </div>

            <NavControls />
          </div>
        )}
      </div>

      {/*
        ── Spotlight ────────────────────────────────────────────────────────────
        Single element using box-shadow for the dark overlay so the cutout
        naturally inherits border-radius → true rounded corners.
        pointer-events: none means the backdrop below still blocks clicks
        inside the cutout hole.
      */}
      {showSpotlight && targetRect && (
        <div
          style={{
            position: "fixed",
            top: targetRect.top - PAD,
            left: targetRect.left - PAD,
            width: targetRect.width + PAD * 2,
            height: targetRect.height + PAD * 2,
            borderRadius: 14,
            border: "2px solid var(--btn-primary)",
            boxShadow: "0 0 0 9999px rgba(0,0,0,0.65)",
            zIndex: SPOT_Z,
            pointerEvents: "none",
            animation: current.pulse
              ? "tour-pulse 1.8s ease-in-out infinite"
              : "tour-fadein 0.25s ease",
          }}
        />
      )}

      {/*
        ── Floating tooltip (spotlight steps) ──────────────────────────────────
        Positioned above or below the spotlight, whichever side has more room.
        Clamped to viewport using clientWidth/clientHeight (reliable in Electron).
      */}
      {showSpotlight && tooltipPos && (
        <div
          style={{
            position: "fixed",
            ...tooltipPos,
            zIndex: TOOLTIP_Z,
            background: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: "18px 20px",
            boxShadow: "0 12px 40px rgba(0,0,0,0.35)",
            animation: "tour-fadein 0.2s ease",
            boxSizing: "border-box",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <ProgressBar />

          {/* Scrollable body — buttons always stay visible below */}
          <div style={{ overflowY: "auto", flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: "50%",
                  background: "var(--accent-subtle, #e8f0fe)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <Icon style={{ fontSize: 18, color: "var(--btn-primary)" }} />
              </div>
              <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>
                {current.title}
              </div>
            </div>

            <p
              style={{
                margin: "0 0 14px",
                fontSize: 13,
                color: "var(--text-secondary)",
                lineHeight: 1.55,
                wordBreak: "break-word",
                whiteSpace: "pre-line",
              }}
            >
              {current.description}
            </p>

            <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 12 }}>
              {step + 1} of {steps.length}
            </div>
          </div>

          <NavControls />
        </div>
      )}
    </>
  );
}
