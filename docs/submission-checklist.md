# Submission checklist

Deadline: (add from the hackathon page)

## Official submission form (confirmed with organizers)
One project only. It uses both Tavily and Bifrost, so the second-project section stays empty.

| Field | Our answer |
|---|---|
| Theme * | (pick on the form) |
| Project Title * | (team decides) |
| Github link * | https://github.com/Hak-36/syntax-dynasty-pbb |
| Demo Video Link | (add link after upload) |
| PPT File | (upload the deck) |
| Tavily problem statement | Pre-Meeting Briefing Agent |
| Two separate projects? | NA (not applied) |
| 2nd project fields | Leave empty |

- [ ] Video link opens in a private/incognito window (sharing set to "anyone with the link")
- [ ] PPT is under 7 slides: problem, solution, demo screenshot, architecture, Tavily + Bifrost, team
- [ ] Click "Save submission" and keep a screenshot of the confirmation

## PS-05 core requirements
- [ ] Accepts a company or person plus a meeting time
- [ ] Finds recent news, launches, hires and other updates from the last 30 days
- [ ] Concise, structured, one-page briefing
- [ ] Sources for factual claims, so users can verify them
- [ ] Open questions and discussion points for the meeting
- [ ] Verified and Uncertain findings are separated, and no details are invented

## Required tech (both must do real work)
- [ ] Tavily gives live web search (README section "How we use Tavily" is written)
- [ ] Bifrost handles every LLM call (README section, logs screenshot and fallback screenshot are in)

## Repo
- [ ] Public repo, and the README opens cleanly on GitHub
- [ ] Setup works from the README in about 15 minutes (ask a teammate to try it on a clean clone)
- [ ] `.env.example` has placeholders only, and `.env` is not in the repo
- [ ] No keys, tokens or passwords anywhere in the history
- [ ] Team names and roles are filled in the README
- [ ] All pull requests merged into `main`

## Demo
- [ ] Demo script rehearsed twice (`docs/demo-script.md`)
- [ ] Backup screen recording of a full successful run
- [ ] Pre-run the demo companies so the cache makes the live run fast
- [ ] Bifrost logs page and fallback shown in the demo

## Final 30 minutes
- [ ] Run the tests (`python -m pytest -v`, all passing)
- [ ] Open the live repo page and click through the README links
- [ ] Submit early, and save a screenshot or confirmation of the submission