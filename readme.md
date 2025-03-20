### To run the bot yourself
- You need to upload a resume, cover letter, transcript, and "other document" to Handshake (you can mark them private). There is a documents section where you can upload this.
  - If you're unsure about what to upload for the "other docuemnt," you can make it a pdf of links to portfolio pieces.
- Rename `.env.example` file to `.env` and replace the email and password fields with the credentials to your Handshake account
- Change the keywords in `query_keywords.py` to match the kind of jobs you're looking for
- Run apply.py. You may have to allow your IDE permission to use your mouse, but you should be prompted for this on your first run.

### Notes:
- Track how many jobs you've applied to with the bot, and other things at `utils/tracking.json`

### Soon to be features:
- I'm in the process of making `apply_robust.py` — Handshake is a buggy site. With or without a bot, sometimes you get the "Job Not Found" error for every single job. Sometimes your sesison times out. The file would be able to re-open a new driver and start immediately applying for new jobs from where it left off, reading from the logs of the previous session in job_tracking.json.
- If apply_robust.py becomes reliable enough, it could be scheduled as a CRON job and become a background process, running 24/7 until you apply to everything! This bot can run in a headless state (i.e. the browser is not needed)

<br>

![Handshake Bot Demo](assets/handshake_bot.gif)