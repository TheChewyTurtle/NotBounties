# NotBounties: tested 26.3 candidate

Validated October 15, 2026. Source version: `1.22.17-FOLIA-FIX-3-26.3`. Tested artifact: `NotBounties-1.22.17-FOLIA-FIX-3-26.3.jar`.

SHA-256: `88e7b06f56c5949f3d6c759ed0d48a8f9bf87509c66503ae8e3d94392f135d3f`.

Build with Java 25 and Maven using `mvn verify`. The POM provides Paper API `26.3.build.143-beta`; the descriptor declares API `26.3` and Folia support. The candidate ran on isolated Folia 26.3 build 3, API `26.3.build.3-alpha`, Java `25.0.4.1`. Validation used a prepared offline Maven cache. The provided dependency `com.ironcladmc:IronOrders:1.0.0` must resolve in the Maven repository; supply that compatible API artifact explicitly if unavailable from configured repositories. Local dependency JARs are not included.

The build passed. No automated regression tests exist in this candidate, so packaging success is not a test-suite result. Actual player checks covered the empty bounty browser, one configured self-bounty confirmation with one debit, one saved target/setter/bounty entry and persistence after restart. Self-setting was explicitly allowed by the isolated configuration.

Coverage remains partial: a second player's claim and payout, tracking, immunity, expiry, multi-currency integrations and simultaneous/distant-region cases remain open. No claim/payout acceptance is implied by placement persistence.

This branch starts at `77a3545b370c20e2e0f34f8569e1ecdc6a2b8d6c` and publishes the tested source/build payload. Original license, migration tools, translations and documentation are preserved. Existing source configuration files, including `secret.yml`, are repository templates, not live server configuration. The artifact SHA records the validated isolated JAR; fresh packaging can differ. No binaries, generated dependency-reduced POM, private cache or runtime data are added. Full plugin acceptance is pending.
