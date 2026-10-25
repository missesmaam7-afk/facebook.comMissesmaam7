# Missesmaam7 — Facebook Portrait Publisher

This repository is configured to generate a reference-guided photorealistic portrait with Google's Gemini image API and publish it to the configured Facebook Page.

## Schedule
GitHub Actions is scheduled for 10:00, 15:00, and 19:00 India Standard Time (UTC cron: 04:30, 09:30, 13:30).

## Required GitHub Actions secrets
- `FACEBOOK_PAGE_ID`: Facebook Page ID.
- `FACEBOOK_PAGE_ACCESS_TOKEN`: valid Page access token with supported publishing permissions (including `pages_manage_posts`, as applicable).
- `GEMINI_API_KEY`: Google AI Studio API key.
- `FACE_REFERENCE_IMAGE_BASE64`: a base64-encoded, compressed JPG/PNG reference portrait. Keep this private; do not commit the photo to this public repository.

GitHub Actions repository secrets have size limits (currently 48 KB per secret). Resize/crop the reference to a small JPG and compress it before base64 encoding. If the base64 text exceeds the secret limit, this secret-based method will not work; do not put the private image in this public repository. Make the repository private or use a private, access-controlled asset retrieval method instead.

## What the generator does
- Sends the reference image and an identity-preservation prompt to Google's image-generation Interactions API using model `gemini-nano-banana-2.1`.
- Requests the same recognizable adult woman, while varying outfit, pose, setting, and lighting.
- Saves a generated JPEG and a safe caption to the publishing queue.
- Fails instead of publishing a decorative placeholder if the API key, reference image, or generated image is missing.

## Important limitations
Prompting can improve resemblance but cannot guarantee an identical face in every generated image. Google model availability, API access, rate limits, and pricing/free quota depend on the Google account and current API terms. Generated images may include SynthID watermarking. Confirm the Google AI Studio model/API access and charges before relying on unattended daily publishing.

## Manual test
Open **Actions → Facebook Photo Publisher → Run workflow**. Check every job step and confirm the resulting post is visible on the Facebook Page. A green workflow alone is not proof that a public post is visible.

## Security
This repository has been public. Do not commit API keys, Page access tokens, or private face photos. Keep secrets in GitHub Actions Secrets. If a token was ever committed, revoke it and create a replacement; deleting it from the latest file does not remove it from Git history. Make the repository private if practical.
