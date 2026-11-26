# Third-party notices

The root MIT license covers original harness software, fixtures, documentation and
annotations authored for this repository. It does not relicense the material
listed below. Copyright remains with the upstream authors.

## Drizzle archives and patch

| Distributed file | Origin and exact revision | License and notices |
|---|---|---|
| `runners/artifacts/drizzle-kit-0.31.8-smp.pr5074.tgz` | [PR #5074](https://github.com/drizzle-team/drizzle-orm/pull/5074), head [`72e975734e73d4bc7f4c80a7b4f411a4ff60437e`](https://github.com/ZerGo0/drizzle-orm/tree/72e975734e73d4bc7f4c80a7b4f411a4ff60437e), published base [0.31.8](https://registry.npmjs.org/drizzle-kit/0.31.8) | Package manifest declares MIT; author: Drizzle Team. See the source-license discrepancy below. |
| `runners/artifacts/drizzle-orm-0.45.3-smp.pr5784.tgz` | [PR #5784](https://github.com/drizzle-team/drizzle-orm/pull/5784), head [`2b3f6d8c4b016cb470fa06caa883038d1a93babb`](https://github.com/Zelys-DFKH/drizzle-orm/tree/2b3f6d8c4b016cb470fa06caa883038d1a93babb), published base [0.45.3](https://registry.npmjs.org/drizzle-orm/0.45.3) | Apache-2.0; [unaltered upstream license](licenses/drizzle-pr5784.txt), [retrieval URL](https://raw.githubusercontent.com/Zelys-DFKH/drizzle-orm/2b3f6d8c4b016cb470fa06caa883038d1a93babb/LICENSE). |
| `sources/drizzle-pr5784.patch` | Same #5784 head, relative to base [`48e5406027103a9fca6eb66417187c4a8b5c6aa3`](https://github.com/Zelys-DFKH/drizzle-orm/tree/48e5406027103a9fca6eb66417187c4a8b5c6aa3) | Apache-2.0; [upstream license](licenses/drizzle-pr5784.txt). The patch retains upstream changed source and context. |

Kit's [pinned package manifest](https://github.com/ZerGo0/drizzle-orm/blob/72e975734e73d4bc7f4c80a7b4f411a4ff60437e/drizzle-kit/package.json)
declares MIT, but the pinned repository has no `drizzle-kit/LICENSE` or other
package-specific MIT license text. Its sole license file is the root Apache-2.0
text, retained verbatim as [drizzle-pr5074-source.txt](licenses/drizzle-pr5074-source.txt)
from [this exact URL](https://raw.githubusercontent.com/ZerGo0/drizzle-orm/72e975734e73d4bc7f4c80a7b4f411a4ff60437e/LICENSE).
The [MIT standard text](licenses/MIT.txt) is supplied separately; it is not
represented as a missing upstream copyright notice. Both Drizzle root licenses
contain the standard Apache appendix's placeholder copyright line, rather than
a project-specific copyright notice.
The conflict between Kit's package declaration and source-tree license remains
unresolved by the pinned materials; upstream clarification is needed to establish
a single package-specific licensing statement.

The Kit archive contains 20 files: seven compiled runtime entries (`bin.cjs`,
`api.js`, `api.mjs`, `index.js`, `index.mjs`, `utils.js`, `utils.mjs`), their seven
build-input manifests, four declaration files, `package.json`, and `README.md`.
The runtime entries were compiled from PR #5074 using the locked esbuild build
environment. The API CommonJS build replaces dynamic imports with `require`;
the package version adds `-smp.pr5074`. Declarations and README are carried from
the published base package. The runtime includes the dependencies inventoried
below. External database drivers and the separately installed ORM are not bundled
by this build. The preserved build script is [build_drizzle.mjs](scripts/build_drizzle.mjs).

The ORM archive contains 2,690 files: the published base package's runtime
modules, type declarations, source maps, metadata and README, including its
multiple database adapters. Only the SQLite dialect's ESM/CommonJS modules and
their source maps were recompiled from PR #5784, after checking the published
base's embedded dialect source against the PR base. The version adds
`-smp.pr5784`. Third-party driver packages remain external; no additional
`node_modules` library bundle was found in this archive. The Drizzle patch is
the upstream dialect change; the harness does not edit the retained patch.
Exact archive hashes, source hashes, build inputs and runtime hashes are in
[sources/upstream_builds.json](sources/upstream_builds.json).

## Rails resolution patches

Both patches redistribute ActiveRecord source, tests and changelog context under
MIT. The original notices, preserved verbatim in each retrieved license, are:

> Copyright (c) David Heinemeier Hansson
>
> Arel originally copyright (c) 2007-2016 Nick Kallen, Bryan Helmkamp, Emilio Tagua, Aaron Patterson

| Patch | Upstream parents | Full license texts at the pinned heads |
|---|---|---|
| `sources/rails-pr57128+56811-resolution.patch` | [#57128](https://github.com/rails/rails/pull/57128) at `8823c1370c7bc8910e609d1b6f27f4fc34f3d81d` and [#56811](https://github.com/rails/rails/pull/56811) at `7ddc17783418454c0e406181ae442d0aaf558ad8` | [#57128 text](licenses/rails-pr57128.txt), [retrieval URL](https://raw.githubusercontent.com/emirn/rails/8823c1370c7bc8910e609d1b6f27f4fc34f3d81d/activerecord/MIT-LICENSE); [#56811 text](licenses/rails-pr56811.txt), [retrieval URL](https://raw.githubusercontent.com/aka-nez/rails/7ddc17783418454c0e406181ae442d0aaf558ad8/activerecord/MIT-LICENSE) |
| `sources/rails-pr58709+56811-resolution.patch` | [#58709](https://github.com/rails/rails/pull/58709) at `428884a88b3a42c914f5227819b6b672325b3312` and the same #56811 head | [#58709 text](licenses/rails-pr58709.txt), [retrieval URL](https://raw.githubusercontent.com/nicolasva/rails/428884a88b3a42c914f5227819b6b672325b3312/activerecord/MIT-LICENSE); [#56811 text](licenses/rails-pr56811.txt), [retrieval URL](https://raw.githubusercontent.com/aka-nez/rails/7ddc17783418454c0e406181ae442d0aaf558ad8/activerecord/MIT-LICENSE) |

These are locally resolved merge deltas relative to each first parent, combining
foreign-key/transaction handling with trigger preservation. The #57128 merge
resolves conflicts in the changelog, SQLite schema statements, adapter and adapter
tests. The #58709 merge resolves changelog and SQLite schema-statement conflicts.
The resulting local revisions are `5827151e652ee67ed7060e7da20c67ab2a75fb31` and
`bec5f3e1d7ec75a43f65af23b7b58e65b20caf9e`, respectively. Their complete delta,
parent hashes, tree hashes and deterministic identity are recorded in the patches
and [sources/upstream_fixes.json](sources/upstream_fixes.json).

## Tracker quotations

`results/tracker_labels.jsonl` contains original annotations and short quotations
from public GitHub issues and pull requests. Each record links its source.
Copyright in the quotations remains with their authors; quoted text is not
covered by this repository's MIT license. Source URLs supply attribution and
context; the data does not claim quote-level author identities or comment anchors
where those were not recorded. Original labels and adjudications are distinct
from the quoted evidence.

## Replay evidence

`results/realworld.json` references pinned public histories and contains no
migration files; its event lists hold the transaction and PRAGMA statements
that were executed, some of which come from project migrations. Full project SQL/schema in the dated rerun requires both a
recorded MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause or ISC label and applicable
license text collected at the exact migration commit. All 25 full artifacts meet
this condition. For each of these rows `evidence.license_notices` points to a hashed
project provenance manifest. The [notice index](licenses/replay/index.json) links
each project, commit, retrieved file and corresponding artifact. Original notice
bytes and copyright lines are retained; they are not replaced by the root MIT
license. Complete pinned repository trees were checked for LICENSE, LICENCE,
COPYING, COPYRIGHT and NOTICE files; no separate NOTICE file was found in these
25 trees. Application modules named `licence.ts` are not license notices.

`skyfallwastaken/at-channel` has `LICENSE-APACHE` and `LICENSE-MIT` at its pinned
commit. Both are included below, although the `license_files` field recorded for
this project in the aggregate is empty. A project without applicable license
files at the pinned commit is redacted even if its recorded label is permissive.
A notice manifest with a missing or altered file fails verification.

The other 68 artifacts contain hashes and source positions in place of project
SQL and schema; framework SQL and synthetic values are verbatim. One of them is
a failed attempt without project SQL and is published unchanged; the unredacted
files of the other 67 are not published. The
[evidence README](results/realworld-rerun-2026-11-02/README.md) describes the
files; `scripts/rebuild_realworld_evidence.py` produces full evidence again from
the pinned commits. The root MIT license covers original harness observations,
not third-party project material.

| Project and pinned source | Commit | Retained notices and artifact provenance |
|---|---|---|
| [pitzzahh/powertrackr](https://github.com/pitzzahh/powertrackr/tree/2b907ed3614de56ab19205c32f9660376787f9f1) | `2b907ed3614de56ab19205c32f9660376787f9f1` | [LICENSE](licenses/replay/pitzzahh__powertrackr/LICENSE) ([source](https://raw.githubusercontent.com/pitzzahh/powertrackr/2b907ed3614de56ab19205c32f9660376787f9f1/LICENSE)); [provenance](licenses/replay/pitzzahh__powertrackr/provenance.json) |
| [XeinTDM/MeatFlicks](https://github.com/XeinTDM/MeatFlicks/tree/c0bd316872ec36b47ce8135f0faa0a1868382511) | `c0bd316872ec36b47ce8135f0faa0a1868382511` | [LICENSE](licenses/replay/XeinTDM__MeatFlicks/LICENSE) ([source](https://raw.githubusercontent.com/XeinTDM/MeatFlicks/c0bd316872ec36b47ce8135f0faa0a1868382511/LICENSE)); [provenance](licenses/replay/XeinTDM__MeatFlicks/provenance.json) |
| [ncvyn/adu-tutor](https://github.com/ncvyn/adu-tutor/tree/96475068d8ba7455f742e98d6f2ae149039f3ea0) | `96475068d8ba7455f742e98d6f2ae149039f3ea0` | [LICENSE](licenses/replay/ncvyn__adu-tutor/LICENSE) ([source](https://raw.githubusercontent.com/ncvyn/adu-tutor/96475068d8ba7455f742e98d6f2ae149039f3ea0/LICENSE)); [provenance](licenses/replay/ncvyn__adu-tutor/provenance.json) |
| [choyiny/saasmail](https://github.com/choyiny/saasmail/tree/1be56eb77246b3f355469983a970265f63b7c47c) | `1be56eb77246b3f355469983a970265f63b7c47c` | [LICENSE](licenses/replay/choyiny__saasmail/LICENSE) ([source](https://raw.githubusercontent.com/choyiny/saasmail/1be56eb77246b3f355469983a970265f63b7c47c/LICENSE)); [provenance](licenses/replay/choyiny__saasmail/provenance.json) |
| [alteran-social/alteran](https://github.com/alteran-social/alteran/tree/6bfa4be0fc79aaee55fb35d48dada5f70788d360) | `6bfa4be0fc79aaee55fb35d48dada5f70788d360` | [LICENSE](licenses/replay/alteran-social__alteran/LICENSE) ([source](https://raw.githubusercontent.com/alteran-social/alteran/6bfa4be0fc79aaee55fb35d48dada5f70788d360/LICENSE)); [provenance](licenses/replay/alteran-social__alteran/provenance.json) |
| [flyaltitudeapp/altitude](https://github.com/flyaltitudeapp/altitude/tree/4ddaf5625d1211d6eac706188a9809ab9716163e) | `4ddaf5625d1211d6eac706188a9809ab9716163e` | [LICENCE](licenses/replay/flyaltitudeapp__altitude/LICENCE) ([source](https://raw.githubusercontent.com/flyaltitudeapp/altitude/4ddaf5625d1211d6eac706188a9809ab9716163e/LICENCE)); [provenance](licenses/replay/flyaltitudeapp__altitude/provenance.json) |
| [Shiinama/next-cloudflare-template](https://github.com/Shiinama/next-cloudflare-template/tree/a35f20e9f251fa6a3dfc1f9bd139fc24d983f8f4) | `a35f20e9f251fa6a3dfc1f9bd139fc24d983f8f4` | [LICENSE](licenses/replay/Shiinama__next-cloudflare-template/LICENSE) ([source](https://raw.githubusercontent.com/Shiinama/next-cloudflare-template/a35f20e9f251fa6a3dfc1f9bd139fc24d983f8f4/LICENSE)); [provenance](licenses/replay/Shiinama__next-cloudflare-template/provenance.json) |
| [skyfallwastaken/at-channel](https://github.com/skyfallwastaken/at-channel/tree/aa486b2dbf7515136bb8385e970500c74f67b646) | `aa486b2dbf7515136bb8385e970500c74f67b646` | [LICENSE-APACHE](licenses/replay/skyfallwastaken__at-channel/LICENSE-APACHE) ([source](https://raw.githubusercontent.com/skyfallwastaken/at-channel/aa486b2dbf7515136bb8385e970500c74f67b646/LICENSE-APACHE)); [LICENSE-MIT](licenses/replay/skyfallwastaken__at-channel/LICENSE-MIT) ([source](https://raw.githubusercontent.com/skyfallwastaken/at-channel/aa486b2dbf7515136bb8385e970500c74f67b646/LICENSE-MIT)); [provenance](licenses/replay/skyfallwastaken__at-channel/provenance.json) |
| [raffaele-lungarella/appointment-scheduler](https://github.com/raffaele-lungarella/appointment-scheduler/tree/116c9371d2ff0679b698cfe8d9d3949fad1d62fa) | `116c9371d2ff0679b698cfe8d9d3949fad1d62fa` | [LICENSE](licenses/replay/raffaele-lungarella__appointment-scheduler/LICENSE) ([source](https://raw.githubusercontent.com/raffaele-lungarella/appointment-scheduler/116c9371d2ff0679b698cfe8d9d3949fad1d62fa/LICENSE)); [provenance](licenses/replay/raffaele-lungarella__appointment-scheduler/provenance.json) |
| [bradymholt/snoozer](https://github.com/bradymholt/snoozer/tree/71b56c1b2ff1c264ba2af4737368f4dc5c50a2e9) | `71b56c1b2ff1c264ba2af4737368f4dc5c50a2e9` | [LICENSE](licenses/replay/bradymholt__snoozer/LICENSE) ([source](https://raw.githubusercontent.com/bradymholt/snoozer/71b56c1b2ff1c264ba2af4737368f4dc5c50a2e9/LICENSE)); [provenance](licenses/replay/bradymholt__snoozer/provenance.json) |
| [vaibhavrxj/-vaibhav-asset-intelligence](https://github.com/vaibhavrxj/-vaibhav-asset-intelligence/tree/10d799c850557a3303809a3375be6182dceaf197) | `10d799c850557a3303809a3375be6182dceaf197` | [LICENSE](licenses/replay/vaibhavrxj__-vaibhav-asset-intelligence/LICENSE) ([source](https://raw.githubusercontent.com/vaibhavrxj/-vaibhav-asset-intelligence/10d799c850557a3303809a3375be6182dceaf197/LICENSE)); [provenance](licenses/replay/vaibhavrxj__-vaibhav-asset-intelligence/provenance.json) |
| [realmroot/realmroot](https://github.com/realmroot/realmroot/tree/be7ab7472f1b73675670a4ce03a7a6cb84130e90) | `be7ab7472f1b73675670a4ce03a7a6cb84130e90` | [LICENSE](licenses/replay/realmroot__realmroot/LICENSE) ([source](https://raw.githubusercontent.com/realmroot/realmroot/be7ab7472f1b73675670a4ce03a7a6cb84130e90/LICENSE)); [provenance](licenses/replay/realmroot__realmroot/provenance.json) |
| [dadezzz/events-cash-register](https://github.com/dadezzz/events-cash-register/tree/25293b8d312ca8075fa064b09988d124c614188e) | `25293b8d312ca8075fa064b09988d124c614188e` | [LICENSE](licenses/replay/dadezzz__events-cash-register/LICENSE) ([source](https://raw.githubusercontent.com/dadezzz/events-cash-register/25293b8d312ca8075fa064b09988d124c614188e/LICENSE)); [provenance](licenses/replay/dadezzz__events-cash-register/provenance.json) |
| [trevclev0/terminal-quiz](https://github.com/trevclev0/terminal-quiz/tree/5a92afeed96c25df83ed6d1b7ece80e391f090a3) | `5a92afeed96c25df83ed6d1b7ece80e391f090a3` | [LICENSE](licenses/replay/trevclev0__terminal-quiz/LICENSE) ([source](https://raw.githubusercontent.com/trevclev0/terminal-quiz/5a92afeed96c25df83ed6d1b7ece80e391f090a3/LICENSE)); [provenance](licenses/replay/trevclev0__terminal-quiz/provenance.json) |
| [tijptjik/hype](https://github.com/tijptjik/hype/tree/6ee39e249f1b42013b8b49530509b0f2e74dd2d4) | `6ee39e249f1b42013b8b49530509b0f2e74dd2d4` | [LICENSE.md](licenses/replay/tijptjik__hype/LICENSE.md) ([source](https://raw.githubusercontent.com/tijptjik/hype/6ee39e249f1b42013b8b49530509b0f2e74dd2d4/LICENSE.md)); [provenance](licenses/replay/tijptjik__hype/provenance.json) |
| [BatthewZ/cadence-public](https://github.com/BatthewZ/cadence-public/tree/0f07383719c43fb55acc97c6fc6d942d6d785716) | `0f07383719c43fb55acc97c6fc6d942d6d785716` | [LICENSE](licenses/replay/BatthewZ__cadence-public/LICENSE) ([source](https://raw.githubusercontent.com/BatthewZ/cadence-public/0f07383719c43fb55acc97c6fc6d942d6d785716/LICENSE)); [provenance](licenses/replay/BatthewZ__cadence-public/provenance.json) |
| [VesperQuartz/payhub](https://github.com/VesperQuartz/payhub/tree/23b58005cc121af5c0dfef8de853b56d40456442) | `23b58005cc121af5c0dfef8de853b56d40456442` | [LICENSE](licenses/replay/VesperQuartz__payhub/LICENSE) ([source](https://raw.githubusercontent.com/VesperQuartz/payhub/23b58005cc121af5c0dfef8de853b56d40456442/LICENSE)); [provenance](licenses/replay/VesperQuartz__payhub/provenance.json) |
| [syahrulfadli/kanban-app](https://github.com/syahrulfadli/kanban-app/tree/f3b42a93eaabb2dae9a5987e7638318cec4568da) | `f3b42a93eaabb2dae9a5987e7638318cec4568da` | [LICENSE](licenses/replay/syahrulfadli__kanban-app/LICENSE) ([source](https://raw.githubusercontent.com/syahrulfadli/kanban-app/f3b42a93eaabb2dae9a5987e7638318cec4568da/LICENSE)); [provenance](licenses/replay/syahrulfadli__kanban-app/provenance.json) |
| [Ankit-Maurya-12223197/Ai-Powered-Inventory](https://github.com/Ankit-Maurya-12223197/Ai-Powered-Inventory/tree/da6ab17911f9bbf6276255650e27489cc109d21a) | `da6ab17911f9bbf6276255650e27489cc109d21a` | [LICENSE](licenses/replay/Ankit-Maurya-12223197__Ai-Powered-Inventory/LICENSE) ([source](https://raw.githubusercontent.com/Ankit-Maurya-12223197/Ai-Powered-Inventory/da6ab17911f9bbf6276255650e27489cc109d21a/LICENSE)); [provenance](licenses/replay/Ankit-Maurya-12223197__Ai-Powered-Inventory/provenance.json) |
| [srvo/saasmail](https://github.com/srvo/saasmail/tree/b287dcbff2cf151b722a015f93a86f4253dacc14) | `b287dcbff2cf151b722a015f93a86f4253dacc14` | [LICENSE](licenses/replay/srvo__saasmail/LICENSE) ([source](https://raw.githubusercontent.com/srvo/saasmail/b287dcbff2cf151b722a015f93a86f4253dacc14/LICENSE)); [provenance](licenses/replay/srvo__saasmail/provenance.json) |
| [jtk5aw/committed](https://github.com/jtk5aw/committed/tree/82b97fa333e7872440a5322c2b469054085d2ffc) | `82b97fa333e7872440a5322c2b469054085d2ffc` | [LICENSE](licenses/replay/jtk5aw__committed/LICENSE) ([source](https://raw.githubusercontent.com/jtk5aw/committed/82b97fa333e7872440a5322c2b469054085d2ffc/LICENSE)); [provenance](licenses/replay/jtk5aw__committed/provenance.json) |
| [kuranai/dovari](https://github.com/kuranai/dovari/tree/89af16260e71e0d0f6a46981da2c188dfafab2f1) | `89af16260e71e0d0f6a46981da2c188dfafab2f1` | [LICENSE](licenses/replay/kuranai__dovari/LICENSE) ([source](https://raw.githubusercontent.com/kuranai/dovari/89af16260e71e0d0f6a46981da2c188dfafab2f1/LICENSE)); [provenance](licenses/replay/kuranai__dovari/provenance.json) |
| [kuranai/kuranai-com](https://github.com/kuranai/kuranai-com/tree/f0d47bb4f6618901dc3f7873b5388fe726ba6bc6) | `f0d47bb4f6618901dc3f7873b5388fe726ba6bc6` | [LICENSE](licenses/replay/kuranai__kuranai-com/LICENSE) ([source](https://raw.githubusercontent.com/kuranai/kuranai-com/f0d47bb4f6618901dc3f7873b5388fe726ba6bc6/LICENSE)); [provenance](licenses/replay/kuranai__kuranai-com/provenance.json) |
| [columk1/threads-clone](https://github.com/columk1/threads-clone/tree/41d9bcb92c9d414417e0da2d4175c171ee26ecab) | `41d9bcb92c9d414417e0da2d4175c171ee26ecab` | [LICENSE](licenses/replay/columk1__threads-clone/LICENSE) ([source](https://raw.githubusercontent.com/columk1/threads-clone/41d9bcb92c9d414417e0da2d4175c171ee26ecab/LICENSE)); [provenance](licenses/replay/columk1__threads-clone/provenance.json) |
| [dynamicagents/slack-gatekeeper](https://github.com/dynamicagents/slack-gatekeeper/tree/c28aaf2c253533d92afdca567548238d30d8ce69) | `c28aaf2c253533d92afdca567548238d30d8ce69` | [LICENSE](licenses/replay/dynamicagents__slack-gatekeeper/LICENSE) ([source](https://raw.githubusercontent.com/dynamicagents/slack-gatekeeper/c28aaf2c253533d92afdca567548238d30d8ce69/LICENSE)); [provenance](licenses/replay/dynamicagents__slack-gatekeeper/provenance.json) |

## Libraries bundled inside Kit

The following inventory comes from the seven `*.inputs.json` members of the
retained Kit archive, matched to `runners/build-drizzle/package-lock.json`.
It lists 61 package/version entries, including two versions of minimatch.
The [machine-readable inventory](licenses/kit-bundled.json) records package
origins, exact download URLs, integrity hashes, retrieved notice paths and hashes,
and upstream revisions where supplied by the registry. Archive integrity was
checked before extracting notices. Full license/NOTICE files retain their original
copyright lines. [Embedded legal comments](licenses/kit-embedded-notices.txt)
are copied without alteration from the compiled Kit entries and remain in the
archive too. The inventory also links `SOURCE-NOTICES.txt` files containing
legal comments from the contributing dependency source files. These preserve
the Node/Joyent notice in fs.realpath and the notices in lodash.throttle,
fetch-blob, web-streams-polyfill and Gel. Chalk also includes its vendored
ANSI-style and color-support utilities in the counted package inputs. This includes MagicStack/Gel and Python Software Foundation notices;
Gel's date utility and the difflib port carry Python-derived licensing in addition
to the package-level declarations. [PSF text](licenses/PSF-2.0.txt) accompanies
those notices. The difflib README's complete license section is also retained.

Bundled libraries were incorporated by esbuild without harness source edits.
Some published packages omit license files and registry commit identifiers.
Six of the published archives contain no separate license or notice file;
[the archive review](licenses/kit-bundled-review.md) lists each checked URL,
file count and result. The README of `@hono/zod-validator` 0.2.2 contains only
the declaration “MIT”, which is recorded verbatim. For these packages the text
of the declared license is supplied; the checked archives contain no
package-specific notice. SPDX
standard texts are supplements, not evidence of an upstream copyright statement.
[licenses/sources.json](licenses/sources.json) records their pinned retrieval URLs
alongside the top-level upstream license URLs.

| Bundled package | Version | Declared license / source notice | Origin (exact package) | Full license or notice |
|---|---|---|---|---|
| `@aws-sdk/client-rds-data` | 3.1148.0 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/client-rds-data/-/client-rds-data-3.1148.0.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__client-rds-data-3.1148.0/LICENSE) |
| `@aws-sdk/core` | 3.978.1 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/core/-/core-3.978.1.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__core-3.978.1/LICENSE) |
| `@aws-sdk/credential-provider-env` | 3.972.72 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-env/-/credential-provider-env-3.972.72.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__credential-provider-env-3.972.72/LICENSE) |
| `@aws-sdk/credential-provider-http` | 3.972.74 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-http/-/credential-provider-http-3.972.74.tgz) | [declared text](licenses/drizzle-pr5074-source.txt); package notice absent |
| `@aws-sdk/credential-provider-ini` | 3.973.17 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-ini/-/credential-provider-ini-3.973.17.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__credential-provider-ini-3.973.17/LICENSE) |
| `@aws-sdk/credential-provider-login` | 3.972.79 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-login/-/credential-provider-login-3.972.79.tgz) | [declared text](licenses/drizzle-pr5074-source.txt); package notice absent |
| `@aws-sdk/credential-provider-node` | 3.972.84 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-node/-/credential-provider-node-3.972.84.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__credential-provider-node-3.972.84/LICENSE) |
| `@aws-sdk/credential-provider-process` | 3.972.72 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-process/-/credential-provider-process-3.972.72.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__credential-provider-process-3.972.72/LICENSE) |
| `@aws-sdk/credential-provider-sso` | 3.973.16 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-sso/-/credential-provider-sso-3.973.16.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__credential-provider-sso-3.973.16/LICENSE) |
| `@aws-sdk/credential-provider-web-identity` | 3.972.78 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/credential-provider-web-identity/-/credential-provider-web-identity-3.972.78.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__credential-provider-web-identity-3.972.78/LICENSE) |
| `@aws-sdk/nested-clients` | 3.997.46 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/nested-clients/-/nested-clients-3.997.46.tgz) | [declared text](licenses/drizzle-pr5074-source.txt); package notice absent |
| `@aws-sdk/signature-v4-multi-region` | 3.996.47 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/signature-v4-multi-region/-/signature-v4-multi-region-3.996.47.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__signature-v4-multi-region-3.996.47/LICENSE) |
| `@aws-sdk/token-providers` | 3.1138.0 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/token-providers/-/token-providers-3.1138.0.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__token-providers-3.1138.0/LICENSE) |
| `@aws-sdk/xml-builder` | 3.972.41 | Apache-2.0 | [package](https://registry.npmjs.org/@aws-sdk/xml-builder/-/xml-builder-3.972.41.tgz) | [LICENSE](licenses/kit-bundled/@aws-sdk__xml-builder-3.972.41/LICENSE) |
| `@aws/lambda-invoke-store` | 0.3.0 | Apache-2.0 | [package](https://registry.npmjs.org/@aws/lambda-invoke-store/-/lambda-invoke-store-0.3.0.tgz) | [LICENSE](licenses/kit-bundled/@aws__lambda-invoke-store-0.3.0/LICENSE) |
| `@drizzle-team/brocli` | 0.10.2 | Apache-2.0 | [package](https://registry.npmjs.org/@drizzle-team/brocli/-/brocli-0.10.2.tgz) | [declared text](licenses/drizzle-pr5074-source.txt); package notice absent |
| `@ewoudenberg/difflib` | 0.1.0 | PSF-2.0 | [package](https://registry.npmjs.org/@ewoudenberg/difflib/-/difflib-0.1.0.tgz) | [LICENSE-from-README.md](licenses/kit-bundled/@ewoudenberg__difflib-0.1.0/LICENSE-from-README.md) |
| `@hono/node-server` | 1.19.17 | MIT | [package](https://registry.npmjs.org/@hono/node-server/-/node-server-1.19.17.tgz) | [LICENSE](licenses/kit-bundled/@hono__node-server-1.19.17/LICENSE) |
| `@hono/zod-validator` | 0.2.2 | MIT | [package](https://registry.npmjs.org/@hono/zod-validator/-/zod-validator-0.2.2.tgz) | [declared text](licenses/MIT.txt); package notice absent |
| `@petamoriken/float16` | 3.9.3 | MIT | [package](https://registry.npmjs.org/@petamoriken/float16/-/float16-3.9.3.tgz) | [LICENSE](licenses/kit-bundled/@petamoriken__float16-3.9.3/LICENSE) |
| `@smithy/core` | 3.35.2 | Apache-2.0 | [package](https://registry.npmjs.org/@smithy/core/-/core-3.35.2.tgz) | [LICENSE](licenses/kit-bundled/@smithy__core-3.35.2/LICENSE) |
| `@smithy/credential-provider-imds` | 4.5.2 | Apache-2.0 | [package](https://registry.npmjs.org/@smithy/credential-provider-imds/-/credential-provider-imds-4.5.2.tgz) | [LICENSE](licenses/kit-bundled/@smithy__credential-provider-imds-4.5.2/LICENSE) |
| `@smithy/node-http-handler` | 4.12.1 | Apache-2.0 | [package](https://registry.npmjs.org/@smithy/node-http-handler/-/node-http-handler-4.12.1.tgz) | [LICENSE](licenses/kit-bundled/@smithy__node-http-handler-4.12.1/LICENSE) |
| `@smithy/signature-v4` | 5.7.4 | Apache-2.0 | [package](https://registry.npmjs.org/@smithy/signature-v4/-/signature-v4-5.7.4.tgz) | [LICENSE](licenses/kit-bundled/@smithy__signature-v4-5.7.4/LICENSE) |
| `@smithy/types` | 4.19.0 | Apache-2.0 | [package](https://registry.npmjs.org/@smithy/types/-/types-4.19.0.tgz) | [LICENSE](licenses/kit-bundled/@smithy__types-4.19.0/LICENSE) |
| `balanced-match` | 1.0.2 | MIT | [package](https://registry.npmjs.org/balanced-match/-/balanced-match-1.0.2.tgz) | [LICENSE.md](licenses/kit-bundled/balanced-match-1.0.2/LICENSE.md) |
| `bowser` | 2.14.1 | MIT | [package](https://registry.npmjs.org/bowser/-/bowser-2.14.1.tgz) | [LICENSE](licenses/kit-bundled/bowser-2.14.1/LICENSE) |
| `brace-expansion` | 2.1.7 | MIT | [package](https://registry.npmjs.org/brace-expansion/-/brace-expansion-2.1.7.tgz) | [LICENSE](licenses/kit-bundled/brace-expansion-2.1.7/LICENSE) |
| `camelcase` | 7.0.1 | MIT | [package](https://registry.npmjs.org/camelcase/-/camelcase-7.0.1.tgz) | [license](licenses/kit-bundled/camelcase-7.0.1/license) |
| `chalk` | 5.6.2 | MIT | [package](https://registry.npmjs.org/chalk/-/chalk-5.6.2.tgz) | [license](licenses/kit-bundled/chalk-5.6.2/license) |
| `colors` | 1.4.0 | MIT | [package](https://registry.npmjs.org/colors/-/colors-1.4.0.tgz) | [LICENSE](licenses/kit-bundled/colors-1.4.0/LICENSE) |
| `data-uri-to-buffer` | 4.0.1 | MIT | [package](https://registry.npmjs.org/data-uri-to-buffer/-/data-uri-to-buffer-4.0.1.tgz) | [LICENSE-from-README.md](licenses/kit-bundled/data-uri-to-buffer-4.0.1/LICENSE-from-README.md) |
| `debug` | 4.4.3 | MIT | [package](https://registry.npmjs.org/debug/-/debug-4.4.3.tgz) | [LICENSE](licenses/kit-bundled/debug-4.4.3/LICENSE) |
| `dotenv` | 16.6.1 | BSD-2-Clause | [package](https://registry.npmjs.org/dotenv/-/dotenv-16.6.1.tgz) | [LICENSE](licenses/kit-bundled/dotenv-16.6.1/LICENSE) |
| `env-paths` | 3.0.0 | MIT | [package](https://registry.npmjs.org/env-paths/-/env-paths-3.0.0.tgz) | [license](licenses/kit-bundled/env-paths-3.0.0/license) |
| `esbuild-register` | 3.6.0 | MIT | [package](https://registry.npmjs.org/esbuild-register/-/esbuild-register-3.6.0.tgz) | [LICENSE](licenses/kit-bundled/esbuild-register-3.6.0/LICENSE) |
| `fetch-blob` | 3.2.0 | MIT | [package](https://registry.npmjs.org/fetch-blob/-/fetch-blob-3.2.0.tgz) | [LICENSE](licenses/kit-bundled/fetch-blob-3.2.0/LICENSE) |
| `formdata-polyfill` | 4.0.10 | MIT | [package](https://registry.npmjs.org/formdata-polyfill/-/formdata-polyfill-4.0.10.tgz) | [LICENSE](licenses/kit-bundled/formdata-polyfill-4.0.10/LICENSE) |
| `fs.realpath` | 1.0.0 | ISC | [package](https://registry.npmjs.org/fs.realpath/-/fs.realpath-1.0.0.tgz) | [LICENSE](licenses/kit-bundled/fs.realpath-1.0.0/LICENSE) |
| `gel` | 2.2.1 | Apache-2.0 | [package](https://registry.npmjs.org/gel/-/gel-2.2.1.tgz) | [UPSTREAM-LICENSE](licenses/kit-bundled/gel-2.2.1/UPSTREAM-LICENSE) |
| `glob` | 8.1.0 | ISC | [package](https://registry.npmjs.org/glob/-/glob-8.1.0.tgz) | [LICENSE](licenses/kit-bundled/glob-8.1.0/LICENSE) |
| `hanji` | 0.0.5 | ISC | [package](https://registry.npmjs.org/hanji/-/hanji-0.0.5.tgz) | [declared text](licenses/ISC.txt); package notice absent |
| `heap` | 0.2.7 | MIT | [package](https://registry.npmjs.org/heap/-/heap-0.2.7.tgz) | [LICENSE](licenses/kit-bundled/heap-0.2.7/LICENSE) |
| `hono` | 4.13.13 | MIT | [package](https://registry.npmjs.org/hono/-/hono-4.13.13.tgz) | [LICENSE](licenses/kit-bundled/hono-4.13.13/LICENSE) |
| `inflight` | 1.0.6 | ISC | [package](https://registry.npmjs.org/inflight/-/inflight-1.0.6.tgz) | [LICENSE](licenses/kit-bundled/inflight-1.0.6/LICENSE) |
| `inherits` | 2.0.4 | ISC | [package](https://registry.npmjs.org/inherits/-/inherits-2.0.4.tgz) | [LICENSE](licenses/kit-bundled/inherits-2.0.4/LICENSE) |
| `json-diff` | 1.0.6 | MIT | [package](https://registry.npmjs.org/json-diff/-/json-diff-1.0.6.tgz) | [LICENSE-MIT](licenses/kit-bundled/json-diff-1.0.6/LICENSE-MIT) |
| `lodash.throttle` | 4.1.1 | MIT | [package](https://registry.npmjs.org/lodash.throttle/-/lodash.throttle-4.1.1.tgz) | [LICENSE](licenses/kit-bundled/lodash.throttle-4.1.1/LICENSE) |
| `minimatch` | 5.1.9 | ISC | [package](https://registry.npmjs.org/minimatch/-/minimatch-5.1.9.tgz) | [LICENSE](licenses/kit-bundled/minimatch-5.1.9/LICENSE) |
| `minimatch` | 7.4.9 | ISC | [package](https://registry.npmjs.org/minimatch/-/minimatch-7.4.9.tgz) | [LICENSE](licenses/kit-bundled/minimatch-7.4.9/LICENSE) |
| `ms` | 2.1.3 | MIT | [package](https://registry.npmjs.org/ms/-/ms-2.1.3.tgz) | [license.md](licenses/kit-bundled/ms-2.1.3/license.md) |
| `node-domexception` | 1.0.0 | MIT | [package](https://registry.npmjs.org/node-domexception/-/node-domexception-1.0.0.tgz) | [LICENSE](licenses/kit-bundled/node-domexception-1.0.0/LICENSE) |
| `node-fetch` | 3.3.2 | MIT | [package](https://registry.npmjs.org/node-fetch/-/node-fetch-3.3.2.tgz) | [LICENSE.md](licenses/kit-bundled/node-fetch-3.3.2/LICENSE.md) |
| `once` | 1.4.0 | ISC | [package](https://registry.npmjs.org/once/-/once-1.4.0.tgz) | [LICENSE](licenses/kit-bundled/once-1.4.0/LICENSE) |
| `pluralize` | 8.0.0 | MIT | [package](https://registry.npmjs.org/pluralize/-/pluralize-8.0.0.tgz) | [LICENSE](licenses/kit-bundled/pluralize-8.0.0/LICENSE) |
| `semver` | 7.8.5 | ISC | [package](https://registry.npmjs.org/semver/-/semver-7.8.5.tgz) | [LICENSE](licenses/kit-bundled/semver-7.8.5/LICENSE) |
| `sisteransi` | 1.0.5 | MIT | [package](https://registry.npmjs.org/sisteransi/-/sisteransi-1.0.5.tgz) | [license](licenses/kit-bundled/sisteransi-1.0.5/license) |
| `web-streams-polyfill` | 3.3.3 | MIT | [package](https://registry.npmjs.org/web-streams-polyfill/-/web-streams-polyfill-3.3.3.tgz) | [LICENSE](licenses/kit-bundled/web-streams-polyfill-3.3.3/LICENSE) |
| `wrappy` | 1.0.2 | ISC | [package](https://registry.npmjs.org/wrappy/-/wrappy-1.0.2.tgz) | [LICENSE](licenses/kit-bundled/wrappy-1.0.2/LICENSE) |
| `ws` | 8.22.0 | MIT | [package](https://registry.npmjs.org/ws/-/ws-8.22.0.tgz) | [LICENSE](licenses/kit-bundled/ws-8.22.0/LICENSE) |
| `zod` | 3.25.76 | MIT | [package](https://registry.npmjs.org/zod/-/zod-3.25.76.tgz) | [LICENSE](licenses/kit-bundled/zod-3.25.76/LICENSE) |
