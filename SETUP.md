# Facebook photo automation — setup

Repository: `missesmaam7-afk/facebook.comMissesmaam7`

## What this currently does
- GitHub Actions runs at 10:00, 15:00, and 19:00 India Standard Time.
- Each run takes the first `pending` item in `queue/posts.json`, uploads its local image to the configured Facebook Page, and records the returned media/post ID.
- Queue state is committed back to the repository to avoid reposting the same pending item on later runs.
- Manual testing is available from **Actions → Facebook Photo Publisher → Run workflow**.

## Required GitHub Actions secrets
Open **Settings → Secrets and variables → Actions → New repository secret** and add:
- `FACEBOOK_PAGE_ID`: the numeric Facebook Page ID for the exact target Page.
- `FACEBOOK_PAGE_ACCESS_TOKEN`: a valid Page access token authorized for publishing photos to that Page.

Never commit access tokens into repository files. Confirm the token has the required Meta permissions and is issued for the intended Page. Do not use a personal user token where a Page token is required.

## Queue format
Add image files under `assets/queue/` and add entries to `queue/posts.json` with:
- `image`: repository-relative image path, e.g. `assets/queue/post-001.jpg`
- `caption`: caption and hashtags
- `status`: `pending`

Use unique entries and verify each image/caption before scheduling. Only add media you have rights to publish.

## Important limitations
This is a scheduled publisher for **already-created images and captions**. It does not yet generate AI images or captions. That requires a separate generation provider or a self-hosted model and its own credentials/runtime; free tiers and usage limits vary. The workflow is not active for publishing until the correct Page ID and valid Page access token are added and a test run succeeds.

The schedule is UTC-based and may be delayed by GitHub Actions queueing. Avoid running the workflow manually at the same time as a scheduled run.


## Current implementation status
- Scheduled publishing code is present, but no Facebook secrets have been configured by this repository workflow.
- The queue starts empty. Add real image files and matching queue entries before enabling a publishing test.
- AI image generation is not included in this version. Captions are supplied in queue entries; there is no caption-generation model connected yet.
- Do not add secrets to code or JSON files.
- The repository was reported as Public when inspected. Change it to Private in Settings → General → Danger Zone → Change repository visibility before adding any operational configuration.
