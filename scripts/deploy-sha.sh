#!/usr/bin/env bash
# Deploy a commit through GitOps: point values-gitops.yaml at the images CI
# published for that commit, then commit and push. Argo CD does the rest.
#
#   scripts/deploy-sha.sh            # deploy the current HEAD
#   scripts/deploy-sha.sh <full-sha> # deploy a specific commit
#
# Nothing here touches the cluster. The only thing that changes is a file in
# Git, which is the point.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
sha="${1:-$(git rev-parse HEAD)}"
file=helm/mltracker/values-gitops.yaml
registry=ghcr.io/anisha-singhal/ml-experiment-tracker

if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "expected a full 40-character commit SHA, got: $sha" >&2
  exit 1
fi

# Refuse to deploy a tag CI never published, or Argo CD will roll out pods
# that sit in ImagePullBackOff.
for image in backend frontend; do
  if ! docker manifest inspect "$registry-$image:$sha" >/dev/null 2>&1; then
    echo "$registry-$image:$sha is not in GHCR yet - wait for the pipeline to go green." >&2
    exit 1
  fi
done

current=$(grep -m1 -oE '[0-9a-f]{40}' "$file")
if [[ "$current" == "$sha" ]]; then
  echo "already deployed: ${sha:0:7}"
  exit 0
fi

perl -pi -e "s/$current/$sha/g" "$file"
git add "$file"
git commit -q -m "Deploy ${sha:0:7} through Argo CD"
git push -q origin HEAD
echo "values-gitops.yaml: ${current:0:7} -> ${sha:0:7}, pushed. Argo CD will sync within a few minutes."
