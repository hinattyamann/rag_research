# Phase11 v32専用Checkoutの実再現証拠

記録時間: 2026-10-27 23:21 JST。対象は再現証拠の正式出版時点（2026-10-27 23:17:48 JST）。

[正式Manifest](../data/manifests/phase11_v32_checkout_reproduction_v1.json)と[Hash](../data/manifests/phase11_v32_checkout_reproduction_v1.sha256)を実発行し、Rootの独立postcheckが48成果・884資産・25 alias・31 immutable・44独立コピーを照合した。Manifest SHA256は `9bab37b7921713e6b8cf645ed9cdb970d6780d5416f5fc76c3f99c590bd0891a`。実再現は成功したが、この証拠単体は実GPU Contextの健康・Kernel安定性、形式/意味採用、Gate11通過を立証しない。Phase12は開始していない。

- 固定Commit: `81563f7aefe0ca3a659ba0677a74d6d71e05d1bd`。Rootが通常Push・Remote先端一致・cleanを確認して新専用WTを作成した。
- 候補Identity: `73d9ac7d429e11129a8c5faceee6d8d50a48b196ccea3d45b85fc631f10512af`。[正式事前登録](../data/manifests/phase11_semantic_v32_preregistration_v1.json) SHA `09236fcae9807a780eb175312ed8c2774b01843973defc05f3ae078be09bea1f`。
- 科学上の親はv31 `dbb983…`。変更はJudgeのJSONキー提示順だけで、他5 Identity成分・Core94・全本文/Expected/基準は不変。人工Tokenizer11/形式10の実証拠はv30 `87cf5942…` の元ID/contextを保持する。旧意味出力の再利用は0。
- 親781資産・19 aliasを保全して884資産・25 aliasへ閉じ、31 immutableは親の実Hash来歴・stat・同inodeを条件にhardlinkした。mutable/旧Run/aliasは実コピー前→target→後Hashと独立inodeを確認。今回コピーで重い不変資産を再Hashせず、コピー後の実loaderが現8B GGUF/Runtimeを一回実Hashした。
- 新専用uv環境は58 packages。実`load_config`/`build_identity`で全Identity・Core94・固定39 QA/45文/78条件/90 Call契約、FAoff設定を確認した。生成・server・render/tokenize・明示GPU列挙は0、全禁止count0。固定診断の必要parseと未使用Main/Cal/Evaluation本文を区別し、後者のopenは0。

## 時系列と費用の範囲

実コピー→専用uv→実loader→正式再現出版の後に、初認可・最初のPlan・実験へ進む。PublisherがRootと新WTの全5段階出力/supervision/Plan及び初認可、計32予定pathを出版の初回と正式write直前にstatし、全不存在を保存した。これは出版時点の観測であり将来namespaceを予約する証明ではない。v31の「初Plan生成が正式出版より先」という履歴をv32へ流用していない。

|成分|内部・独立child実測（秒）|別の観測|
|---|---|---|
|資産コピー|内部1.303328857990、child1.332681261003|tool wall未記録/null|
|専用uv同期|child0.066544150002|installer報告30 ms、tool wall未記録/null|
|生成0のloader/Identity|内部5.022870994057、child5.131218316965|tool wall未記録/null|
|正式出版|write前成分0.689635131042、child0.789452426019|tool wall0.751716019|
|独立postcheck|0.052263359074|48成果・44コピー、全禁止count0|
|実行証拠の独立保存|コピー成分0.006054605008、CPU0.004557724|summary/seal作成前まで|

内部・child・tool・installerの観測を合算しない。全再現wall、電気代、AI評価の実際の金額は未計測/null。v31 Hostscan/初loader失敗・修復費用は親履歴として保存し、新v32失敗・新費用へ再ラベルしない。今回Manifestの新v32 CPU失敗証拠は空配列である。

## 出版・独立保存

Root実Publisherはtool chunk `522076` のexit0、独立postcheck `eefc2b` は成功。参照先7個のpathだけを同SHAのcanonical/labへ移した別actual releaseを使い、sealed原releaseを保持した。内部再計算222 bindingは今回の実配列から算出・照合した値で、旧v31の固定値ではない。`canonical_preparation_inventory` と `complete_reproduction_receipt_files_sha256`（progress1個）を維持した。

[実出版/検算とSource準備の独立保存](../data/runs/lab/phase11-v32-checkout-reproduction-publication-execution-preservation-v1/summary.json)は22コピー、全25成果＋[封印](../data/runs/lab/phase11-v32-checkout-reproduction-publication-execution-preservation-v1/SHA256SUMS) SHA `9efb53a71fa13dce5ec12e249a86fb057f1854b9ca597e41778ec2f9f0faf9b2`。原本の前後Hash/stat不変、全コピーのinode独立、正式Manifest bytes不変を確認した。保存作業はWT stat/body・Model/Runtime・Raw本文・QA・台帳・Native0、追加test0。

Source準備では資産3入口の必要差分9 test（0.04秒）、Publisher差分12 test（0.05秒）・Ruff・pending早期拒否に通過し、不変17/11関数のASTを根拠に旧検証を再利用した。人工通過例を実意味採用へ代用していない。AI担当は `/root` と `/root/assets_v25`、human_reviewed/history_isolated=false、履歴fork=all。6.1 Sol 極高はユーザー申告で、厳密な実行Model識別子は取得できずnull。

次はRootが別証拠として新90入力のGPU/token収容0、NS/C、Rewrite品質、全90全文/thinking監査、新鮮Known20の元84 Callを順に閉じる。実採用後だけ元Main/予約Cal・最終規則/Validator/Manifest/Hash/Gate11へ進み、Phase12は開始しない。
