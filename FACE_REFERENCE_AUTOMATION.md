# Daily Face-Reference Portrait Automation — Missesmaam7

## Goal
Publish three original, safe portrait posts per day to Facebook Page `436135029576334` at 10:00, 15:00, and 19:00 Asia/Kolkata time.

## Visual continuity
- Use an authorized, privately stored reference image as the identity/appearance reference for each generation.
- Keep the same overall facial appearance, hair, eyes, nose, lips, and natural skin texture.
- Change the location, outfit, pose, camera angle, and lighting each day.
- Generate one distinct image per scheduled run; avoid duplicate poses/scenes across recent posts.
- Keep images photorealistic and non-explicit.

## Safety rules
- Do not generate violence, graphic injury, vulgarity, nudity, or explicit sexual content.
- Do not add hateful, harassing, or abusive captions.
- Only use reference photos that the Page owner is authorized to use.
- Never commit the reference photo, access tokens, or private credentials to this repository.
- Store secrets in GitHub Actions repository secrets.

## Important implementation limitation
The current free local template generator can create decorative template images, but it cannot create realistic new photographs from a face reference. To meet the goal above, the workflow needs an image-generation provider/model that explicitly supports reference-image input. That provider may have usage limits or cost; do not claim fully automated same-face photorealistic generation until it is integrated and tested.

## Facebook publishing
- Page ID: `436135029576334`
- Required secret: `FACEBOOK_PAGE_ACCESS_TOKEN` (valid Page access token)
- Required secret: `FACEBOOK_PAGE_ID`
- Use the supported Meta Page publishing permissions, including `pages_manage_posts` where applicable.
- Never use the deprecated `publish_actions` permission.
- Fail clearly and preserve logs if generation or publishing fails; never print the token in logs.

## Scheduled workflow
Use GitHub Actions cron expressions with the timezone `Asia/Kolkata` if supported by the workflow syntax in use. Verify the schedule in Actions and test one manual run before relying on scheduled publishing.
