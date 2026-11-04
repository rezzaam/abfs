#!/usr/bin/env python3
"""
Conflict resolution script for ABFS PR integration.
Resolves overlapping lines in ninjago/abfs.go, abfs_test.go,
gitpusher/repowatcher_test.go, repo/repo_test.go, and abfsrepo/project.go.
"""

import sys

def resolve_pr13():
    path = "ninjago/abfs.go"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Ensure isPhonyNode is present
    phony_code = """
// isPhonyNode reports whether the outputs of n are not files: a phony build, or a build with
// phony_output set on it or on its rule. Kati writes a .PHONY target with a recipe that way.
func isPhonyNode(n *graph.Node) bool {
	return n.Build.Rule.IsPhony() || n.Build.Scope.ExpandField("phony_output") != ""
}
"""
    if "func isPhonyNode(" not in content:
        content += "\n" + phony_code

    # Ensure applyIfCached includes IsPhonyOutput check
    if "if c.config.EvalNoCache || eval.step.IsPhonyOutput() {" not in content:
        content = content.replace(
            "if c.config.EvalNoCache {",
            "// A phony_output step runs on every build, so it is never looked up or recorded.\n\tif c.config.EvalNoCache || eval.step.IsPhonyOutput() {"
        )

    # Ensure execTapLocal checks !eval.step.IsPhonyOutput()
    content = content.replace(
        "if err := c.recordResults(ctx, eval, resp, tapResult.ExitCode == 0); err != nil {",
        "if err := c.recordResults(ctx, eval, resp, tapResult.ExitCode == 0 && !eval.step.IsPhonyOutput()); err != nil {"
    )

    # Ensure addInput uses isPhonyNode
    content = content.replace(
        "if n := c.graph.Targets.Get(fname); n != nil && n.Build.Rule.IsPhony() {",
        "if n := c.graph.Targets.Get(fname); n != nil && isPhonyNode(n) {"
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Resolved PR 13 conflict in ninjago/abfs.go (preserved phony_output support)")


def resolve_pr14():
    path = "ninjago/abfs.go"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_block = (
        "<<<<<<< HEAD\n"
        "\tcacheErrors     atomic.Int64\n"
        "=======\n"
        "\tmetadata        *binding.BuildMetadata\n"
        ">>>>>>> pr-14"
    )
    new_block = (
        "\tcacheErrors     atomic.Int64\n"
        "\tmetadata        *binding.BuildMetadata"
    )

    if old_block in content:
        content = content.replace(old_block, new_block)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Resolved PR 14 conflict in ninjago/abfs.go")
    else:
        print("Warning: PR 14 block not found in ninjago/abfs.go")


def resolve_pr17():
    # 1. abfs_test.go
    with open("abfs_test.go", "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("<<<<<<< HEAD\n", "").replace("=======\n", "").replace(">>>>>>> pr-17\n", "")
    with open("abfs_test.go", "w", encoding="utf-8") as f:
        f.write(c)
    print("Resolved abfs_test.go")

    # 2. gitpusher/repowatcher_test.go
    with open("gitpusher/repowatcher_test.go", "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace("<<<<<<< HEAD\n", "").replace("=======\n", "").replace(">>>>>>> pr-17\n", "")
    with open("gitpusher/repowatcher_test.go", "w", encoding="utf-8") as f:
        f.write(c)
    print("Resolved repowatcher_test.go")

    # 3. repo/repo_test.go
    with open("repo/repo_test.go", "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace(
        '<<<<<<< HEAD\n\t"crypto/sha1"\n=======\n\t"errors"\n>>>>>>> pr-17',
        '\t"crypto/sha1"\n\t"errors"'
    )
    c = c.replace(
        '<<<<<<< HEAD\n\t"github.com/google/abfs/shared/remote"\n\t"github.com/google/abfs/shared/remote/grpc/client"\n\t"github.com/google/abfs/shared/remote/grpc/server"\n\t"github.com/google/abfs/shared/remote/servers/filebased"\n=======\n>>>>>>> pr-17',
        '\t"github.com/google/abfs/shared/remote"\n\t"github.com/google/abfs/shared/remote/grpc/client"\n\t"github.com/google/abfs/shared/remote/grpc/server"\n\t"github.com/google/abfs/shared/remote/servers/filebased"'
    )
    c = c.replace("<<<<<<< HEAD\n", "").replace("=======\n", "").replace(">>>>>>> pr-17\n", "")
    with open("repo/repo_test.go", "w", encoding="utf-8") as f:
        f.write(c)
    print("Resolved repo_test.go")

    # 4. abfsrepo/project.go
    with open("abfsrepo/project.go", "r", encoding="utf-8") as f:
        c = f.read()
    c = c.replace(
        '<<<<<<< HEAD\n\terr := r.updateGitRepo(ctx, gitRepo, "manifests", r.manifestsDir, gitDir, objDir, "origin", target, SyncOpts{})\n=======\n\terr := r.updateGitRepo(ctx, gitRepo, "manifests", r.manifestsDir, gitDir, objDir, "origin", r.manifestBranch, "", "", SyncOpts{})\n>>>>>>> pr-17',
        '\terr := r.updateGitRepo(ctx, gitRepo, "manifests", r.manifestsDir, gitDir, objDir, "origin", target, "", "", SyncOpts{})'
    )

    old_update = (
        "<<<<<<< HEAD\n"
        "// manifestTarget returns what the manifest project is checked out at by casgit and by git.\n"
        "// abfs repo init stores every -b value under refs/heads/, so the name is resolved again\n"
        "// as the first clone resolves it, and a tag is checked out at its hash.\n"
        "func (r *Repo) manifestTarget(ctx context.Context, name string) (target, gitTarget string) {\n"
        "\t// A full ref, stored as typed by git-repo's repo init or after the git fallback clone,\n"
        "\t// is checked out by git as given.\n"
        "\tif entities.IsHash(name) || strings.HasPrefix(name, \"refs/\") {\n"
        "\t\treturn name, name\n"
        "\t}\n"
        "\tif u, err := url.Parse(r.manifestURL); err == nil {\n"
        "\t\thash, ref, err := r.Git.ResolveRef(ctx, u.Host, strings.Trim(u.Path, \"/\"), name)\n"
        "\t\tif err != nil {\n"
        "\t\t\t// The fetch reports an unreachable server; a git fallback may still work.\n"
        "\t\t\tlog.Printf(\"Warning: cannot resolve manifest revision %s, treating it as a branch: %v\", name, err)\n"
        "\t\t} else if strings.HasPrefix(ref, \"refs/tags/\") {\n"
        "\t\t\treturn hash.String(), hash.String()\n"
        "\t\t}\n"
        "\t}\n"
        "\t// A git clone of the manifest has no local branch, and the fetch does not move one, so\n"
        "\t// git checks out the remote branch.\n"
        "\treturn name, \"refs/remotes/origin/\" + name\n"
        "}\n\n"
        "func (r *Repo) updateProject(ctx context.Context, project *manifest.Project, workDir, gitDir, objDir, remoteName, revision string, opts SyncOpts) error {\n"
        "=======\n"
        "func (r *Repo) updateProject(ctx context.Context, project *manifest.Project, workDir, gitDir, objDir, remoteName, revision, refServer string, opts SyncOpts) error {\n"
        ">>>>>>> pr-17"
    )

    new_update = (
        "// manifestTarget returns what the manifest project is checked out at by casgit and by git.\n"
        "// abfs repo init stores every -b value under refs/heads/, so the name is resolved again\n"
        "// as the first clone resolves it, and a tag is checked out at its hash.\n"
        "func (r *Repo) manifestTarget(ctx context.Context, name string) (target, gitTarget string) {\n"
        "\t// A full ref, stored as typed by git-repo's repo init or after the git fallback clone,\n"
        "\t// is checked out by git as given.\n"
        "\tif entities.IsHash(name) || strings.HasPrefix(name, \"refs/\") {\n"
        "\t\treturn name, name\n"
        "\t}\n"
        "\tif u, err := url.Parse(r.manifestURL); err == nil {\n"
        "\t\thash, ref, err := r.Git.ResolveRef(ctx, u.Host, strings.Trim(u.Path, \"/\"), name)\n"
        "\t\tif err != nil {\n"
        "\t\t\t// The fetch reports an unreachable server; a git fallback may still work.\n"
        "\t\t\tlog.Printf(\"Warning: cannot resolve manifest revision %s, treating it as a branch: %v\", name, err)\n"
        "\t\t} else if strings.HasPrefix(ref, \"refs/tags/\") {\n"
        "\t\t\treturn hash.String(), hash.String()\n"
        "\t\t}\n"
        "\t}\n"
        "\t// A git clone of the manifest has no local branch, and the fetch does not move one, so\n"
        "\t// git checks out the remote branch.\n"
        "\treturn name, \"refs/remotes/origin/\" + name\n"
        "}\n\n"
        "func (r *Repo) updateProject(ctx context.Context, project *manifest.Project, workDir, gitDir, objDir, remoteName, revision, refServer string, opts SyncOpts) error {"
    )

    if old_update in c:
        c = c.replace(old_update, new_update)
        with open("abfsrepo/project.go", "w", encoding="utf-8") as f:
            f.write(c)
        print("Resolved abfsrepo/project.go")
    else:
        print("Warning: updateProject block not found in project.go")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "pr13":
        resolve_pr13()
    elif len(sys.argv) > 1 and sys.argv[1] == "pr14":
        resolve_pr14()
    elif len(sys.argv) > 1 and sys.argv[1] == "pr17":
        resolve_pr17()
    else:
        print("Usage: resolve_conflicts.py [pr13|pr14|pr17]")
        sys.exit(1)
