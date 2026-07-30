# Manual Git and GitHub UI guide

No Codex process needs GitHub credentials. Use the Git UI or the commands below.

## First push

Create one empty private GitHub repository named `HAXS` in the browser. Do not
add a README, licence, or `.gitignore` in GitHub.

Then run:

```bash
cd "/Users/subhojithalder/Desktop/Research Papers/Hole Aware XXZ Screening/HAXS"

git remote add origin "https://github.com/Subhojith90/HAXS.git"
git push -u origin main
git push -u origin release/stage5c2g-r32a
```

The same operations in a Git UI are:

1. Open the local `HAXS` folder as an existing repository.
2. Add remote `origin` with URL `https://github.com/Subhojith90/HAXS.git`.
3. Push `main`.
4. Push `release/stage5c2g-r32a`.

## Run the current workflow

In GitHub:

1. Open the single `HAXS` repository.
2. Select **Actions**.
3. Select **HAXS Stage5C2G-R3.2A Host-B G0**.
4. Select **Run workflow**.
5. Choose branch `release/stage5c2g-r32a`.
6. Run it exactly once.

Do not rerun a failed attempt. Download its diagnostic artifact and preserve it.

## Future stages

```bash
git switch main
git switch -c work/<new-stage>
```

Develop and test on the work branch. After approval:

```bash
git switch -c release/<new-stage>
git push -u origin release/<new-stage>
```

Add the next workflow under `.github/workflows/` in this same repository.
