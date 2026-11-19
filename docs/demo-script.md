# Demo script (3 minutes)

**Goal:** show a salesperson getting a trustworthy one-page briefing in under a minute, with proof that Tavily and Bifrost do real work.

## Before the demo (checklist)
- [ ] Bifrost is running (`npx -y @maximhq/bifrost`) and the dashboard logs page is open in a tab
- [ ] API is running (`uvicorn api.main:app`), `MOCK_MODE=0`
- [ ] `.env` has `TAVILY_API_KEY` and `BIFROST_VIRTUAL_KEY`
- [ ] Pre-run the demo company once so the cache makes the live run fast
- [ ] Backup: a screen recording of a full successful run

## Script

| Time | Say | Show |
|---|---|---|
| 0:00 | "Meet Priya, a salesperson. She meets Stripe tomorrow and has 5 minutes to prepare." | Title slide or the app's start page |
| 0:20 | "Normal chatbots answer from old memory and give no proof. Our agent searches the live web." | The input form |
| 0:35 | Type company, meeting time, meeting type "sales", click Generate | The form, then the loading state |
| 1:00 | "One page: a snapshot, key developments of the last 30 days, each with a date, a source link and a Verified or Uncertain tag." | The briefing |
| 1:30 | Click one source link. "Every claim can be checked." | The source opens in a new tab |
| 1:45 | Point at an Uncertain item. "If sources are weak or undated, we say so and never invent details." | The Uncertain tag and its note |
| 2:00 | "Talking points, risks and questions to ask in the meeting." | Bottom half of the briefing |
| 2:20 | "Tavily gives us live search. Every model call goes through Bifrost." | Bifrost dashboard logs page |
| 2:40 | "If a model fails, Bifrost falls back automatically." | Fallback screenshot or a quick `python -m api.bifrost_check --fallback` |
| 2:55 | "Traceable sources, honest uncertainty, built for a real meeting. Thank you." | Final slide |

## If something breaks
- Slow or failing live run: switch to the pre-recorded video.
- Tavily or Bifrost error: show the cached result for the pre-run company.
- No internet: run with `MOCK_MODE=1` and say clearly that it is sample data.

## Who does what
| Part | Owner |
|---|---|
| Speaking | (add) |
| Driving the app | (add) |
| Bifrost and Tavily explanation | (add) |