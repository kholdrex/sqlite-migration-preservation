# RQ4 rerun comparison

Observed 2026-11-02T13:06:08.728287+00:00; completed 2026-11-02T13:14:30.811359+00:00.

All 93 pinned attempts were compared with the original run. 0 differ in a compared outcome field; the aggregate counts are the same.

70 replayed; 23 unreplayable. 20 qualifying parent rebuilds in 20 repositories (16 distinct migration hashes); 43 controls.

| Path | Preserved | Silent loss | Loud | Unreplayable |
| --- | ---: | ---: | ---: | ---: |
| drizzle | 25 | 20 | 25 | 23 |
| raw | 43 | 13 | 14 | 23 |
| raw-tx | 29 | 24 | 17 | 23 |

Qualifying migrations only:

| Path | Preserved | Silent loss | Loud |
| --- | ---: | ---: | ---: |
| drizzle | 0 | 15 | 5 |
| raw | 13 | 4 | 3 |
| raw-tx | 0 | 17 | 3 |

Fields that differ between the runs: 0.

All 152 replay quantities of the paper have the same value in both runs. The paper's adjudication excludes the intentionally superseded `activity_events_org_id_idx` index in `saltbo/zpan` / `0054_lively_nuke.sql`. After that same adjudication, silent-loss counts are 19 Drizzle, 12 raw and 23 raw-tx (unadjudicated: 20, 13 and 24). Among qualifying migrations, 11 change from Drizzle silent loss to raw preservation and 4 remain silent loss.

Published gzip evidence: 2,256,142 bytes in 93 artifacts. License split: 25 full, 68 redacted repositories.

Recorded labels: AGPL-3.0: 14, Apache-2.0: 6, BSD-3-Clause: 1, EUPL-1.2: 1, GPL-3.0: 5, MIT: 18, NOASSERTION: 4, null: 44.

Complete before/after snapshots exist for every executed target path. For an unexecuted path, the record contains the failure reason and any available setup trace. Schema provenance in restricted artifacts is a conservative DDL dependency set stored once under `schema_sources`; `sources_ref: #/schema_sources` resolves to byte/line positions in pinned files. It is not a minimal schema derivation.

Original row identities cannot be compared because the original snapshots were not retained. The comparison checks every original finding (including retained synthetic row differences), qualification, seed count, outcome, lost table, missing row count and after count. SQLite callback traces and submitted statements are distinguished as described in the protocol.

The published artifacts hold 210 executed target paths with 420 snapshots, 3243 trace callbacks and 1865 submitted project statements; 69 paths did not execute.

## Migration-by-migration comparison

Each row reports the rerun result; `same` means all compared fields match the original. Loss cells list missing rows by table and tables whose values differ from the reference. A value difference can reflect a failed migration; the path outcome remains authoritative.

| Repository / migration | Qualification | Drizzle | Raw | Raw-tx | Comparison |
| --- | --- | --- | --- | --- | --- |
| dakohhh/cf_ai_speakscribe / `migrations/0005_fat_nightcrawler.sql` | parent | silent-loss; missing rows: speakerTurn=3; values: speakerTurn | preserved | silent-loss; missing rows: speakerTurn=3; values: speakerTurn | same |
| CinatitBR/usp-acessivel-backend / `migrations/0001_aberrant_randall_flagg.sql` | parent | loud | loud | loud | same |
| DynacomSolutions/Cloudwarden / `migrations/0005_organizations.sql` | control | preserved | preserved | preserved | same |
| CrashVibe/FGateNexus / `migrations/0002_broken_eternity.sql` | parent | silent-loss; missing rows: player_server=3, target=3; values: player_server, target | silent-loss; missing rows: player_server=3, target=3; values: player_server, target | silent-loss; missing rows: player_server=3, target=3; values: player_server, target | same |
| loadchange/cherry-lite / `migrations/sqlite-drizzle/0001_tan_cerise.sql` | parent | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | preserved | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | same |
| Vinay-786/reviewsite / `migrations/0001_premium_prima.sql` | control | preserved | preserved | preserved | same |
| CMD-world/platform / `migrations/0004_busy_lethal_legion.sql` | replayed | loud; values: apiKey | loud | loud; values: apiKey | same |
| DrOlu/SuperAgent / `migrations/sqlite-drizzle/0001_tan_cerise.sql` | parent | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | preserved | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | same |
| hb-robo/theshelf.blog / `migrations/0001_rainy_starjammers.sql` | control | loud; values: media_items, reviews | loud; values: reviews | loud; values: media_items, reviews | same |
| shanuflash/laddr / `migrations/0003_melted_cassandra_nova.sql` | parent | silent-loss; missing rows: match=3, match_event=3, match_game=3, match_slot=3, participant=3, roster_member=3, stage=3, stage_group=3, standing=3, tournament_member=3, veto_action=3, veto_session=3; values: match, match_event, match_game, match_slot, participant, roster_member, stage, stage_group, standing, tournament_member, veto_action, veto_session | preserved | silent-loss; missing rows: match=3, match_event=3, match_game=3, match_slot=3, participant=3, roster_member=3, stage=3, stage_group=3, standing=3, tournament_member=3, veto_action=3, veto_session=3; values: match, match_event, match_game, match_slot, participant, roster_member, stage, stage_group, standing, tournament_member, veto_action, veto_session | same |
| pitzzahh/powertrackr / `migrations/20260307051734_youthful_mongu/migration.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| XeinTDM/MeatFlicks / `migrations/0001_unique_ghost_rider.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| CherryHQ/cherry-studio / `migrations/sqlite-drizzle/0001_tan_cerise.sql` | parent | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | preserved | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | same |
| ncvyn/adu-tutor / `migrations/0001_good_mister_fear.sql` | parent | loud; values: user | preserved | silent-loss; missing rows: account=3, session=3; values: account, session | same |
| saltbo/zpan / `migrations/0054_lively_nuke.sql` | control | silent-loss | silent-loss | silent-loss | same |
| choyiny/saasmail / `migrations/0017_windy_sister_grimm.sql` | control | preserved | preserved | preserved | same |
| Doezer/Questarr / `migrations/0007_broad_hannibal_king.sql` | parent | silent-loss; missing rows: game_downloads=3, xrel_notified_releases=3; values: game_downloads, xrel_notified_releases | preserved | silent-loss; missing rows: game_downloads=3, xrel_notified_releases=3; values: game_downloads, xrel_notified_releases | same |
| realchendahuang/FlareMo / `migrations/0022_violet_raza.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| alteran-social/alteran / `migrations/0005_odd_bishop.sql` | control | preserved | preserved | preserved | same |
| flyaltitudeapp/altitude / `migrations/0026_daffy_plazm.sql` | parent | silent-loss; missing rows: accounts=3, event_aircraft=3, event_gates=3, event_participants=3, events=3, leave_requests=3, pirep_events=3, pireps=3, sessions=3; values: accounts, event_aircraft, event_gates, event_participants, events, leave_requests, pirep_events, pireps, sessions | preserved | silent-loss; missing rows: accounts=3, event_aircraft=3, event_gates=3, event_participants=3, events=3, leave_requests=3, pirep_events=3, pireps=3, sessions=3; values: accounts, event_aircraft, event_gates, event_participants, events, leave_requests, pirep_events, pireps, sessions | same |
| xerosanyam/remfo / `migrations/0004_bouncy_venus.sql` | control | preserved | preserved | preserved | same |
| Shiinama/next-cloudflare-template / `migrations/0009_clever_fallen_one.sql` | parent | loud; values: posts | preserved | silent-loss; missing rows: postTranslations=3; values: postTranslations | same |
| skyfallwastaken/at-channel / `migrations/0001_flimsy_zzzax.sql` | control | preserved | preserved | preserved | same |
| SocksTheWolf/SkyScheduler / `migrations/0010_smiling_namorita.sql` | control | loud | loud | loud | same |
| JackTheButler/JackTheButler / `migrations/0007_slow_morph.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| mst-mkt/diggraph-anime / `migrations/0004_abnormal_titania.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| raffaele-lungarella/appointment-scheduler / `migrations/0002_tired_betty_brant.sql` | control | preserved | preserved | preserved | same |
| kdleonard93/creatures-of-habit / `migrations/0002_sharp_abomination.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| rt8digital/opensauce-pos / `migrations/0010_striped_ghost_rider.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| codechefPesuecc/CodeChef-PESUECC-Chapter / `migrations/0010_sparkling_stephen_strange.sql` | control | preserved | preserved | preserved | same |
| bradymholt/snoozer / `migrations/0003_green_ink.sql` | control | preserved | preserved | preserved | same |
| franciscolopesdev/KitchenOS / `migrations/0002_marvelous_warpath.sql` | control | preserved | preserved | preserved | same |
| rayhanadev/personal-website-v8 / `migrations/0001_milky_scarlet_spider.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| 501A-gh/hence / `migrations/0001_curved_xorn.sql` | replayed | loud | preserved | loud | same |
| heysubinoy/nimbus-frontend / `migrations/0002_motionless_nightmare.sql` | control | loud | loud | loud | same |
| Alfredoeb9/ele / `migrations/0002_uniqueUserRecord.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| Ghaith4230/drivingWebapp / `migrations/0006_last_black_widow.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| vaibhavrxj/-vaibhav-asset-intelligence / `migrations/0001_windy_blizzard.sql` | control | preserved | preserved | preserved | same |
| realmroot/realmroot / `migrations/0030_agent_management_actor.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| h-jennings/text-embeddings-prototype / `migrations/0001_purple_gambit.sql` | control | preserved | preserved | preserved | same |
| eremiltonribeiro/VehicleTracker / `migrations/0001_init.sql` | replayed | loud | loud | loud | same |
| sagyzdop/meriksirat / `migrations/0004_setup.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| dadezzz/events-cash-register / `migrations/0010_curvy_phalanx.sql` | parent | loud; values: order, product | loud; values: product | loud; values: order, product | same |
| b0sc/api / `migrations/0004_burly_thing.sql` | control | loud; values: user | preserved | preserved | same |
| yassine-safraoui/job-offers-monitor / `migrations/0001_simple_klaw.sql` | replayed | loud | loud | loud | same |
| aryanjain2005/ueta_web / `migrations/0004_rapid_malice.sql` | control | loud | loud; values: users | loud | same |
| trevclev0/terminal-quiz / `migrations/0003_melodic_jane_foster.sql` | parent | silent-loss; missing rows: gates=3; values: gates | silent-loss; missing rows: gates=3; values: gates | silent-loss; missing rows: gates=3; values: gates | same |
| tijptjik/hype / `migrations/0007_capabilities.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| Kwaraz/scrapyard / `migrations/0001_loose_iron_fist.sql` | control | loud; values: scams | silent-loss; missing rows: scams=3; values: scams | silent-loss; missing rows: scams=3; values: scams | same |
| aryan-79/gator / `migrations/0001_lame_hex.sql` | control | preserved | preserved | preserved | same |
| saltbo/zme / `migrations/20260804164145_strange_chimera.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| myers268/wedding-site / `migrations/0005_many_rage.sql` | control | loud; lost tables: party; values: guest, party | silent-loss | silent-loss | same |
| noelserdna/colonias-felinas / `migrations/0008_fotos_r2.sql` | control | preserved | preserved | preserved | same |
| BB-84C/opencode-cost-observatory / `migrations/0001_glorious_dreaming_celestial.sql` | control | preserved | preserved | preserved | same |
| BatthewZ/cadence-public / `migrations/0016_shocking_kabuki.sql` | parent | silent-loss; missing rows: task_attachment=3; values: task_attachment | preserved | silent-loss; missing rows: task_attachment=3; values: task_attachment | same |
| marceldobehere/goofy-media-back / `migrations/0014_cultured_hellion.sql` | control | preserved | preserved | preserved | same |
| Ch3mson/personal-portfolio-v2 / `migrations/0001_swift_brood.sql` | control | silent-loss; missing rows: posts=3; values: posts | silent-loss; missing rows: posts=3; values: posts | silent-loss; missing rows: posts=3; values: posts | same |
| dylanreedx/schoolOS / `migrations/0001_pale_post.sql` | parent | silent-loss; missing rows: classes=3, study_sessions=3; values: classes, study_sessions | silent-loss; missing rows: classes=3, study_sessions=3; values: classes, study_sessions | silent-loss; missing rows: classes=3, study_sessions=3; values: classes, study_sessions | same |
| VesperQuartz/payhub / `migrations/0009_violet_black_tarantula.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| M4YAVI/portfolio / `migrations/0004_silky_talon.sql` | replayed | loud; values: goals | preserved | preserved | same |
| syahrulfadli/kanban-app / `migrations/0016_mushy_martin_li.sql` | control | silent-loss | silent-loss | silent-loss | same |
| Kavehrafie/pucked / `migrations/0001_lean_wither.sql` | parent | loud | loud | loud | same |
| fanthpl/payment-router / `migrations/0002_cooing_inertia.sql` | control | preserved | preserved | preserved | same |
| tropicbliss/mobiling / `migrations/0003_amusing_redwing.sql` | control | loud | loud | loud | same |
| Ankit-Maurya-12223197/Ai-Powered-Inventory / `migrations/0001_windy_blizzard.sql` | control | preserved | preserved | preserved | same |
| MiaAI-Lab/mia-chat / `migrations/sqlite-drizzle/0001_tan_cerise.sql` | parent | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | preserved | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | same |
| srvo/saasmail / `migrations/0017_windy_sister_grimm.sql` | control | preserved | preserved | preserved | same |
| hwiseongahn/portfolio-sitev2 / `migrations/0001_swift_brood.sql` | control | silent-loss; missing rows: posts=3; values: posts | silent-loss; missing rows: posts=3; values: posts | silent-loss; missing rows: posts=3; values: posts | same |
| wujianguo/zpan-demo / `migrations/0045_soft_outlaw_kid.sql` | control | preserved | preserved | preserved | same |
| belliod/flaremo / `migrations/0022_violet_raza.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| jtk5aw/committed / `migrations/0004_reflective_argent.sql` | control | loud | loud | loud | same |
| bhirmbani/notex / `migrations/0006_retire_project_userid.sql` | parent | silent-loss; missing rows: contexts=3, entity_links=3, files=3, grants=3, mermaid_diagrams=3, notes=3, repositories=3; values: contexts, entity_links, files, grants, mermaid_diagrams, notes, repositories | preserved | silent-loss; missing rows: contexts=3, entity_links=3, files=3, grants=3, mermaid_diagrams=3, notes=3, repositories=3; values: contexts, entity_links, files, grants, mermaid_diagrams, notes, repositories | same |
| cjpais/dumpster / `migrations/0001_dazzling_alex_wilder.sql` | control | preserved | preserved | preserved | same |
| ree-jp-univ/agri-api / `migrations/0003_mean_masked_marvel.sql` | control | preserved | preserved | preserved | same |
| glitchassassin/freedom-seed / `migrations/0002_careless_killraven.sql` | control | loud; lost tables: team_invitations, team_members, teams; values: team_invitations, team_members, teams | silent-loss | loud; lost tables: team_invitations, team_members, teams; values: team_invitations, team_members, teams | same |
| kuranai/dovari / `migrations/0009_aromatic_the_order.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| kuranai/kuranai-com / `migrations/0009_aromatic_the_order.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| jeremy93-2008/Brioche-Forms / `migrations/0001_motionless_madrox.sql` | replayed | loud | loud | loud | same |
| KeeghanM/SpotSpot / `migrations/0002_keen_piledriver.sql` | control | preserved | preserved | preserved | same |
| columk1/threads-clone / `migrations/0002_gray_molly_hayes.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| SeanHolt/nextjs-blog / `migrations/0003_magenta_gamora.sql` | control | loud; values: blogs | preserved | preserved | same |
| sovereignfs/sovereign-plugin-shopper / `migrations/sqlite/0002_calm_molly_hayes.sql` | control | preserved | preserved | preserved | same |
| yawarpwn/hono-tell-api / `migrations/0004_slimy_callisto.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| dynamicagents/slack-gatekeeper / `migrations/0004_agents_endpoint_notnull.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| TheHyphen/bots / `migrations/0003_blushing_polaris.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| JMRhodes/quizzle-server / `migrations/0002_bent_may_parker.sql` | control | silent-loss | silent-loss | silent-loss | same |
| modecode22/required-books-api / `migrations/0001_safe_ultimatum.sql` | control | preserved | preserved | preserved | same |
| radiumcoders-alt/order-management-system / `migrations/0002_light_franklin_storm.sql` | control | loud; lost tables: coils, orders, wires; missing rows: coils=3; values: coils, orders, wires | preserved | preserved | same |
| vlbin/glint / `migrations/0003_loving_proemial_gods.sql` | replayed | loud; values: direct_messages, friendships, posts, users | silent-loss | loud; values: direct_messages, friendships, posts, users | same |
| DOOduneye/portfolio / `migrations/0008_odd_shadow_king.sql` | unreplayable | unreplayable | unreplayable | unreplayable | same |
| ffeew/job-application-assistant / `migrations/0003_tranquil_hawkeye.sql` | control | loud | loud | loud | same |
| julesmeister/orbitandchill / `migrations/0002_peaceful_marvel_boy.sql` | parent | silent-loss; missing rows: discussion_tags=3; values: discussion_tags | silent-loss; missing rows: discussion_tags=3; values: discussion_tags | silent-loss; missing rows: discussion_tags=3; values: discussion_tags | same |
| leappower/cherry-studio-managed / `migrations/sqlite-drizzle/0001_tan_cerise.sql` | parent | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | preserved | silent-loss; missing rows: agent_channel_task=3; values: agent_channel_task | same |
