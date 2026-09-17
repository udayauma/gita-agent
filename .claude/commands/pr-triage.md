---
description: Poll the current branch's PR for a Greptile review, then triage its findings for human decision
argument-hint: "[PR number — optional, defaults to the PR for the current branch]"
allowed-tools: Bash(gh pr view:*), Bash(gh pr status:*), Bash(gh pr checks:*), Bash(gh api:*), Bash(git branch:*), Bash(git log:*), Bash(git diff:*), Read, Grep, Glob
---

# Greptile PR triage

Poll for a Greptile review on a pull request and triage what it found. **This command
never modifies code, never pushes, and never posts comments.** It reports and stops.

## Target PR

$ARGUMENTS

If no PR number was given, resolve it from the current branch:

```
gh pr view --json number,title,url,state,headRefName,isDraft
```

If there is no open PR for this branch, say so plainly and stop — do not create one.

## Step 1 — has the review landed?

Greptile posts as `greptileai` and typically takes ~3 minutes. Check both signals:

```
gh pr checks --json name,state,link
gh pr view --json comments --jq '.comments[] | select(.author.login | test("greptile"; "i")) | {createdAt, body}'
```

Read the state:

- **No Greptile comment and no Greptile check** → not started. Report "not started" with
  how long the PR has been open, and stop. Do not escalate this to the user as a
  problem before ~5 minutes have passed.
- **Comment present with 👀** → still analyzing. Report "in progress" and stop.
- **Comment present with 😕** → the review failed. Report that, and tell the user they
  can retry by commenting `@greptileai` on the PR themselves.
- **Comment present with 👍, or a completed status check** → review landed. Continue to
  step 2.

When the review has not landed, keep the output to a single line. These polls repeat;
they should be quiet until there is something to say.

## Step 2 — pull the findings

```
gh pr view --json reviews,comments
gh api "repos/{owner}/{repo}/pulls/{number}/comments" --jq '.[] | select(.user.login | test("greptile"; "i")) | {path, line, body}'
```

Collect:

- The PR-level **confidence score** (`X/5`) from the summary comment.
- Every inline comment, with its file, line, and **severity badge (P0 / P1 / P2)**.

## Step 3 — verify before reporting

Do not relay findings unread. For each **P0 and P1**, open the cited file and lines and
judge it yourself:

- Does the code actually do what the finding claims?
- Is it real, or does a project convention explain it? Check `.greptile/rules.md` and
  the design docs in `docs/` — Greptile may not have weighted them correctly.
- Would the described failure actually occur, with concrete inputs?

Mark each as **confirmed**, **disputed** (say why), or **needs-a-human-call**.

Do not verify P2s individually — list them, grouped, one line each.

## Step 4 — report and stop

Output, in this shape:

```
PR #<n> — <title>
Greptile score: <X>/5
P0: <n>   P1: <n>   P2: <n>

CONFIRMED
  <file:line> [P0] <one-line defect> → <one-line fix>

DISPUTED
  <file:line> [P1] <finding> — <why it is wrong here>

NOTED (P2)
  <file:line> <finding>

Recommend: <fix these | merge as-is | needs your call on X>
```

Then **stop and wait**. Do not fix anything. Do not push. Do not comment on the PR. Do
not merge. The user decides what happens next; ask which findings they want addressed.

If this command is running inside `/loop`, end the loop once a review has landed and
been triaged — the polling is done, and what follows needs a person.

## Credit note

`triggerOnUpdates` is `false` in `.greptile/config.json`, so pushing new commits does
**not** re-trigger a review. A re-review costs 1 credit and must be requested by
commenting `@greptileai` on the PR — that is the user's call to make, not yours. Tell
them it is the next step; do not post it for them.
