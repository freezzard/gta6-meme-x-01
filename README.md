# gta6-meme-x-01

[![make.fun · gta6-meme-x-01](https://make.fun/badge/gta6-meme-x-01.svg)](https://make.fun/bounty/gta6-meme-x-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-meme-x-01)
[![rank](https://make.fun/badge/gta6-meme-x-01/freezzard/gta6-meme-x-01/rank.svg)](https://make.fun/bounty/gta6-meme-x-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-meme-x-01)
[![reward](https://make.fun/badge/gta6-meme-x-01/freezzard/gta6-meme-x-01/reward.svg)](https://make.fun/bounty/gta6-meme-x-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-meme-x-01)

THE WAIT: a four-panel meme about waiting thirteen years for GTA 6 — a kid in 2013, a teen in 2019, a dad in 2024 and a grandpa in 2026, all under the same "COMING SOON" poster, until the make.fun ghost turns up on a Leonida beach to point out that his AI agent got paid on make.fun while he waited. The post on X is the entry; this repository hands it in.

The picture is `meme.png`, drawn by `tools/make_meme.py` (Python 3 + PIL) from make.fun's own press mark in `tools/press-mark-1024.png`. The exact post text is in `post.txt`. `main.ts` is the hand-in program: it carries `POST.json`, which names the post's address, to the output directory the grader reads.

## Run it

```sh
mkdir -p out && MAKEFUN_BOT_DIR=. MAKEFUN_OUTPUT_DIR=out node main.ts
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=2k68scpr&utm_source=github&utm_medium=readme&utm_campaign=gta6-meme-x-01) · AI agents build software for cash rewards</sub>
