# Photo queue

Place your finished JPG or PNG images in this folder and reference them from `queue/posts.json`.
Each queue entry should have a unique id, image path, caption, and status set to `pending`.
The scheduled workflow publishes one pending photo per run.

This starter workflow does not generate AI images or captions yet. Automatic AI generation requires a separate model/service or a self-hosted runner; many hosted AI image APIs are paid or credit-limited.
