# Facebook photo automation — setup

Repository: `missesmaam7-afk/facebook.comMissesmaam7`

## What the workflow does
- GitHub Actions runs at 10:00, 15:00, and 19:00 India Standard Time (UTC cron: `30 4,9,13 * * *`).
- `scripts/generate_content.py` uses the Google Gemini image API to create a reference-guided portrait and Hinglish caption.
- `scripts/publish_next.py` uploads the next pending image/caption to the configured Facebook Page using the Facebook Graph API.
- Queue state is saved in `queue/posts.json` to reduce accidental repeat posts.
- Manual test: **Actions → Facebook Photo Publisher → Run workflow**.

## Required GitHub Actions secrets
Open **Settings → Secrets and variables → Actions → New repository secret** and add all four:

- `FACEBOOK_PAGE_ID`: `436135029576334` (verify this is the intended Page).
- `FACEBOOK_PAGE_ACCESS_TOKEN`: a valid Page access token with publishing permission for this Page (including `pages_manage_posts`, as applicable).
- `GEMINI_API_KEY`: Google AI Studio API key with access to the configured image-generation model.
- `FACE_REFERENCE_IMAGE_BASE64`: base64 text for a compressed JPG or PNG reference image. This is required for the current reference-guided image generator; if it is missing, generation fails and the publish step is skipped.

### Create the reference-image secret on Windows
1. Prepare a small JPG/PNG of the reference image. GitHub Actions secrets have a 48 KB maximum value; the base64 text itself must be under that limit.
2. In PowerShell, run (replace the path):
   ```powershell
   $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\reference.jpg"))
   $b64.Length
   $b64 | Set-Clipboard
   ```
3. If the printed length is 49152 or more, use a smaller/compressed image and repeat.
4. In GitHub, create a repository secret named exactly `FACE_REFERENCE_IMAGE_BASE64` and paste the clipboard contents as its value.

Do not put the reference photo, base64 text, Page token, or API key in repository files, commits, screenshots, or chat. Never expose tokens or API keys; revoke/regenerate any that were exposed.

## Schedule
The UTC cron `30 4,9,13 * * *` corresponds to 10:00, 15:00, and 19:00 IST. GitHub Actions may start a little late due to queueing.

## Before enabling
- Make the repository **Private** (Settings → General → Danger Zone) to protect operational details.
- Confirm all four secrets are present and valid.
- Run one manual workflow test and inspect each step. Confirm the run succeeds and the resulting post is visible on the Facebook Page; a green workflow alone is not proof of a visible post.
- Google model availability, API access, quotas, and pricing depend on the Google account and current API terms.
- Only publish images you have rights to use. Prompting may improve resemblance but cannot guarantee an identical face.
