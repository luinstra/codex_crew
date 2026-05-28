#!/usr/bin/env bash
#
# Post-commit hook: auto-bump the Codex Crew plugin version.
#
# Install:
#   ln -sf ../../scripts/post-commit-version-bump.sh .git/hooks/post-commit
#
# This runs after each commit and:
# - Skips version-bump commits to avoid recursion.
# - Skips commits marked [skip version] or [no bump].
# - Determines the bump type from conventional commit subjects since the last bump.
# - Bumps plugins/codex-crew/.codex-plugin/plugin.json when plugin files changed.

set -e

PLUGIN_DIR="plugins/codex-crew"
PLUGIN_JSON="$PLUGIN_DIR/.codex-plugin/plugin.json"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[version-bump]${NC} $1"; }
success() { echo -e "${GREEN}[version-bump]${NC} $1"; }
warn() { echo -e "${YELLOW}[version-bump]${NC} $1"; }
error() { echo -e "${RED}[version-bump]${NC} $1"; }

cd "$(git rev-parse --show-toplevel)"

if [ ! -f "$PLUGIN_JSON" ]; then
    warn "Skipping version bump; missing $PLUGIN_JSON"
    exit 0
fi

LAST_MSG=$(git log -1 --format="%s")
if [[ "$LAST_MSG" == "chore: bump version"* ]]; then
    exit 0
fi

if [[ "$LAST_MSG" == *"[skip version]"* ]] || [[ "$LAST_MSG" == *"[no bump]"* ]]; then
    info "Skipping version bump ([skip version] or [no bump] in commit message)"
    exit 0
fi

get_last_bump_commit() {
    local commit
    commit=$(git log --grep="chore: bump version" -1 --format="%H" 2>/dev/null || echo "")
    if [ -z "$commit" ]; then
        commit=$(git rev-list --max-parents=0 HEAD 2>/dev/null || echo "HEAD~20")
    fi
    echo "$commit"
}

get_bump_type() {
    local last_bump="$1"
    local commits
    commits=$(git log "$last_bump"..HEAD --format="%s" 2>/dev/null || git log -20 --format="%s")

    if echo "$commits" | grep -qE '^[a-z]+(\([^)]+\))?!:|BREAKING CHANGE'; then
        echo "major"
    elif echo "$commits" | grep -qE '^feat(\([^)]+\))?:'; then
        echo "minor"
    else
        echo "patch"
    fi
}

bump_version() {
    local current="$1"
    local bump_type="$2"
    local major minor patch

    major=$(echo "$current" | cut -d. -f1)
    minor=$(echo "$current" | cut -d. -f2)
    patch=$(echo "$current" | cut -d. -f3)

    case "$bump_type" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
        *)
            error "Unknown bump type: $bump_type"
            exit 1
            ;;
    esac

    echo "$major.$minor.$patch"
}

current_version() {
    grep -o '"version": *"[^"]*"' "$PLUGIN_JSON" | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+'
}

has_substantive_changes() {
    local file="$1"
    local last_bump="$2"
    local diff

    diff=$(
        git diff "$last_bump"..HEAD -- "$file" 2>/dev/null |
            grep '^[+-]' |
            grep -v '^[+-]\{3\}' |
            grep -v '"version"' || true
    )

    [ -n "$diff" ]
}

has_plugin_changes() {
    local last_bump="$1"
    local changes

    changes=$(git diff --name-only "$last_bump"..HEAD -- "$PLUGIN_DIR" 2>/dev/null || echo "")
    if [ -z "$changes" ]; then
        return 1
    fi

    if echo "$changes" | grep -qx "$PLUGIN_JSON"; then
        if ! has_substantive_changes "$PLUGIN_JSON" "$last_bump"; then
            changes=$(echo "$changes" | grep -vx "$PLUGIN_JSON" || true)
        fi
    fi

    [ -n "$changes" ]
}

main() {
    info "Checking for Codex Crew version bumps..."

    local last_bump bump_type current new
    last_bump=$(get_last_bump_commit)
    info "Last version bump: ${last_bump:0:7}"

    if ! has_plugin_changes "$last_bump"; then
        info "No codex-crew plugin changes"
        exit 0
    fi

    bump_type=$(get_bump_type "$last_bump")
    info "Bump type from commits: $bump_type"

    current=$(current_version)
    new=$(bump_version "$current" "$bump_type")

    if [ "$current" = "$new" ]; then
        info "No version change needed"
        exit 0
    fi

    sed -i.bak "s/\"version\": *\"$current\"/\"version\": \"$new\"/" "$PLUGIN_JSON"
    rm -f "$PLUGIN_JSON.bak"
    success "codex-crew: $current -> $new"

    git add "$PLUGIN_JSON"
    if ! git diff --cached --quiet -- "$PLUGIN_JSON"; then
        git commit --no-verify -m "chore: bump version (codex-crew $current -> $new)"
        success "Version bump committed. Ready to push."
    fi
}

main "$@"
