# tools/

## bountyhunters_to_notbounties.py

Converts a **BountyHunters** (Indyuce) plugin folder into **NotBounties** data and config.
Server-agnostic: run it against any server's folders. Python 3 standard library only.

```
python tools/bountyhunters_to_notbounties.py <plugins/BountyHunters> <plugins/NotBounties> \
    [--usercache <server>/usercache.json] [--jar NotBounties.jar] [--no-config] [--dry-run]
```

Recommended procedure on a live server:

1. Stop the server.
2. Copy `plugins/BountyHunters/` and `usercache.json` to your PC (or run the script on the host).
3. Run the script with the NotBounties folder as the output. If NotBounties has never
   started on that server, pass `--jar` so default config files can be extracted and edited.
4. Read `bountyhunters-migration-report.txt` in the output folder.
5. Remove the BountyHunters jar, install the NotBounties jar, start the server.
   NotBounties imports `bounties.yml` on first start and converts it to `data/*.json`.

### What is migrated

| BountyHunters | NotBounties |
|---|---|
| `data.yml` active bounties (target, per-setter contributions, console `extra`) | `bounties.yml` -> `data/bounties.json` |
| `userdata/*.yml` `claimed-bounties` | player stat `kills` |
| `userdata/*.yml` `successful-bounties` | player stat `set` |
| leaderboard caches + `usercache.json` names | `logged-players` name cache |
| `inactive-bounty-removal` | `config.yml` `bounty-expire.time` (hours -> days) |
| `claim-restrictions.own-bounties` | `config.yml` `setter-claim-own` (inverted) |
| `drop-head.creator/killer` | `config.yml` `reward-heads.setters/claimed` |
| `bounty-set-restriction` | `settings/immunity.yml` `bounty-cooldown` |
| `bounty-tax.bounty-creation.scale` (%) | `settings/money.yml` `bounty-tax` (decimal) |
| `min-reward` / `max-reward` | `settings/money.yml` `minimum-bounty` / `maximum-bounty` |
| `formatted-numbers` | `settings/money.yml` `number-formatting.use-divisions` |
| `player-tracking.enabled` / `can-track-own-bounties` | `settings/display.yml` `bounty-tracker.enabled` / `give-own` |
| `claim-restrictions` town/lands/clans/factions/kingdoms | `settings/integrations.yml` `teams.*` |
| `auto-bounty` (if enabled) | `settings/auto-bounties.yml` `murder-bounty.bounty-increase` |

### Not migrated (no NotBounties equivalent)

Levels, hunter titles, quotes/animations and `levels.yml` rewards; per-player illegal kills and
redeemable heads; `bounty-amount-restriction`; removal / target-set taxes; tax bank account;
tracking compass price and cooldown; login message; all `language/*.yml` text.
The report lists these for the folder you converted.
