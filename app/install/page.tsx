"use client";

import { useEffect, useState } from "react";
import { Navigation } from "@/components/landing/navigation";
import { FooterSection } from "@/components/landing/footer-section";
import { Button } from "@/components/ui/button";
import {
  ArrowRight,
  Terminal,
  Key,
  FolderSearch,
  Shield,
  CheckCircle2,
  Copy,
  Check,
  ChevronDown,
  Download,
} from "lucide-react";

const steps = [
  {
    number: "01",
    icon: Terminal,
    title: "Download & Install BCB",
    description: "Download the BCBob CLI tool and install it with pip.",
    hasDownload: true,
    codeBlocks: [
      {
        label: "After downloading, run:",
        code: `unzip bcb-latest.zip
cd bcb
python3 -m pip install -e .`,
      },
    ],
    note: 'Expected output: Successfully installed bcb-0.1.0',
  },
  {
    number: "02",
    icon: Key,
    title: "Set Up API Key",
    description: "Configure your IBM Bob API credentials as environment variables.",
    hasDownload: false,
    codeBlocks: [
      {
        label: "macOS / Linux",
        code: `export BOB_API_KEY="your-api-key-here"`,
      },
      {
        label: "Windows PowerShell",
        code: `$env:BOB_API_KEY = "your-api-key-here"`,
      },
    ],
    note: null,
  },
  {
    number: "03",
    icon: FolderSearch,
    title: "Scan Your Codebase",
    description: "Run an initial report-only scan to identify vulnerabilities without making changes.",
    hasDownload: false,
    codeBlocks: [
      {
        label: "Report Only (recommended first)",
        code: `python3 run_bcb.py scan /path/to/project --report-only`,
      },
      {
        label: "Scan & Auto-Fix",
        code: `python3 run_bcb.py scan /path/to/project`,
      },
      {
        label: "Critical & High Only",
        code: `python3 run_bcb.py scan /path/to/project --severity critical --severity high`,
      },
    ],
    note: null,
  },
  {
    number: "04",
    icon: Shield,
    title: "Review & Fix",
    description: "Review the generated report and let BCBob auto-fix issues iteratively.",
    hasDownload: false,
    codeBlocks: [
      {
        label: "Auto-Fix with Iterations",
        code: `python3 run_bcb.py scan /path/to/project --max-iterations 5

# This will:
# 1. Discover vulnerabilities
# 2. Verify with IBM Bob LLM
# 3. Cluster into root causes
# 4. Generate & apply patches
# 5. Re-scan until clean`,
      },
    ],
    note: null,
  },
  {
    number: "05",
    icon: CheckCircle2,
    title: "Verify & Ship",
    description: "Run a final verification scan and commit your secured codebase.",
    hasDownload: false,
    codeBlocks: [
      {
        label: "Verify",
        code: `python3 run_bcb.py verify /path/to/project`,
      },
      {
        label: "Commit",
        code: `git add .
git commit -m "Security fixes from BCB scan"`,
      },
    ],
    note: 'Target: Production readiness ✅ READY',
  },
];

const requirements = [
  { name: "Python", version: "3.11+", description: "Runtime", link: null },
  { name: "Git", version: "Latest", description: "Patch management", link: null },
  { name: "IBM Bob API Key", version: "Get your API key", description: "LLM features", link: "https://bob.ibm.com/" },
];

const commands = [
  { cmd: "python3 run_bcb.py scan <path>", desc: "Full scan with auto-fix" },
  { cmd: "python3 run_bcb.py scan <path> --report-only", desc: "Generate report, no changes" },
  { cmd: "python3 run_bcb.py fix <path> --dry-run", desc: "Preview fixes without applying" },
  { cmd: "python3 run_bcb.py verify <path>", desc: "Verify applied fixes" },
  { cmd: "python3 run_bcb.py report <path> --format json", desc: "Export JSON for CI/CD" },
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 rounded-md hover:bg-foreground/10 transition-colors duration-200"
      aria-label="Copy code"
    >
      {copied ? (
        <Check className="w-3.5 h-3.5 text-green-500" />
      ) : (
        <Copy className="w-3.5 h-3.5 text-muted-foreground" />
      )}
    </button>
  );
}

function CodeBlock({ code, label }: { code: string; label: string }) {
  return (
    <div className="border border-foreground/10 overflow-hidden mt-4">
      {/* Window header */}
      <div className="px-4 py-2.5 border-b border-foreground/10 flex items-center justify-between bg-foreground/[0.02]">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-foreground/15" />
            <div className="w-2.5 h-2.5 rounded-full bg-foreground/15" />
            <div className="w-2.5 h-2.5 rounded-full bg-foreground/15" />
          </div>
          <span className="text-xs font-mono text-muted-foreground ml-2">
            {label}
          </span>
        </div>
        <CopyButton text={code} />
      </div>

      {/* Code content */}
      <div className="p-5 font-mono text-sm leading-relaxed overflow-x-auto">
        <pre className="text-foreground/80">
          {code.split("\n").map((line, i) => (
            <div key={i} className="flex">
              <span className="text-foreground/20 select-none w-8 shrink-0 text-right mr-4">
                {i + 1}
              </span>
              <span className={line.startsWith("#") ? "text-muted-foreground" : ""}>
                {line}
              </span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}

function StepCard({
  step,
  index,
}: {
  step: (typeof steps)[0];
  index: number;
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExpanded, setIsExpanded] = useState(index === 0);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 100 + index * 120);
    return () => clearTimeout(timer);
  }, [index]);

  const Icon = step.icon;

  return (
    <div
      className={`transition-all duration-700 ${
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-12"
      }`}
    >
      <div className="py-8 lg:py-10 border-b border-foreground/10">
        {/* Clickable header */}
        <div
          role="button"
          tabIndex={0}
          onClick={() => setIsExpanded(!isExpanded)}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setIsExpanded(!isExpanded); } }}
          className="w-full text-left cursor-pointer group"
        >
          <div className="flex items-start gap-6 lg:gap-10">
            {/* Number */}
            <div className="shrink-0 flex flex-col items-center gap-3">
              <span className="font-mono text-sm text-muted-foreground">
                {step.number}
              </span>
              <div className="w-10 h-10 rounded-full border border-foreground/20 flex items-center justify-center group-hover:border-ibm-blue group-hover:text-ibm-blue transition-colors duration-300">
                <Icon className="w-4 h-4" />
              </div>
            </div>

            {/* Header content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <h3 className="text-2xl lg:text-3xl font-display group-hover:translate-x-2 transition-transform duration-500">
                  {step.title}
                </h3>
                <ChevronDown
                  className={`w-5 h-5 text-muted-foreground transition-transform duration-300 shrink-0 ml-4 ${
                    isExpanded ? "rotate-180" : ""
                  }`}
                />
              </div>
              <p className="text-muted-foreground leading-relaxed mt-2 text-base lg:text-lg">
                {step.description}
              </p>
            </div>
          </div>
        </div>

        {/* Expandable content (outside the clickable area) */}
        <div
          className={`overflow-hidden transition-all duration-500 pl-16 lg:pl-20 ${
            isExpanded ? "max-h-[2000px] opacity-100 mt-4" : "max-h-0 opacity-0"
          }`}
        >
          {step.hasDownload && (
            <a
              href="/bcb-latest.zip"
              download="bcb-latest.zip"
              className="inline-flex items-center gap-3 mt-2 mb-2 px-6 py-3.5 bg-ibm-blue hover:bg-ibm-blue/90 text-white rounded-full text-sm font-medium transition-colors duration-200"
            >
              <Download className="w-4 h-4" />
              Download BCBob CLI
              <span className="text-white/60 font-mono text-xs">(.zip)</span>
            </a>
          )}

          {step.codeBlocks.map((block, i) => (
            <CodeBlock key={i} code={block.code} label={block.label} />
          ))}

          {step.note && (
            <div className="mt-4 flex items-center gap-3 px-4 py-3 bg-ibm-blue/5 border border-ibm-blue/10">
              <span className="w-2 h-2 rounded-full bg-ibm-blue shrink-0" />
              <span className="text-sm font-mono text-muted-foreground">
                {step.note}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function InstallPage() {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <main className="relative min-h-screen overflow-x-hidden noise-overlay">
      <Navigation />

      {/* Hero */}
      <section className="relative pt-24 lg:pt-32 pb-16 lg:pb-24 overflow-hidden">
        {/* Subtle grid lines */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none opacity-20">
          {[...Array(6)].map((_, i) => (
            <div
              key={`h-${i}`}
              className="absolute h-px bg-foreground/10"
              style={{
                top: `${16.66 * (i + 1)}%`,
                left: 0,
                right: 0,
              }}
            />
          ))}
          {[...Array(10)].map((_, i) => (
            <div
              key={`v-${i}`}
              className="absolute w-px bg-foreground/10"
              style={{
                left: `${10 * (i + 1)}%`,
                top: 0,
                bottom: 0,
              }}
            />
          ))}
        </div>

        <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
          {/* Breadcrumb */}
          <div
            className={`mb-10 transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground">
              <span className="w-8 h-px bg-foreground/30" />
              Installation Guide
            </span>
          </div>

          {/* Main headline */}
          <div className="mb-8">
            <h1
              className={`text-[clamp(2.5rem,8vw,5.5rem)] font-display leading-[0.9] tracking-tight transition-all duration-1000 ${
                isVisible
                  ? "opacity-100 translate-y-0"
                  : "opacity-0 translate-y-8"
              }`}
            >
              <span className="block">Get started</span>
              <span className="block">
                with{" "}
                <span className="text-ibm-blue">BCBob</span>
              </span>
            </h1>
          </div>

          <p
            className={`text-xl lg:text-2xl text-muted-foreground leading-relaxed max-w-2xl transition-all duration-700 delay-200 ${
              isVisible
                ? "opacity-100 translate-y-0"
                : "opacity-0 translate-y-4"
            }`}
          >
            Five steps to go from vulnerable vibe-coded prototype to production-ready software.
          </p>
        </div>
      </section>

      {/* Requirements */}
      <section className="relative py-12 lg:py-16 border-t border-foreground/10">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
          <div className="mb-8">
            <span className="inline-flex items-center gap-3 text-sm font-mono text-muted-foreground mb-4">
              <span className="w-8 h-px bg-foreground/30" />
              Prerequisites
            </span>
            <h2 className="text-3xl lg:text-4xl font-display tracking-tight">
              Requirements
            </h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
            {requirements.map((req, i) => (
              <div
                key={req.name}
                className={`p-6 border border-foreground/10 hover:border-foreground/20 transition-all duration-500 group`}
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <span className="text-xs font-mono text-muted-foreground block mb-3">
                  {req.description}
                </span>
                <h3 className="text-lg font-display group-hover:translate-x-1 transition-transform duration-300">
                  {req.name}
                </h3>
                {req.link ? (
                  <div className="text-sm font-mono mt-1">
                    <span className="text-ibm-blue">{req.version}</span>
                    <br />
                    <a
                      href={req.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-ibm-blue hover:text-ibm-blue/80 transition-colors duration-200 underline break-all"
                    >
                      {req.link}
                    </a>
                  </div>
                ) : (
                  <span className="text-sm text-ibm-blue font-mono mt-1 block">
                    {req.version}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Steps */}
      <section className="relative py-16 lg:py-24">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12">
          <div className="border-t border-foreground/10">
            {steps.map((step, index) => (
              <StepCard key={step.number} step={step} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* Command Reference */}
      <section className="relative py-16 lg:py-24 bg-foreground text-background overflow-hidden">
        {/* Diagonal lines pattern */}
        <div className="absolute inset-0 opacity-[0.03] pointer-events-none">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `repeating-linear-gradient(
              -45deg,
              transparent,
              transparent 40px,
              currentColor 40px,
              currentColor 41px
            )`,
            }}
          />
        </div>

        <div className="relative z-10 max-w-[1400px] mx-auto px-6 lg:px-12">
          <div className="mb-12 lg:mb-16">
            <span className="inline-flex items-center gap-3 text-sm font-mono text-background/50 mb-6">
              <span className="w-8 h-px bg-background/30" />
              Reference
            </span>
            <h2 className="text-4xl lg:text-6xl font-display tracking-tight">
              CLI Commands
            </h2>
          </div>

          <div className="grid gap-0">
            {commands.map((item, i) => (
              <div
                key={i}
                className="flex flex-col lg:flex-row lg:items-center justify-between py-6 border-b border-background/10 group"
              >
                <div className="flex items-center gap-4">
                  <span className="text-background/30 font-mono text-sm shrink-0">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <code className="font-mono text-sm lg:text-base text-background/80 group-hover:text-background transition-colors duration-300">
                    {item.cmd}
                  </code>
                </div>
                <span className="text-sm text-background/40 mt-2 lg:mt-0 ml-10 lg:ml-0">
                  {item.desc}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative py-24 lg:py-32">
        <div className="max-w-[1400px] mx-auto px-6 lg:px-12 text-center">
          <h2
            className="text-4xl lg:text-6xl font-display tracking-tight mb-8"
          >
            Ready to secure
            <br />
            <span className="text-muted-foreground">your codebase?</span>
          </h2>

          <p className="text-xl text-muted-foreground mb-12 max-w-xl mx-auto leading-relaxed">
            Install BCBob and start auditing in under 5 minutes. No configuration headaches.
          </p>

          <Button
            asChild
            size="lg"
            className="bg-ibm-blue hover:bg-ibm-blue/90 text-white px-8 h-14 text-base rounded-full group"
          >
            <a
              href="/bcb-latest.zip"
              download="bcb-latest.zip"
              className="flex items-center justify-center"
            >
              <Download className="w-4 h-4 mr-2" />
              Download BCBob CLI
              <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
            </a>
          </Button>
        </div>
      </section>

      <FooterSection />
    </main>
  );
}
