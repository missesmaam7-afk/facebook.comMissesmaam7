# Facebook photo automation — setup

Repository: `missesmaam7-afk/facebook.comMissesmaam7`

## What the workflow does
- GitHub Actions is scheduled for 10:00, 15:00, and 19:00 India Standard Time.
- If `OPENAI_API_KEY` is configured, it generates one original square image and one Hinglish caption per run.
- It then uploads the next pending image/caption to the configured Facebook Page.
- It records queue state to reduce accidental repeat posts.
- Manual test: **Actions → Facebook Photo Publisher → Run workflow**.

## Required GitHub Actions secrets
Open **Settings → Secrets and variables → Actions → New repository secret** and add:
- `FACEBOOK_PAGE_ID`: `436135029576334` for the Page shown in the Meta Business Suite screenshot; verify this is the intended Page.
- `FACEBOOK_PAGE_ACCESS_TOKEN`: a valid Page access token with publishing permission for that Page.
- `OPENAI_API_KEY`: optional for AI generation, but required if you want the workflow to generate new images and captions automatically. OpenAI API usage may be billed; ChatGPT plan access does not automatically include API credits.

Never paste tokens or API keys into code, screenshots, or chat. If a token was exposed in a screenshot, revoke/regenerate it.

## Schedule
The UTC cron `30 4,9,13 * * *` corresponds to 10:00, 15:00, and 19:00 IST. GitHub Actions may start a little late due to queueing.

## If you want zero API spend
Leave `OPENAI_API_KEY` unset and add your own image files plus captions to `queue/posts.json`. The workflow can publish queued posts, but it will not generate AI images/captions without a generation service.

## Before enabling
- Make the repository **Private** (Settings → General → Danger Zone) to avoid exposing operational details.
- Add the correct Page ID and a valid Page access token as GitHub Actions secrets.
- Test manually once and check the Actions log. Do not assume publishing works until the run succeeds and the post appears on the Page.
- Only publish images you have rights to use. The generator asks for original images and does not imitate a real person's identity.
