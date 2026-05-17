# BCBob - IBM Bob Hackathon Project

![BCBob Banner](public/ibm-bob.png)

A modern landing page and CLI tool for BCBob (Better Code Bob), an AI-powered security auditing and code fixing tool built for the IBM Bob Hackathon.

## 🌟 Overview

BCBob leverages IBM Bob's AI capabilities to continuously audit, fix, and verify your codebase for security vulnerabilities. Transform your vibe-coded prototype into production-ready software in minutes.

## 🚀 Features

- **AI-Powered Security Auditing** - Automated vulnerability detection using IBM Bob LLM
- **Intelligent Auto-Fix** - Iterative patching with root cause analysis
- **Modern Landing Page** - Built with Next.js 16, React 19, and Tailwind CSS
- **CLI Tool** - Python-based command-line interface for seamless integration
- **Real-time Verification** - Continuous scanning and validation

## 📦 Project Structure

```
BCBob-IBM-Bob/
├── app/                    # Next.js app directory
│   ├── install/           # Installation guide page
│   ├── page.tsx           # Landing page
│   └── layout.tsx         # Root layout
├── components/            # React components
│   ├── landing/          # Landing page sections
│   └── ui/               # Reusable UI components
├── bcb/                   # BCBob CLI tool
│   ├── bcb/              # Python package
│   ├── setup.py          # Package setup
│   └── run_bcb.py        # CLI entry point
├── public/               # Static assets
│   └── bcb-latest.zip    # Downloadable CLI tool
└── BOB report-history/   # Task history and reports
```

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 16.0.10 with Turbopack
- **UI Library**: React 19.2.0
- **Styling**: Tailwind CSS 4.1.9
- **Components**: Radix UI, shadcn/ui
- **3D Graphics**: React Three Fiber
- **Animations**: Framer Motion (via Tailwind Animate)

### Backend/CLI
- **Language**: Python 3.11+
- **AI Integration**: IBM Bob LLM
- **Security Scanning**: Custom pattern matching
- **Patch Management**: Git-based workflow

## 🚀 Getting Started

### Prerequisites

- Node.js 18+ (for the landing page)
- Python 3.11+ (for the CLI tool)
- Git
- IBM Bob API Key

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/cytojen/BCBob-IBM-Bob.git
cd BCBob-IBM-Bob
```

#### 2. Install Landing Page Dependencies

```bash
npm install --legacy-peer-deps
```

#### 3. Run the Development Server

```bash
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to see the landing page.

#### 4. Install BCBob CLI

Download the CLI tool from the website or extract from `public/bcb-latest.zip`:

```bash
unzip public/bcb-latest.zip
python3 -m pip install -e .
```

#### 5. Configure API Key

```bash
# macOS / Linux
export BOB_API_KEY="your-api-key-here"

# Windows PowerShell
$env:BOB_API_KEY = "your-api-key-here"
```

Get your API key at [https://bob.ibm.com/](https://bob.ibm.com/)

## 📖 Usage

### BCBob CLI Commands

```bash
# Full scan with auto-fix
python3 run_bcb.py scan /path/to/project

# Report only (no changes)
python3 run_bcb.py scan /path/to/project --report-only

# Preview fixes without applying
python3 run_bcb.py fix /path/to/project --dry-run

# Verify applied fixes
python3 run_bcb.py verify /path/to/project

# Export JSON for CI/CD
python3 run_bcb.py report /path/to/project --format json
```

### Advanced Options

```bash
# Scan with severity filtering
python3 run_bcb.py scan /path/to/project --severity critical --severity high

# Auto-fix with iterations
python3 run_bcb.py scan /path/to/project --max-iterations 5
```

## 🎨 Landing Page Features

- **Responsive Design** - Mobile-first approach with smooth animations
- **Interactive 3D Elements** - Animated sphere, tetrahedron, and wave graphics
- **Dark/Light Mode** - Theme switching with next-themes
- **Installation Guide** - Step-by-step instructions with code snippets
- **Copy-to-Clipboard** - Easy command copying
- **Download Integration** - Direct CLI tool download

## 🔧 Development

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

### Environment Variables

Create a `.env.local` file for local development:

```env
BOB_API_KEY=your-api-key-here
```

## 📝 Contributing

This project was built for the IBM Bob Hackathon. Contributions are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is part of the IBM Bob Hackathon submission.

## 🙏 Acknowledgments

- **IBM Bob Team** - For providing the AI platform and hackathon opportunity
- **Next.js Team** - For the amazing React framework
- **Radix UI & shadcn/ui** - For the beautiful component library
- **Vercel** - For hosting and deployment

---

Built with ❤️ for the IBM Bob Hackathon
