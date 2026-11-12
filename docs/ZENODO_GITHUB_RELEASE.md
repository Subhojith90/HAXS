# Zenodo/GitHub release procedure

This repository is archived through Zenodo's GitHub integration. Zenodo reads
`.zenodo.json` as its primary metadata source. `CITATION.cff` is retained for
GitHub's citation panel and other citation tooling.

## One-time account setup

1. Sign in to Zenodo using the GitHub-linked account.
2. Open the Zenodo profile menu and choose **GitHub**.
3. Click **Sync now**.
4. Find `Subhojith90/HAXS` and enable its repository toggle.

## Release v1.0.0

Run the local preflight before committing:

```bash
python3 scripts/validate_zenodo_github_release.py
python3 scripts/verify_publication_closure_release.py
```

After the prepared changes are committed and pushed to `main`, create and push
the immutable tag:

```bash
git tag -a v1.0.0 -m "HAXS code-and-data reproducibility release v1.0.0"
git push origin v1.0.0
```

On GitHub, create a release from `v1.0.0` with title:

```text
HAXS code-and-data reproducibility release v1.0.0
```

Use `docs/releases/v1.0.0.md` as the release notes and publish the release.
Zenodo will ingest the tagged GitHub snapshot and mint both a version DOI and a
concept DOI. Use the version DOI in the manuscript.

Do not move or recreate tag `v1.0.0` after publication. Corrections require a
new version and tag.
