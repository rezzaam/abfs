#!/usr/bin/env bash
# Builds the abfs-client .deb from public sources:
#   google/abfs @ BASE_COMMIT
#   + open upstream pull requests #3-#20, pinned to their reviewed head commits
#   + post-merge-fixups.patch (resolutions for the overlapping pull requests)
#   + EXTRA_COMMITS from FORK (fixes not upstream yet)
# then runs go vet and the unit tests, and packages the client into OUT_DIR.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION="${VERSION:?set VERSION, e.g. 0.1.23-lars.c975ebd.v3 (no '+': it ends up in image tags)}"
OUT_DIR="${OUT_DIR:-${HERE}/out}"
UPSTREAM="https://github.com/google/abfs.git"
FORK="${FORK:-https://github.com/rezzaam/abfs.git}"
BASE_COMMIT="c975ebdf233c427f9ce058202e269c04189a964c"

# Upstream pull requests, pinned; the build fails if a head moved.
PRS=(3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20)
declare -A PR_SHA=(
  [3]=f41177603d04d7c4763cae8343144e1c62512139
  [4]=66dba5fb46de527354f30ec9a61cd7601ef9db50
  [5]=49c8093e98969506dde17c9343bc1876aad1f82d
  [6]=80d8b6f431d630b347ecabc9df8adac04ad1f226
  [7]=c11472a2033e42eaae6fe3ebfa5381e3388ff00a
  [8]=c1121ede6c60b51ca21f69d1a18d1d00b66adeb3
  [9]=bb51c0f1f1ecdb7718fa731b7016e7404a8d5698
  [10]=25375a3ee218c2691aa6e4467a53284ef62bb84e
  [11]=f06477a1e00af81ef86122b0fe46a429cde9c21f
  [12]=06d56a1eec8994fbad99ff76d349fe9592d7ca56
  [13]=35947726122e7375c83ebd9ad46e67c46e3ad01a
  [14]=02ca921353a0411ca86d802996a7b707c3347b28
  [15]=a01f905b04b402cae79c1da6d64378546bbac017
  [16]=ecef1e69b089a11a8b0d905b2e1cbc1f3c632e7b
  [17]=12d75caaa507ca951b687a0cc2cb0635408a9198
  [18]=3c94013f6e6bc167598b211f2c82b8e863e28d00
  [19]=0bd65fce8788b640cfcee46769cf2ed5c69feda4
  [20]=a6f317280371f9ac2bd9f9258c1969b17b07935c
)

# Fixes from FORK that are not upstream yet, applied in order.
#   d3d1999  abfs mount skips an optional remove-project that matches no project
EXTRA_COMMITS=(d3d199971dd7cdfc4dd20bc33549c91cea804392)

if [[ ! "${VERSION}" =~ ^[0-9][0-9A-Za-z.~-]*$ ]]; then
    echo "ERROR: VERSION='${VERSION}' must start with a digit and use only [0-9A-Za-z.~-]." >&2
    exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT
src="${work}/abfs"
git init -q "${src}"
cd "${src}"
git config user.name "ABFS Builder"
git config user.email "abfs-builder@example.com"
git remote add origin "${UPSTREAM}"
git remote add fork "${FORK}"

echo "== base ${BASE_COMMIT}"
git fetch -q origin main
git checkout -q -b integrated "${BASE_COMMIT}"

echo "== fetching pull requests"
for pr in "${PRS[@]}"; do
    git fetch -q origin "pull/${pr}/head:pr-${pr}"
    got="$(git rev-parse "pr-${pr}")"
    [[ "${got}" == "${PR_SHA[$pr]}" ]] || { echo "ERROR: PR #${pr} head moved: ${got} != ${PR_SHA[$pr]}" >&2; exit 1; }
done

echo "== merging pull requests"
merge() { git merge -q --no-edit "pr-$1" >/dev/null; echo "   #$1"; }
for pr in 3 4 5 6 7 8 9 10 11; do merge "${pr}"; done
# #12 and #10 both change shared/cmd/cliexec.go; #12 is taken here and #10's part is
# restored by post-merge-fixups.patch.
git merge -q --no-commit pr-12 >/dev/null 2>&1 || true
git checkout pr-12 -- shared/cmd/cliexec.go
git commit -q -m "Merge PR 12"; echo "   #12"
git merge -q --no-commit pr-13 >/dev/null 2>&1 || true
git checkout pr-13 -- ninjago/abfs.go
python3 "${HERE}/resolve_conflicts.py" pr13
git add ninjago/abfs.go && git commit -q -m "Merge PR 13"; echo "   #13"
git merge -q --no-commit pr-14 >/dev/null 2>&1 || true
python3 "${HERE}/resolve_conflicts.py" pr14
git add ninjago/abfs.go && git commit -q -m "Merge PR 14"; echo "   #14"
for pr in 15 16; do merge "${pr}"; done
git merge -q --no-commit pr-17 >/dev/null 2>&1 || true
python3 "${HERE}/resolve_conflicts.py" pr17
git add abfs_test.go gitpusher/repowatcher_test.go repo/repo_test.go abfsrepo/project.go
git commit -q -m "Merge PR 17"; echo "   #17"
for pr in 18 19 20; do merge "${pr}"; done

echo "== post-merge fixups"
git apply "${HERE}/post-merge-fixups.patch"
if git grep -nE '^(<<<<<<<|=======|>>>>>>>)( |$)' -- '*.go'; then
    echo "ERROR: conflict markers left" >&2
    exit 1
fi
git commit -q -am "Post-merge fixups"

echo "== extra commits from ${FORK}"
for c in "${EXTRA_COMMITS[@]}"; do
    git fetch -q fork "${c}"
    git cherry-pick -x "${c}" >/dev/null
    echo "   $(git log -1 --format='%h %s')"
done

# DigestMap objects (added in 0.1.20) are unknown to a 0.1.14 abfs-server; only upload them
# when ABFS_ENABLE_DIGEST_MAP=true, so the git-pusher in this package works with such a server.
sed -i 's/if err := s.saveDigestMap(ctx, refs, treeHashes); err != nil {/if os.Getenv("ABFS_ENABLE_DIGEST_MAP") == "true" { if err := s.saveDigestMap(ctx, refs, treeHashes); err != nil { return err } }\n\tif false {/' gitpusher/pusher.go
grep -q 'ABFS_ENABLE_DIGEST_MAP' gitpusher/pusher.go || { echo "ERROR: saveDigestMap guard not applied" >&2; exit 1; }

echo "== go vet + unit tests"
go vet ./...
ABFS_ENABLE_DIGEST_MAP=true go test -count=1 ./manifest/... ./ninjago/... ./abfsrepo/... ./repo/... \
    ./shared/... ./gitpusher/... ./cmd/... ./daemon/... ./casgit/... ./binding/... ./store/... .

echo "== package ${VERSION}"
pkg="${work}/pkg/abfs-client_${VERSION}_amd64"
mkdir -p "${pkg}/usr/local/bin" "${pkg}/usr/share/doc/abfs-client" "${pkg}/DEBIAN"
make -C "${src}" VERSION="${VERSION}" DESTDIR="${pkg}/usr/local/bin" \
    DOCDIR="${pkg}/usr/share/doc/abfs-client" SKIP_SETCAP=1 install-client
cat > "${pkg}/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
if [[ "$1" == "configure" ]] && command -v setcap >/dev/null 2>&1; then
    setcap CAP_SYS_ADMIN,CAP_SYS_MODULE+ep /usr/local/bin/casfs-mounter || true
    setcap CAP_SYS_RESOURCE+ep /usr/local/bin/casfuse-mounter || true
fi
EOF
chmod 0755 "${pkg}/DEBIAN/postinst"
cat > "${pkg}/DEBIAN/control" <<EOF
Package: abfs-client
Version: ${VERSION}
Architecture: amd64
Depends: psmisc, procps
Maintainer: Google Cloud PSO (test build)
Description: ABFS client (google/abfs ${BASE_COMMIT:0:7} + pull requests #3-#20 + fixes)
EOF
mkdir -p "${OUT_DIR}"
deb="${OUT_DIR}/abfs-client_${VERSION}_amd64.deb"
dpkg-deb --build --root-owner-group "${pkg}" "${deb}"

{
    echo "{"
    echo "  \"version\": \"${VERSION}\","
    echo "  \"upstream\": \"${UPSTREAM}\","
    echo "  \"base_commit\": \"${BASE_COMMIT}\","
    echo "  \"pull_requests\": {$(for pr in "${PRS[@]}"; do printf '"%s": "%s"' "${pr}" "${PR_SHA[$pr]}"; [[ "${pr}" != "${PRS[-1]}" ]] && printf ', '; done)},"
    echo "  \"fork\": \"${FORK}\","
    echo "  \"extra_commits\": [$(printf '"%s"' "${EXTRA_COMMITS[@]}" | sed 's/""/", "/g')],"
    echo "  \"post_merge_fixups_sha256\": \"$(sha256sum "${HERE}/post-merge-fixups.patch" | cut -d' ' -f1)\","
    echo "  \"source_tree\": \"$(git rev-parse HEAD^{tree})\","
    echo "  \"go\": \"$(go env GOVERSION)\","
    echo "  \"deb_sha256\": \"$(sha256sum "${deb}" | cut -d' ' -f1)\""
    echo "}"
} > "${OUT_DIR}/BUILD_INFO.json"
cat "${OUT_DIR}/BUILD_INFO.json"
echo "== built ${deb}"
