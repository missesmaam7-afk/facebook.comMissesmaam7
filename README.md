# Missesmaam7 — Free Local Facebook Publisher

This repository generates decorative social graphics and captions locally with Python/Pillow, then uploads the image to the configured Facebook Page using the Meta Graph API.

## Important limitation
This workflow does **not** generate photorealistic portraits, face swaps, or same-face images from a reference photo. It has no image-generation API and does not upload or store a face reference. The generated files are graphic quote cards with decorative shapes and text.

## Schedule
The GitHub Actions workflow runs at 10:00, 15:00, and 19:00 India Standard Time (UTC cron schedule: 04:30, 09:30, 13:30).

## Required GitHub Actions secrets
- `FACEBOOK_PAGE_ID`: Page ID (currently intended to be `436135029576334`)
- `FACEBOOK_PAGE_ACCESS_TOKEN`: valid Page access token with supported publishing permissions, including `pages_manage_posts` as applicable.

Never put tokens in source code, commit history, workflow logs, or screenshots. Do not use deprecated `publish_actions`.

## Safe content rules
- Use nonviolent, non-explicit, non-vulgar positive captions and decorative graphics only.
- Do not add hateful, harassing, or abusive content.
- Generated graphics are local and free of paid image API calls; GitHub Actions usage remains subject to GitHub's usage limits.

## How it works
1. `scripts/generate_content.py` creates a locally generated PNG and safe caption and adds it to `queue/posts.json`.
2. `scripts/publish_next.py` uploads the next pending image and caption to the Page Photos endpoint.
3. The workflow saves the queue and generated images to the repository.
4. If Facebook publishing fails, the job reports the error and leaves the item pending for retry. Fix the cause before expecting future posts to publish.

## Manual test
Open **Actions → Facebook Photo Publisher → Run workflow**. Verify the workflow logs and confirm the resulting post is visible on the Facebook Page. A green workflow alone should not be treated as proof that a public post is visible.

## Security
Keep this repository private if practical. Review existing repository history before storing sensitive data. If a token was ever committed, revoke it in Meta and replace it; deleting it from the latest file does not remove it from Git history.
