# YoTradeApi Blog automation

This repository publishes the Chinese SEO blog at `https://blog.yotradeapi.com`.

## Daily publishing

`scripts/daily-run.sh` is the scheduled entry point (launchd, 09:00 local). It
tries Claude Code first and falls back to Codex, so both agents run the same
instructions: `.claude/commands/daily-post.md`, with these Codex-specific
adaptations:

1. Produce 5 posts unless the task explicitly requests another count.
2. Start from an up-to-date `main` and create a unique
   `codex/daily-YYYY-MM-DD` branch. Never commit daily content directly to
   `main`.
3. Treat `python3 scripts/validate-blog.py` and `npm run build` as required
   gates before pushing.
4. **Pushing the branch is where your job ends.** Do not open a PR, merge,
   deploy, or notify IndexNow — `.github/workflows/daily-autopublish.yml`
   does all of that on GitHub. It re-runs both gates on the pushed branch,
   squash-merges to `main`, deploys to Cloudflare Pages, and notifies
   IndexNow. It skips branches already merged, and refuses to merge anything
   touching paths outside `src/content/blog/`, `src/assets/`, and
   `scripts/topic-pool.md`.
5. This split is deliberate. `gh` resolves hostnames through `HTTP_PROXY`,
   which scheduled runs historically lost, producing
   `error connecting to api.github.com` and bogus `invalid keyring token`
   reports. `git push` uses git's own `http.proxy` setting and has stayed
   reliable. So never put `gh` on the critical path — if `gh` fails at any
   point, that alone is not a failed run.
6. Preserve unrelated local changes and untracked files.
7. If a pushed `*/daily-YYYY-MM-DD` branch or an already-published slug shows
   today's run completed, verify it instead of publishing duplicates.

## Topic pool

`scripts/pick-next-topic.py` is the source of truth for selection and
deduplication. If fewer than 30 unpublished topics remain, add at least 60
new candidates to `scripts/topic-pool.md` before publishing. New candidates
must use unique slugs, existing categories, and topics that fit YoTradeApi's
developer/API audience. Research unstable product, pricing, policy, or model
claims from primary sources before writing.

## Content and safety

- Follow the frontmatter schema in `src/content.config.ts`.
- Use factual, practical Chinese. Do not invent benchmarks, prices, release
  dates, funding figures, or product capabilities.
- Link only to existing internal slugs.
- Keep the YoTradeApi CTA factual and avoid guarantees.
- Do not expose tokens, credentials, customer data, or private operational
  details in posts, logs, commits, or PR bodies.
