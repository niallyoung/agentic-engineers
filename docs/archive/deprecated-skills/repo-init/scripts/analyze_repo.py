# -*- coding: utf-8 -*-
"""
analyze_repo.py — Phase 1: Repository analysis for repo-init skill.

Scans a target repository to detect:
- Primary programming language
- Package manager
- Test framework
- CI/CD provider
- Monorepo structure
- Existing documentation
- License
- Git metadata (remote, contributor count)

Author: Senior Engineer
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# ── Language detection ────────────────────────────────────────────────────────

_LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".swift": "swift",
    ".scala": "scala",
}

# ── Package manager detection (ordered: first match wins) ─────────────────────

_PACKAGE_MANAGER_FILES: list[tuple[str, str]] = [
    ("pyproject.toml", "pip/poetry"),
    ("requirements.txt", "pip"),
    ("requirements.in", "pip"),
    ("package.json", "npm"),  # May be yarn/pnpm — checked below
    ("go.mod", "go"),
    ("Cargo.toml", "cargo"),
    ("pom.xml", "maven"),
    ("build.gradle", "gradle"),
    ("build.gradle.kts", "gradle"),
    ("Gemfile", "bundler"),
    ("composer.json", "composer"),
    ("pubspec.yaml", "pub"),
    ("mix.exs", "mix"),
]

# ── Test framework detection ──────────────────────────────────────────────────

_TEST_FRAMEWORK_SIGNALS: list[tuple[str, str]] = [
    ("pytest.ini", "pytest"),
    ("setup.cfg", "pytest"),       # May contain [tool:pytest]
    ("pyproject.toml", "pytest"),  # May contain [tool.pytest.ini_options]
    ("jest.config.js", "jest"),
    ("jest.config.ts", "jest"),
    ("jest.config.cjs", "jest"),
    ("vitest.config.ts", "vitest"),
    ("vitest.config.js", "vitest"),
    ("go.mod", "go-test"),         # Go always has go test
    ("Cargo.toml", "cargo-test"),  # Rust always has cargo test
    ("phpunit.xml", "phpunit"),
    ("RSpec", "rspec"),            # Directory signal
]

# ── CI/CD detection ───────────────────────────────────────────────────────────

_CI_SIGNALS: list[tuple[str, str]] = [
    (".github/workflows", "github-actions"),
    (".gitlab-ci.yml", "gitlab-ci"),
    ("Jenkinsfile", "jenkins"),
    (".circleci", "circleci"),
    (".buildkite", "buildkite"),
    (".travis.yml", "travis"),
    ("azure-pipelines.yml", "azure-pipelines"),
    ("bitbucket-pipelines.yml", "bitbucket"),
    (".drone.yml", "drone"),
]

# ── Framework detection ───────────────────────────────────────────────────────

_FRAMEWORK_SIGNALS: dict[str, list[str]] = {
    "django": ["django", "DJANGO_SETTINGS_MODULE"],
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "express": ["express"],
    "nextjs": ["next.config.js", "next.config.ts"],
    "nuxt": ["nuxt.config.ts", "nuxt.config.js"],
    "gin": ["gin-gonic/gin"],
    "echo": ["labstack/echo"],
    "rails": ["config/routes.rb"],
    "spring": ["src/main/java"],
}


# ============================================================================
# RESULT
# ============================================================================

@dataclass
class AnalysisResult:
    """Complete analysis of a target repository."""

    repo_root: Path
    project_name: str
    primary_language: str = "unknown"
    secondary_languages: List[str] = field(default_factory=list)
    package_manager: str = "unknown"
    test_framework: str = "unknown"
    ci_provider: str = "none"
    framework: str = "unknown"
    is_monorepo: bool = False
    has_readme: bool = False
    has_docs: bool = False
    license: str = "unknown"
    git_remote: str = ""
    contributor_count: int = 0
    total_files: int = 0
    size_class: str = "small"     # "small" | "medium" | "large"
    existing_spec: bool = False
    existing_agents: bool = False
    existing_init: bool = False


# ============================================================================
# ANALYZER
# ============================================================================

def analyze_repo(repo_root: Path) -> AnalysisResult:
    """
    Full Phase 1 analysis of a repository.

    Args:
        repo_root: Absolute path to the target repository.

    Returns:
        AnalysisResult with all detected attributes.
    """
    repo_root = Path(repo_root).resolve()

    result = AnalysisResult(
        repo_root=repo_root,
        project_name=repo_root.name.lower().replace(" ", "-"),
    )

    result.primary_language, result.secondary_languages = _detect_languages(repo_root)
    result.package_manager = _detect_package_manager(repo_root)
    result.test_framework = _detect_test_framework(repo_root, result.package_manager)
    result.ci_provider = _detect_ci(repo_root)
    result.framework = _detect_framework(repo_root)
    result.is_monorepo = _detect_monorepo(repo_root)
    result.has_readme = (repo_root / "README.md").is_file()
    result.has_docs = (repo_root / "docs").is_dir()
    result.license = _detect_license(repo_root)
    result.git_remote = _detect_git_remote(repo_root)
    result.contributor_count = _count_contributors(repo_root)
    result.total_files = _count_files(repo_root)
    result.size_class = _classify_size(result.total_files)
    result.existing_spec = (repo_root / "docs" / "SPEC.md").is_file()
    result.existing_agents = (repo_root / "agents").is_dir()
    result.existing_init = (
        repo_root / ".agentic-engineers" / "INIT-COMPLETE.yaml"
    ).is_file()

    return result


# ============================================================================
# DETECTION HELPERS
# ============================================================================

def _detect_languages(repo_root: Path) -> tuple[str, list[str]]:
    """Count files per language extension; return (primary, secondaries)."""
    counts: dict[str, int] = {}
    for path in repo_root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            lang = _LANGUAGE_EXTENSIONS.get(path.suffix.lower())
            if lang:
                counts[lang] = counts.get(lang, 0) + 1

    if not counts:
        return "unknown", []

    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondaries = [lang for lang, _ in ranked[1:] if lang != primary]
    return primary, secondaries


def _detect_package_manager(repo_root: Path) -> str:
    """First matching package manager file wins."""
    for filename, pm in _PACKAGE_MANAGER_FILES:
        if (repo_root / filename).exists():
            if pm == "npm":
                # Refine: check packageManager field in package.json
                pkg = repo_root / "package.json"
                try:
                    data = json.loads(pkg.read_text())
                    pm_field = data.get("packageManager", "")
                    if pm_field.startswith("yarn"):
                        return "yarn"
                    if pm_field.startswith("pnpm"):
                        return "pnpm"
                except Exception:
                    pass
                # Fallback: check for lockfiles
                if (repo_root / "yarn.lock").exists():
                    return "yarn"
                if (repo_root / "pnpm-lock.yaml").exists():
                    return "pnpm"
            return pm
    return "unknown"


def _detect_test_framework(repo_root: Path, package_manager: str) -> str:
    """Detect test framework from config files and language signals."""
    for filename, fw in _TEST_FRAMEWORK_SIGNALS:
        target = repo_root / filename
        if target.exists():
            # For pyproject.toml/setup.cfg, verify pytest is actually configured
            if filename in ("pyproject.toml", "setup.cfg"):
                content = target.read_text(errors="ignore")
                if "pytest" in content:
                    return "pytest"
                continue
            return fw

    # npm-based: look in package.json scripts
    if package_manager in ("npm", "yarn", "pnpm"):
        pkg = repo_root / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text())
                scripts = data.get("scripts", {})
                test_script = scripts.get("test", "")
                if "jest" in test_script:
                    return "jest"
                if "vitest" in test_script:
                    return "vitest"
                if "mocha" in test_script:
                    return "mocha"
            except Exception:
                pass

    return "unknown"


def _detect_ci(repo_root: Path) -> str:
    """First matching CI signal wins."""
    for path_fragment, provider in _CI_SIGNALS:
        if (repo_root / path_fragment).exists():
            return provider
    return "none"


def _detect_framework(repo_root: Path) -> str:
    """Detect web/application framework from config files and imports."""
    for fw, signals in _FRAMEWORK_SIGNALS.items():
        for signal in signals:
            if (repo_root / signal).exists():
                return fw
            # Check for imports in Python files (limited scan)
            if fw in ("django", "fastapi", "flask"):
                for py_file in list(repo_root.glob("*.py"))[:20]:
                    try:
                        if fw in py_file.read_text(errors="ignore")[:2000]:
                            return fw
                    except Exception:
                        pass
    return "unknown"


def _detect_monorepo(repo_root: Path) -> bool:
    """Detect monorepo structures."""
    monorepo_dirs = ("packages", "apps", "services", "modules")
    for d in monorepo_dirs:
        target = repo_root / d
        if target.is_dir():
            # Require at least 2 subdirectories to call it a monorepo
            subdirs = [x for x in target.iterdir() if x.is_dir()]
            if len(subdirs) >= 2:
                return True

    # Check package.json workspaces
    pkg = repo_root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text())
            if "workspaces" in data:
                return True
        except Exception:
            pass

    return False


def _detect_license(repo_root: Path) -> str:
    """Detect license from LICENSE file first line."""
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
        path = repo_root / name
        if path.exists():
            try:
                first_line = path.read_text(errors="ignore").strip().splitlines()[0]
                # Normalize common licenses
                upper = first_line.upper()
                if "MIT" in upper:
                    return "MIT"
                if "APACHE" in upper:
                    return "Apache-2.0"
                if "GPL" in upper:
                    return "GPL"
                if "BSD" in upper:
                    return "BSD"
                if "ISC" in upper:
                    return "ISC"
                if "PROPRIETARY" in upper or "ALL RIGHTS RESERVED" in upper:
                    return "proprietary"
                return "other"
            except Exception:
                return "unknown"

    return "unknown"


def _detect_git_remote(repo_root: Path) -> str:
    """Get first git remote URL."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _count_contributors(repo_root: Path) -> int:
    """Count unique contributor emails from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--format=%ae"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return 0
        emails = set(e.strip() for e in result.stdout.splitlines() if e.strip())
        return len(emails)
    except Exception:
        return 0


def _count_files(repo_root: Path) -> int:
    """Count non-git files in repository."""
    count = 0
    for path in repo_root.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            count += 1
    return count


def _classify_size(total_files: int) -> str:
    """Classify repository size for default tuning."""
    if total_files < 100:
        return "small"
    if total_files < 1000:
        return "medium"
    return "large"
