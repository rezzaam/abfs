# abfs-client build

Builds the `abfs-client` Debian package from public sources, with Cloud Build:

1. `google/abfs` at a pinned upstream commit (`c975ebd`)
2. the open upstream pull requests #3 to #20, each pinned to its reviewed head commit. The build fails if a head has moved.
3. `post-merge-fixups.patch`: resolutions where those pull requests overlap. They were found by running the pull requests' own tests on the merged tree.
4. fixes that are not upstream yet, cherry-picked from this fork (`EXTRA_COMMITS` in `build.sh`):
   - `d3d1999` abfs mount skips an optional remove-project that matches no project
5. `go vet ./...` and the unit tests of the changed packages, then `make install-client`, packaged as `abfs-client_<version>_amd64.deb`

The package installs the client binaries into `/usr/local/bin`:
- `abfs`, `cacheman`, `ninjago`, `casfs-mounter`, `casfuse-mounter`
- helpers, including the `*-no-cgo` ones copied by `abfs setup`

It does not contain the casfs kernel module.

## Run

```bash
git clone -b abfs-client-build https://github.com/rezzaam/abfs.git abfs-client-build
cd abfs-client-build
gcloud builds submit --project <project> --region <region> --config cloudbuild.yaml \
  --substitutions=_REPOSITORY=<apt-repo>,_ARTIFACT_BUCKET=<bucket> .
```

| Substitution | Default | Meaning |
|---|---|---|
| `_VERSION` | `0.1.23-lars.c975ebd.v3` | Package version. Do not use `+`: the version ends up in image tags. |
| `_REPOSITORY` | `abfs-apt` | Artifact Registry APT repository to upload to. Use a separate repository for trials: an image that runs `apt install abfs-client` without a version takes the highest version in it. |
| `_LOCATION` | `europe-west4` | Location of the repository |
| `_UPLOAD` | `true` | `false` builds without uploading |
| `_ARTIFACT_BUCKET` | `abfs-argolis-rezzaam-casfs-cache` | The `.deb` and `BUILD_INFO.json` are copied to `gs://<bucket>/abfs-client/<version>/` |

**Permissions:** the Cloud Build service account needs `roles/artifactregistry.writer` on the repository and write access to the bucket.

`BUILD_INFO.json` records the base commit, the pull request heads, the extra commits, the source tree hash, the Go version and the package checksum.

## Updating

- **To move to newer upstream code:** change `BASE_COMMIT`, `PR_SHA` and `EXTRA_COMMITS` in `build.sh`, re-run the build and check that the tests still pass. Drop entries that have been merged upstream.
- **When the pull requests are merged and released:** build from the release tag instead.

`resolve_conflicts.py` comes from the first integration build of these pull requests, by Mouad Bichouarine.
