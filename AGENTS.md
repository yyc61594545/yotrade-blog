# YoTradeApi Blog automation

This repository publishes the Chinese SEO blog at `https://blog.yotradeapi.com`.

## Daily publishing

When asked to run the daily blog update, follow
`.claude/commands/daily-post.md` with these Codex-specific adaptations:

1. Produce 5 posts unless the task explicitly requests another count.
2. Start from an up-to-date `main` and create a unique
   `codex/daily-YYYY-MM-DD` branch. Never commit daily content directly to
   `main`.
3. Use `gh pr create` and `gh pr merge --squash --delete-branch` instead of
   the Claude GitHub MCP calls.
4. Treat `python3 scripts/validate-blog.py` and `npm run build` as required
   gates before pushing.
5. Merge only when both gates pass. After merging, wait for the
   `Deploy to Cloudflare Pages` GitHub Actions run and verify it succeeds.
6. Notify IndexNow only after the merge. IndexNow failure is non-blocking.
7. Preserve unrelated local changes and untracked files.
8. If an existing PR or published slug shows that today's run already
   completed, verify it instead of publishing duplicates.

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
