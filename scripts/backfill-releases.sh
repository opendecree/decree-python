#!/usr/bin/env bash
set -euo pipefail

PYPI_PACKAGE="decree"
VERSIONS=("0.1.0" "0.2.0")

for version in "${VERSIONS[@]}"; do
  tag="v${version}"
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT

  echo "Fetching PyPI metadata for ${PYPI_PACKAGE} ${version}..."
  metadata=$(curl -fsSL "https://pypi.org/pypi/${PYPI_PACKAGE}/${version}/json")

  mapfile -t urls < <(echo "$metadata" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for f in data['urls']:
    if f['packagetype'] in ('bdist_wheel', 'sdist'):
        print(f['url'])
")

  for url in "${urls[@]}"; do
    filename=$(basename "$url")
    echo "Downloading ${filename}..."
    curl -fsSL -o "${tmpdir}/${filename}" "$url"
  done

  echo "Creating GitHub release for ${tag}..."
  gh release create "$tag" \
    --repo opendecree/decree-python \
    --generate-notes \
    "${tmpdir}"/*.whl \
    "${tmpdir}"/*.tar.gz

  trap - EXIT
  rm -rf "$tmpdir"
done
