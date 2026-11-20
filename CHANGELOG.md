# Changelog

## v1118.1 · 2026-11-18

### 中文

新增 Epic `27.1.0+2505117` 的原生适配，修复新版 Epic DLL 被送入 Steam 适配器后报 `PE_layout` 的问题。Steam 和 Epic 继续共用一个 EXE。已核对 Epic 样本的指纹、布局和接口，样本可加载。Epic 完赛仍待完整安装环境复测。Steam 27.1.0 已通过原生完赛复测。

### English

Adds a native adapter for Epic `27.1.0+2505117` and fixes the `PE_layout` error caused by selecting the Steam adapter for this Epic build. Steam and Epic still use one EXE. The supplied Epic DLL passed fingerprint and interface checks and loaded on Windows. A complete match on a full Epic installation still needs confirmation. Steam 27.1.0 passed a complete native match in regression testing.

## v1118 · 2026-11-18

### 中文

相比 v1114，本次更新适配 **Steam FM27 27.1.0+2505117**。新版保存的生涯存档可以读取阵容、两阶段战术和自定义定位球。原版引擎也已重新验证了旧档对战、FMF 导入导出、战术执行力和 AI 战术生成。

- **角色、球队指令和个人指令实验室**。从战术板点「实验室」，选一个首发位置的角色，或选一项球队／个人指令，批量比较可用候选。原战术和候选共用对手、主客场和种子，筛出的候选可以换种子再测。原有属性实验室也能从这里进入，存档实验可跨联赛选对手。
- **自动挑选阵容**。在「一线队／比赛名单」里点「自动挑选」，按有球和无球两个阶段的位置熟练度、球员能力安排首发，并兼顾替补的位置覆盖。
- **比赛重要性**。自由推演和存档对战共用预设，默认普通联赛，也可以自定义 1–20。手动战术执行力面板说明了战术理解总分和八个区域的关系。
- **联赛测试和结果**。运行前可看到预计场数。「跑一圈联赛」默认对每个对手主客各一场，可加第二轮复测。详细模式提供整批进球榜和助攻榜，可按对照战术、本次战术和球队查看。
- **并行启动修复**。原生宿主依次完成激活，激活后并行比赛。启动超时会单独提示，已完成的场次可继续接着跑。

新版曼联档和旧版佛罗伦萨档均通过原生主客场测试。Steam 玩家更新工具后，在「存档对战」里重新点一次「读取存档」。统一 EXE 仍含原有 Epic 适配器，本轮原生验证覆盖 Steam。启动窗口会显示内部构建号 v1115。

### English

Compared with v1114, this release supports **Steam FM27 27.1.0+2505117**. It reads squads, both tactical phases, and custom set pieces from career saves written by the updated game. Native checks also covered older saves, FMF import and export, tactical execution, and AI tactic generation.

- **Role, Team Instruction, and Player Instruction Labs.** Open Labs from the tactics board to test available roles for a starting position, or alternatives for a single team or player instruction. The baseline and variants share opponents, venues, and seeds. Shortlisted variants can be retested with fresh seeds. The existing Attribute Lab is available from the same menu, and career-save experiments can use opponents from multiple leagues.
- **Auto-pick the match squad.** The lineup picker uses each player's ability and positional familiarity in and out of possession, with positional coverage on the bench.
- **Match importance.** Free Simulation and Save Matchups share the same presets. The default is an ordinary league match, and custom values range from 1 to 20. The manual tactical execution panel also clarifies how the overall tactical understanding setting relates to the eight tactical areas.
- **League tests and results.** See the estimated match count before running. The league shortcut schedules one home and one away match per opponent by default, with an optional retest. Detailed Save Matchups include batch goal and assist leaderboards for either tactic and team.
- **Parallel startup fixes.** Native workers activate one at a time and run matches in parallel once ready. Activation timeouts are reported separately, and completed matches are retained for resume.

Home and away native matches passed with a new Manchester United save and an older Fiorentina save. Steam users can re-import their save after updating. The unified EXE also includes the existing Epic adapter. This compatibility round was verified on Steam. The startup window shows the internal build number v1115.

## v1115

- 各路原生宿主依次激活，激活成功后照常并行比赛。激活超时会单独提示，已完成场次可以接续。
- 对齐存档对战的「两轮测试」复选框，勾选后显示第二轮每队场数。
- 在手动执行力面板标明战术理解的设置用于总分，八个区域仍由引擎计算。
- 自由推演和存档对战共用比赛重要性预设，默认普通联赛。自定义可填 1–20，开赛前核对双方首发实际使用的值。
- 把比赛设置、A/B 对照和预计总场数放到运行按钮附近。跑一圈联赛默认每个对手主客各一场，确认时可单独加复测。历史结果显示实际采用的条件和统计轮次。
- 存档对战完整模式新增整批进球榜和助攻榜。按存档球员合并主客场数据，分别查看对照方案、本次方案、己方和对手。
- Activate native workers one at a time and run matches in parallel once ready. Report activation timeouts explicitly and keep completed matches available for resume.
- Align the two-round checkbox and show the round-two match count when enabled.
- Clarify that the manual tactical understanding setting changes the overall score. The engine calculates the eight tactical areas.
- Add shared match importance presets to Free Simulation and Save Matchups. Default to the league preset and allow a custom value from 1 to 20. Verify the value for every starter before kick-off.
- Place match settings, A/B tactics, and the estimated match count by the Run button. The league shortcut defaults to one home and one away match per opponent, with optional retesting. Results show the settings used and the scope of each round's statistics.
- Add batch goal and assist leaderboards to detailed Save Matchups, combining home and away counts by save player identity and showing A/B and team scopes.

## v1114 · 2026-11-14

- Add Attribute Lab to the tactics board. Test one attribute at a time for selected starters, retest on fresh seeds, and export an HTML report. Pick up to 120 available career-save opponents and mix clubs from the five major leagues in one batch. The main EXE includes the feature from PR #18.

- Read save-specific player display names and registered shirts, including active loans; bind opposition instructions and historical events to player identity.
- Select clubs and opponents across the loaded top five leagues using current-season membership.
- Add independent screening/retest rounds, per-round results and CSV fields, opposition neutralization, and cancellation/resume validation.
- Resolve first-team coach references and reject unavailable or unverifiable AI opponents.
- Read additional saved tactic, lineup and set-piece layouts. A club with an unverifiable coach no longer blocks the opponent list. Skip stored substitutes whose player identity cannot be verified when loading the current tactic board.
- Preserve completed work when Windows temporarily blocks summary replacement and discard stale squad/opponent responses.
- Fix the opponent-picker click handler, remap personal instructions when replacing a roster, and keep paired A/B statistics scoped to the active round.
- Preserve unbound legacy roster drafts on startup, clear player-specific overrides when changing saves, and retain the original fixture identity in retest summaries.
- Include product, backup-boundary and portability documentation. Full user-data backup/restore remains planned.
- Ship a single Tauri Windows EXE for Steam and Epic with pipe-based backend communication, selectable data folders, fixed and random seeds, and online fantasy draft save support.

## v1113.1 · 2026-11-13

- Register the save layout for `27.0.1+2503222`.
- Record native tactical execution at the original roster identity and report specific verification mismatches.
- Retain startup diagnostics even if the backend exits without output.
- Verified with a Manchester United save, 19 same-league opponents and 38 completed native matches with tactical execution enabled.

## v1113 · 2026-11-13

- Adapt the original-engine host to the FM27 Steam hotfix `27.0.1+2503222`, including its updated initialization address and compatibility checks.
- Validate the packaged build with complete native matches, tactical execution, worker reuse and FMF import/export.

## v1112 · 2026-11-12

- Keep each supported native worker alive until its assigned batch lane finishes instead of recycling after 64 matches. Release the original match, recording references, event observer and thread context after every match.
- Install execution trampolines once per process and reset policies, team bindings, CA receipts and counters for every match. Execution and random-pool A/B batches now reuse workers too.
- Negotiate the counted-session protocol by host identity; older hosts retain the previously verified 64-match/isolated-execution behavior. Keep per-match progress timeouts, cancellation and periodic disk-space checks.
- Let users enter 1–256 concurrent workers directly and preserve their choice. CPU and free-memory estimates only set the default recommendation (up to four); they do not cap manual choices. Counts above the recommendation display a nonblocking resource warning. Higher counts than eight have not been benchmarked.
- Validation: 160 matches in one process matched cold-worker scores, statistics and execution receipts; mixed execution transitions matched full events; three-preset execution A/B cancel/restart/resume passed. A fixed 48-match quick-mode trial took 51.687 / 34.859 / 26.468 seconds at 4 / 6 / 8 workers, with identical results and about 332 MiB peak private memory per native process. These are local measurements, not universal speed guarantees.
- Same-process multi-threaded simulation remains a separate research prototype and is not exposed by this release.


## v1111.2 · 2026-11-11

- Move random opponent tactics into the match run controls and remove the standalone away-pool sidebar page.
- Enable the option to open candidate import, weights and uniform-attribute settings; closing the settings retains the enabled state, while disabling randomization retains candidates and weights.
- Rename save-library import to Add random candidates, without enabling randomization automatically.
- Keep empty-candidate setup local and prevent starting a random match until candidates are added.
- Preserve the existing pool format, per-seed draws and tactical-execution integration; update Chinese and English copy.


## v1111.1 · 2026-11-11

- Integrate PR #3 with the v1111 official FM27 27.0.1+2494687 adapter.
- Browse loaded leagues and read league/country names from local game data.
- Generate original-engine AI plans for opponents in the managed league, with club-home/club-away contexts, progress, caching and retry.
- Export verified FMF plans and import mixed generated/preset plans into the away pool without silently dropping teams.
- Invalidate derived plans when engine identity changes and preserve missing-coach restrictions.
- Retain v1111 save-layout, tactic auxiliary-map, TEAM-count discovery and tactical-execution compatibility fixes.
- AI generation uses current squads, fixed seed 0 and the default player-side template; imported pool plans are static.
- Validation on a 27.0.1 Manchester United save: 19 opponents; 36 generated plans plus one fallback preset exported/imported; one unavailable secondary preset explicitly reported. HIGHWAY STAR FMF round-trip passed. Three complete native matches passed, including one using the final bundled runtime. Automated checks: 145 passed, one Windows symlink skip; i18n and EXE self-test passed.


## v1109.3 · 2026-11-09

- Allow random away tactic pools with experimental tactical execution.
- Isolate every execution match and verify native ability contribution, actual roster identity, CA, and manual component scores.
- Recheck execution receipts against the original drawn inputs when resuming.
- Preserve current squads and automatic CA/role ability calculation across pool expansion.
- Validation: 28 accepted native matches with three opponent presets, same-seed A/B, actual cancel/restart/resume, independent replays, CA and role-suitability changes, and the combined UI flow; zero unexpected failures. Automated checks: 72 passed, one Windows symlink-permission skip. These checks establish functional input handling, not tactical superiority.

## v1109.2 · 2026-11-09

- Follow the Windows display language in the interface and system tray, with Simplified Chinese and English support.
- Merge the weighted away tactic pool and same-league preset library from PR #2.
- Count one shared A/B opponent draw per seed and preserve replayed draws when resuming.
- Select active or upcoming complete league schedules first, with a 90-day limit for preseason and postseason tables.
- Integrate the v1109.1 save-header, named set-piece, split tactical-effectiveness and bounded large-save fixes.
- Retain separate disk budgets for save import, preparation and batch simulation, with the actual data path in errors.


## 未发布

- 新增真实AI战术批量生成：读取每队现任主教练、当前阵容和你自己的主教练，用本机原版引擎做 0 tick 对局准备并回读完整双阶段战术；每个对手生成对手主场/对手客场两套（列表显示为「球队主场战术/球队客场战术」）并直接替换第1/2套，支持进度条、并行生成与缓存增量补齐；缓存绑定引擎与生成协议身份，引擎或适配器变化后失效重生成；导出与导入客队战术池按球队/变体合并真实战术与可用预设并报告遗漏，空库不再阻断预设导出。
- 客队战术池统一属性核对：开启统一属性时，每名首发在战术位置的熟练度固定为满 20，其余属性统一为可配置面板值（默认 15），并在展开后核对。
- 重新设计存档战术导出：可从存档中任意已载入联赛导出对手战术，每位主教练按主/次偏好阵型各生成一套原装预设，文件按「俱乐部-教练-第x套战术」命名并平铺写入导出目录。
- 联赛与国家名称改为读取本机 FM27 游戏数据库（lang_db.dat），并按存档 ID 交叉校验；读取失败时回退到联赛编号。
- 客队战术池导入不再去重，支持重复加入同一套战术；池上限调整为 128 套。
- 重新设计「存档战术」与「客队战术池」页面：联赛选择、球队/教练/两套战术表格、导出与导入主流程，移除旧页面冗余控件。
- 存档战术页的联赛与国家名称跟随界面语言显示中文或英文（读取 FM27 游戏数据库的中文名称表）；同一联赛只列出一条，自动选择进行中或最近的赛程。
- 联赛教练偏好改为直接读取一线队教练分配，不再依赖仅对部分存档可用的球队表；一线队主教练空缺的球队明确标记为不可用。
- 新增存档战术页面：识别存档后按当前联赛浏览除玩家以外的教练偏好预设战术，可导出到本机文件夹或一键导入客队战术池。
- 客队战术池改为侧边栏独立页面，支持导入本机 FMF 或从存档页面导入联赛对手预设；底栏快速模式旁新增随机模式开关，按权重逐场抽取客队战术。
- 统一客队球员属性只统一能力属性，首发按抽中战术的对应位置获得最高位置熟练度，避免此前整队位置熟练度统一为 15 后明显变弱。
- 修复赛季结束后读取存档时无法识别当前联赛、导致存档战术页面提示教练偏好读取失败的问题。

## v1108.5 — 2026-11-08

- Import career saves, edit match squads and run home and away matches against selectable same-league opponents.
- Preview both tactical phases using presets matched to the head coach's saved preferences.
- Preserve position settings when swapping players, correct Chinese transition labels and add experiment management.
- Add optional manual tactical effectiveness settings for both sides.

## v1106 — 2026-11-06

- Add actual interface screenshots to both player guides.
- Serve `engine-settings.js` from the static route allowlist so engine diagnostics and manual path selection initialize correctly. The v1103.2 release is retained. New desktop builds display v1106 and self-test the engine settings endpoint.

## v1103.2 — Public release

- Publish FM Tactics Lab under MIT with Chinese and English player documentation.
- Release the original `FM27战术推演_v1103.2.exe`, unchanged.
- Publish the corresponding desktop application payload and native adapter sources.
- Include double-phase tactics, player input editing, set pieces, batch comparison, original match statistics and full/quick collection modes.
- Include graded engine compatibility and manual game-path selection.
- Keep career-save versus modules in later development versions.
- Add standalone source preparation, build and export scripts. Local initial inputs can be read from the verified release EXE.
