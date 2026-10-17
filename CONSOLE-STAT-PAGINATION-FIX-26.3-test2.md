# NotBounties console stats and pagination repair: 26.3 test2

Candidate: `target/NotBounties-1.22.17-FOLIA-FIX-3-26.3-test2.jar`

SHA-256: `d75a80147f5bc34181f215f75d81e67b0781ee3380215c382b9747e114b89083`

The previous published/tested artifact remains unchanged at `target/NotBounties-1.22.17-FOLIA-FIX-3-26.3.jar`, SHA-256 `88e7b06f56c5949f3d6c759ed0d48a8f9bf87509c66503ae8e3d94392f135d3f`.

## Actual failures

The October 17 console pass reproduced three exceptions in `evidence/console-recheck-20261017-pass1.log` under the Turtle 26.3 root:

- At 12:20:52, READ32 `notbounties stat` passed the console's null player parser into Leaderboard.parseStats and dereferenced player.getUniqueId.
- At 12:20:54, READ34 `notbounties list 0` converted page 0 to index −1 and attempted list index −10.
- At 12:22:42, FEATURE03 `notbounties stat ALL turtleguy123456` resolved the real target but passed a null receiver into displayStats, then dereferenced receiver.isOnline.

`stat turtleguy123456` without the required leaderboard type already returned clean help; that syntax was not a defect reproduction.

## Changes

Targetless console stats, including `stat ALL`, now return explicit usage before reading a null player. Explicit `stat <leaderboard> <player>` formats the existing stat owner's data and sends it to the command's actual CommandSender. This supports console and preserves the requesting player's rendering/recipient. The existing public OfflinePlayer displayStats overloads remain available; the new sender-aware method has a separate name to avoid an ambiguous Player overload. Stats and view permissions are unchanged.

One-based command pages must be positive integers before subtraction. Zero, negative, malformed and out-of-int values are rejected with a clear message. The listing method also rejects negative zero-based callers and checks the available page count before multiplying. Row-end calculation is bounded by the remaining list size, so the last page remains safe even for a theoretical Integer.MAX_VALUE-sized list. Empty page1 remains valid. Valid row order and display are preserved; previous/next targets use numeric page addition. Out-of-range positive pages now report the valid range. Invalid text previously defaulted silently to page1; it now reports the invalid input.

Only Commands, Leaderboard and BountyManager main source, POM version/test configuration, two regression classes and this note changed. Economy, bounty placement/claim, storage, scheduling, sorting and currency rules are unchanged. No installed JAR, server process, runtime data, original checkout or publishing checkout was modified by this repair.

## Validation

Offline Java 25 Maven verify passed: **29 tests, zero failures/errors/skips**. The final build used the existing workspace Maven cache and `-Dmaven.jar.forceCreation=true`; no clean operation removed the frozen previous artifact.

- Eight actual-command/stat-method regressions cover targetless console usage, explicit offline-target console output, explicit target/self player recipients and long/short money/nonmoney rendering, unknown targets and stats permission denial.
- Twenty-one actual-command/list-method regressions cover0/negative/MIN pages, malformed/out-of-int numeric strings, MAX pages, sizes0/1/10/11, middle/partial-final row slices, previous/next links and view permission denial. A maximum-sized virtual list verifies the seven final indices through Integer.MAX_VALUE−1 without allocation or arithmetic overflow.
- Mockito isolates existing storage/configuration/language/Bukkit boundaries against the genuine provided API. Tests do not define replacement Bukkit API classes, duplicate the pagination implementation or start a server.

Evidence: `build-26.3-test2-console.log` and `target/surefire-reports/`. Packaged metadata declares version `1.22.17-FOLIA-FIX-3-26.3-test2`, API 26.3 and Folia support; main class major is 69. No server/API, JUnit, Mockito or test classes are bundled. Independent source/binary review passed: all 346 unrelated plugin classes and 1,836 dependency classes are byte-identical to the old tested JAR.

## Required live retest

The parent controls runtime installation and testing. After verifying the candidate hash/version, run `notbounties stat`, `notbounties stat ALL` and `notbounties stat ALL <knownPlayer>`; the first two must give usage, and the explicit target must give its formatted value without an exception. Check `notbounties list 1`, `notbounties list 0`, `notbounties list -1`, `notbounties list -2147483648`, `notbounties list 2147483647` and `notbounties list 2147483648`. Invalid pages must produce messages without indexing errors; valid list/top/check values must agree with unchanged saved bounty/stat state. Player self/target display and multi-page navigation still need actual player acceptance beyond mocked regressions. Do not use bounty or stat mutation commands as part of this retest.
