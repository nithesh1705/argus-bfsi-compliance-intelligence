"""
ARGUS — Documentation Link Checker & Verification Utility (scripts/check_docs_links.py)

Validates markdown documentation across the repository:
1. Exactly one root README.md exists.
2. Relative links and image paths point to existing files with exact case sensitivity.
3. Anchor (#heading-slug) links resolve to valid headings in target markdown files.
4. No absolute filesystem paths, drive letters, file://, backslashes, or localhost links outside code blocks.
5. No project literals (project ID, project number, bucket names, service accounts) outside the single allowed live frontend URL in root README.md.
6. Flags orphan markdown files and images unreachable from root README.md.
"""

import os
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional


ALLOWED_LIVE_FRONTEND_URL = "https://argus-frontend-833068408683.asia-south1.run.app/"

# Known project literal patterns to flag in documentation (excluding code blocks and allowed URL)
FORBIDDEN_LITERAL_PATTERNS = [
    r"\bargus-438914\b",
    r"\bargus-compliance-prod\b",
    r"\b833068408683\b",
    r"\bargus-calls-incoming\b",
    r"\bargus-regulations\b",
    r"\bargus-backend-sa@[A-Za-z0-9._-]+\.iam\.gserviceaccount\.com\b",
    r"\bargus-eventarc-invoker-sa@[A-Za-z0-9._-]+\.iam\.gserviceaccount\.com\b",
    r"\beventarc-invoker@[A-Za-z0-9._-]+\.iam\.gserviceaccount\.com\b",
]


def github_slugify(heading_text: str) -> str:
    """Converts a markdown heading to GitHub anchor slug."""
    text = heading_text.strip().lower()
    # Strip HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove punctuation except hyphens and spaces
    text = re.sub(r"[^\w\s-]", "", text)
    # Replace whitespace with hyphens
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def extract_headings(content: str) -> Set[str]:
    """Extracts all heading anchor slugs from markdown content."""
    slugs = set()
    lines = content.splitlines()
    in_code_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if match:
            heading_text = match.group(2).strip()
            slug = github_slugify(heading_text)
            slugs.add(slug)
    return slugs


def check_case_exact_path(target_path: Path, root_dir: Path) -> bool:
    """Verifies that each component of target_path matches on-disk casing exactly."""
    try:
        resolved = target_path.resolve()
        if not resolved.exists():
            return False
        
        # Check components from root_dir down
        rel = target_path.relative_to(root_dir)
        curr = root_dir
        for part in rel.parts:
            # List actual entries in curr
            actual_entries = os.listdir(curr)
            if part not in actual_entries:
                return False
            curr = curr / part
        return True
    except Exception:
        return False


def run_checks(root_dir: Path) -> Tuple[int, List[str]]:
    """Runs all markdown checks and returns (error_count, report_lines)."""
    errors: List[str] = []
    warnings: List[str] = []
    
    # 1. Collect markdown files excluding node_modules, .git, .venv
    md_files: List[Path] = []
    for p in root_dir.rglob("*.md"):
        parts = p.parts
        if any(ignored in parts for ignored in ("node_modules", ".git", ".venv", "venv", ".gemini")):
            continue
        md_files.append(p)

    # Check exactly one README.md
    readme_files = [f for f in md_files if f.name.lower() == "readme.md"]
    root_readme = root_dir / "README.md"
    if not root_readme.exists():
        errors.append("CRITICAL: Root README.md does not exist.")
    if len(readme_files) != 1 or (len(readme_files) == 1 and readme_files[0] != root_readme):
        extra = [str(f.relative_to(root_dir)) for f in readme_files if f != root_readme]
        errors.append(f"CRITICAL: Exactly one README.md allowed. Found extras: {extra}")

    # Build graph of links for reachability
    all_headings: Dict[Path, Set[str]] = {}
    file_contents: Dict[Path, str] = {}
    for md_file in md_files:
        try:
            content = md_file.read_text(encoding="utf-8")
            file_contents[md_file] = content
            all_headings[md_file] = extract_headings(content)
        except Exception as exc:
            errors.append(f"Cannot read {md_file.relative_to(root_dir)}: {exc}")

    # Track referenced files
    referenced_files: Set[Path] = set()
    if root_readme.exists():
        referenced_files.add(root_readme)

    # Link regex: [text](link) and ![alt](image)
    link_pattern = re.compile(r"(!?\[.*?\]\((.*?)\))")

    for md_file in md_files:
        rel_md = md_file.relative_to(root_dir)
        content = file_contents.get(md_file, "")
        
        # Check literals in content (excluding code blocks and allowed URL)
        # Split into code blocks vs non-code blocks
        parts = content.split("```")
        for idx, part in enumerate(parts):
            if idx % 2 == 1:
                # Inside fenced code block
                continue
            
            # Check for drive letters, file://, backslashes in non-code text
            for line_no, line in enumerate(part.splitlines(), start=1):
                if re.search(r"[a-zA-Z]:\\", line):
                    errors.append(f"{rel_md}: Drive letter found outside code block: {line.strip()[:60]}")
                if "file://" in line:
                    errors.append(f"{rel_md}: 'file://' scheme found outside code block: {line.strip()[:60]}")
                if "http://localhost" in line or "https://localhost" in line:
                    errors.append(f"{rel_md}: 'localhost' found outside code block: {line.strip()[:60]}")
                
                # Check for backslashes in markdown links
                bs_match = re.search(r"\]\([^)]*\\[^)]*\)", line)
                if bs_match:
                    errors.append(f"{rel_md}: Backslash in link path: {bs_match.group(0)}")

                # Check forbidden project literals
                for pat in FORBIDDEN_LITERAL_PATTERNS:
                    found = re.findall(pat, line)
                    for match in found:
                        # Allow single exception in root README.md
                        if md_file == root_readme and match in ALLOWED_LIVE_FRONTEND_URL and ALLOWED_LIVE_FRONTEND_URL in line:
                            continue
                        errors.append(f"{rel_md}: Forbidden literal '{match}' found in line: {line.strip()[:70]}")

        # Check links
        for full_link, link_target in link_pattern.findall(content):
            raw_target = link_target.strip()
            # Ignore external web links, mailto, etc.
            if raw_target.startswith(("http://", "https://", "mailto:", "ftp://")):
                continue
            
            # Ignore pure anchor link in same file
            if raw_target.startswith("#"):
                anchor = raw_target[1:]
                headings = all_headings.get(md_file, set())
                if anchor not in headings:
                    errors.append(f"{rel_md}: Broken anchor #{anchor} within same file")
                continue

            # Split path and anchor
            if "#" in raw_target:
                path_part, anchor_part = raw_target.split("#", 1)
            else:
                path_part, anchor_part = raw_target, None

            path_part = path_part.strip()
            if not path_part:
                continue

            # Path is relative to the directory containing md_file
            target_path = (md_file.parent / path_part).resolve()
            
            if not target_path.exists():
                errors.append(f"{rel_md}: Target not found for link '{path_part}' (resolved to {target_path})")
                continue

            # Case sensitivity check
            try:
                if not check_case_exact_path(target_path, root_dir):
                    errors.append(f"{rel_md}: Case mismatch for link '{path_part}'")
            except Exception:
                pass

            referenced_files.add(target_path)

            # If anchor is present and target is a markdown file, verify anchor
            if anchor_part and target_path in all_headings:
                target_headings = all_headings[target_path]
                if anchor_part not in target_headings:
                    errors.append(f"{rel_md}: Target file {target_path.name} missing anchor #{anchor_part}")

    # Check for orphan markdown files and images
    # Crawl reachability starting from root_readme
    reachable: Set[Path] = set()
    queue = [root_readme] if root_readme.exists() else []
    while queue:
        curr = queue.pop(0)
        if curr in reachable:
            continue
        reachable.add(curr)
        
        # If it's a markdown file, parse its links
        if curr in file_contents:
            for _, link_target in link_pattern.findall(file_contents[curr]):
                raw_target = link_target.strip()
                if raw_target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part = raw_target.split("#")[0].strip()
                if not path_part:
                    continue
                target = (curr.parent / path_part).resolve()
                if target.exists() and target not in reachable:
                    queue.append(target)

    # Check orphan markdown files
    for md_file in md_files:
        if md_file not in reachable:
            warnings.append(f"Orphan markdown file not reachable from root README.md: {md_file.relative_to(root_dir)}")

    # Check orphan images in docs/glimpse
    glimpse_dir = root_dir / "docs" / "glimpse"
    if glimpse_dir.exists():
        for img in glimpse_dir.rglob("*"):
            if img.is_file() and img.suffix.lower() in (".png", ".jpeg", ".jpg", ".webp"):
                resolved_img = img.resolve()
                if resolved_img not in reachable:
                    warnings.append(f"Orphan image not referenced in docs: {img.relative_to(root_dir)}")

    report = []
    report.append(f"Checked {len(md_files)} markdown files.")
    report.append(f"Errors found: {len(errors)}")
    report.append(f"Warnings / Orphans: {len(warnings)}")
    for err in errors:
        report.append(f"  [ERROR] {err}")
    for warn in warnings:
        report.append(f"  [WARN]  {warn}")

    return len(errors), report


def main():
    parser = argparse.ArgumentParser(description="ARGUS Documentation Link and Case Checker")
    parser.add_argument("--root", type=str, default=".", help="Root repository path (default: current directory)")
    args = parser.parse_args()

    root_dir = Path(args.root).resolve()
    err_count, report = run_checks(root_dir)
    print("\n".join(report))
    sys.exit(0 if err_count == 0 else 1)


if __name__ == "__main__":
    main()
