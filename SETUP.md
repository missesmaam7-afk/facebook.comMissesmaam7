# Facebook photo automation — setup

Repository: `missesmaam7-afk/facebook.comMissesmaam7`

## What the workflow does
- GitHub Actions runs at 10:00, 15:00, and 19:00 India Standard Time (UTC cron: `30 4,9,13 * * *`).
- `scripts/generate_content.py` sends the reference photo and prompt to Pollinations' image-edit API using the Flux.1 Kontext Pro model, then creates a Hinglish caption.
- The reference image is transmitted to Pollinations for image editing. Use this only if you consent to that third-party processing.
- `scripts/publish_next.py` uploads the next pending image/caption to the configured Facebook Page using the Facebook Graph API.
- Queue state is saved in `queue/posts.json` to reduce accidental repeat posts.
- Manual test: **Actions → Facebook Photo Publisher → Run workflow**.

## Required GitHub Actions secrets
Open **Settings → Secrets and variables → Actions → New repository secret** and add:

- `FACEBOOK_PAGE_ID`: verify this is the intended Page ID.
- `FACEBOOK_PAGE_ACCESS_TOKEN`: a valid Page access token with publishing permission for this Page (including `pages_manage_posts`, as applicable).
- `POLLINATIONS_API_KEY`: Pollinations secret key (`sk_…`), created at https://enter.pollinations.ai/keys. Keep it private; never commit it or place it in a URL.
- `FACE_REFERENCE_IMAGE_BASE64`: base64 text for a compressed JPG or PNG reference image. The base64 text must be below GitHub's 48 KB secret-value limit.

### Create the reference-image secret on Windows
1. Prepare a small JPG/PNG of the reference image.
2. In PowerShell, run (replace the path):
   ```powershell
   $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\path\to\reference.jpg"))
   $b64.Length
   $b64 | Set-Clipboard
   ```
3. If the printed length is 49152 or more, use a smaller/compressed image and repeat.
4. In GitHub, create a repository secret named exactly `FACE_REFERENCE_IMAGE_BASE64` and paste the clipboard contents.

Do not put the reference photo, base64 text, Page token, or API key in repository files, commits, screenshots, or chat. Never expose tokens or API keys; revoke/regenerate any that were exposed.

## Schedule
The UTC cron `30 4,9,13 * * *` corresponds to 10:00, 15:00, and 19:00 IST. GitHub Actions may start a little late due to queueing.

## Before enabling
- Make the repository **Private** (Settings → General → Danger Zone) to protect operational details.
- Confirm all four secrets are present and valid.
- Pollinations API usage may consume account balance/credits; check current pricing and budget in your Pollinations account.
- Run one manual workflow test and inspect each step. Confirm the run succeeds and the resulting post is visible on the Facebook Page; a green workflow alone is not proof of a visible post.
- Facial resemblance can be improved but exact identity matching is not guaranteed.
