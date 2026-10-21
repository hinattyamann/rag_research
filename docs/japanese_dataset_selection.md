# Phase 11 日本語Datasetの候補比較とSource選定

確認日: 2026年10月21日。工程は[ロードマップ](research_roadmap.md)、選定基準と実行計画は
[日英比較方針](english_japanese_expansion.md)による。以下はSource選定であり、最終条件凍結ではない。

## 1. 選定したSource

**`baobab-trees/wikipedia-human-retrieval-ja`をPhase 11の日本語Sourceに選定する。**
固定Revisionは`02e85c83a64f345aee62fba3a35af99c075a331f`。
[配布元の固定版説明](https://huggingface.co/datasets/baobab-trees/wikipedia-human-retrieval-ja/blob/02e85c83a64f345aee62fba3a35af99c075a331f/README.md)と
実ファイルを確認した。日本語Wikipediaで人手検索を行い、引用に基づいて回答段落を作る構成で、
短答の長文化や翻訳対の新規作成を必要としない。回答の各文から参照番号へ対応がある。

固定版の回答付き838件と、回答を作れなかった433件を取得し、配布元Git Blob/SHA256を照合した。
構造監査では、ID重複、参照範囲外、引用先Page欠落、回答と文列の本文不一致は0だった。
回答長は中央値222.5文字、文数は3文303件・4文250件・5文120件で、説明回答の比較に適する。
これは形式と課題構成の確認であり、Referenceの意味上の正しさや内部Judgeの妥当性を保証しない。

回答付きQAを日本語の母集団候補とし、回答なし433件をCorpus全体の回答不能へ読み替えない。
回答なしの参照記録も検索CorpusのSource記事一覧へ使用できるが、推論へ正解の印は渡さない。
原データの来歴、ファイルHash、検証結果は
[選定Manifest](../data/manifests/phase11_japanese_source_selection.json)に保存する。

## 2. CLAPNQと近い点・残る差

| 観点 | 既存英語CLAPNQ | 選定した日本語Source |
|---|---|---|
| 課題 | Wikipediaに基づく説明回答 | 日本語Wikipediaの検索・引用に基づく説明回答 |
| 回答 | 人手の長文Reference、複数の根拠文 | 人手の回答段落、文ごとの参照番号 |
| 根拠対応 | Gold Passage / Selected Sentences | 引用文または人手要約、記事Title/URL |
| 公開範囲 | 既存の公開QA4345件、研究用分割済み | 回答付き838件/回答なし433件、内部の文書Group分割はこれから |
| Corpus | 固定178890 Passage、全文/ID対応を検証済み | 引用断片以外の記事全文を、取得条件を固定して準備する必要がある |
| 日付 | 既存の固定Sourceを維持 | 人手収集は2023-12-04〜25。公開QAのRevisionと記事Revisionを別に保存する |

英語の出典質問と日本語の質問収集過程、回答長、参照の数/分散、Corpus規模・検索品質は一致しない。
日英差を言語単独の因果効果とは扱わず、実測と文書の差を保存する。
配布元は、引用外の知識を使わない設計である一方、外界での正しさを保証するQAではないと説明している。
独立AI品質でもReferenceだけに従わず、実使用Contextの支持と質問の必須要点を確認する。

## 3. 他候補の比較

以下の判断は研究目的との適合性についてで、Dataset一般の品質評価ではない。
回答長の数値は文字数であり、英語の語数やTokenizer長へ変換して同一視しない。

| 候補・一次資料 | 確認できた性質 | 今回の主Sourceにしない理由・残る条件 |
|---|---|---|
| [JQaRA](https://github.com/hotchpotch/JQaRA) | 日本語Wikipedia、各質問100候補の検索評価 | 短い回答と候補順位付けが中心。長文Referenceと全文Corpusの同等性を満たさない |
| [JaQuAD](https://github.com/SkelterLabsInc/JaQuAD) | 人手・Wikipedia・記事分離。Train先頭1ファイル1002 QAも確認 | 当該ファイルの回答中央値5文字。短いSpan抽出と説明回答の課題差が大きい |
| [JEMHopQA](https://github.com/aiishii/JEMHopQA) / [長Context派生](https://huggingface.co/datasets/llm-jp/llm-jp-longbench-JEMHop) | 日本語・複数記事・導出Triple・記事ID | Contextが長くてもReferenceは主に短答。導出を長文正解へ無断変換しない |
| [JCrRAG](https://huggingface.co/datasets/alt-dev/jcrrag) | 人手Annotation、Context/Question/Answerの20000件を取得・Hash検証 | 混合12分野の固定Context課題。原記事ID/URL等の列がなく、原文書Groupや独立検索Corpusの来歴整備が必要 |
| [JNQ / JBoolQ](https://www.jstage.jst.go.jp/article/jnlp/32/2/32_497/_article/-char/en) | 日本語検索由来、Wikipedia、長い根拠段落/短答 | 論文の長Answer抽出と、CLAPNQの再構成Referenceは異なる。確認した公開資料から配布Sourceを特定できなかった |
| [CaLMQA](https://huggingface.co/datasets/shanearora/CaLMQA) | 翻訳対ではない多言語長文QA、日本語を含む | Wikipedia根拠・検索Corpusとの対応がない。Card内のLicense表記にも差があり、そのまま採用しない |
| [ChouBun](https://huggingface.co/datasets/SakanaAI/ChouBun) | 日本語・長Context・Wikipedia QAを含む | wiki_qaは抜出し型。長Contextと長文回答は異なる。別の要約課題をQAへ読み替えない |
| [Nonexistent Japanese RAG Benchmark](https://github.com/sbintuitions/nonexistent_japanese_rag_benchmark) | 合成Wikipedia等、Annotation、根拠対応 | Pseudo Wikipediaは50文書166 QA。ZIPはフォーム経由のパスワードが必要で本文未取得。自動申請や保護の迂回は行っていない |
| [LIT-RAGBench](https://github.com/Koki-Itai/LIT-RAGBench) | 原日本語114問、根拠Chunkあり。日本語ファイルを取得・検証 | 回答中央値21文字、人工の表/論理/棄却を含む固定文脈課題。英語版は翻訳対で今回の主比較に使わない |
| [JDocQA](https://github.com/mizuumi/JDocQA) | 日本語・人手・PDF文書ID・説明回答。Train9290件を構造監査 | 視覚/表/OCRの影響。回答可能なopen-ended3102件中、画像種別空欄404件もText-onlyの証明にならない |
| [tmg-cqa](https://huggingface.co/datasets/pfnet/tmg-cqa) | 日本語・複数資料・引用、RAG862問/Tool571問 | 本文は非同梱でPDF/OCR等の準備が必要。行政の複雑課題・モデル生成Referenceで、百科事典QAとの差が大きい |
| [NIILC](https://mynlp.is.s.u-tokyo.ac.jp/niilc-qa/) | 日本語・百科事典・人手・記事等のMetadata | 単純質問を対象にしており、今回の長文回答の主Sourceとして優先しない |

## 4. Source選定後に残る必須作業

1. 日本語の検索Corpusは、全1271 QAの検索記録に現れる記事Title/URLから作る共通Corpusを候補とする。
   引用断片だけを渡すOracle条件へ切り替えない。記事全文の取得・整形・分割をVersion管理し、
   記事Revision/時点・Hash・Redirect対応・取得失敗と規模を保存する。本文取得は全QA共通で、質問ごとにGoldを注入しない。
   2023-12-25以前のRevisionを取得するAPIを開発例1件で確認したが、全記事の準備は未実施。
2. 全検索記録の参照Titleは2178種類。回答付きQAの引用先Titleによる連結Groupは737、最大7 QAだった。
   Redirect/Title別名の解決後に再確認し、複数参照を持つQAを介した分割間漏洩も防ぐ。
3. Cardのプレビューを保守的に扱い、回答付きファイル先頭100 QAとその引用Title連結Groupは開発専用へ予約する。
   初期監査では132 QAへ広がり、残り706 QA。最終分割ではRedirect等によるGroup拡大を反映する。
   残りの質問・回答本文はモデルへ表示せず、構造集計と文書Metadataだけを確認した。
4. 引用本文と人手要約を区別する。全参照に引用1651・要約103件があり、94 QAは要約等の非quote引用先を含む。
   要約をWikipedia原文と偽って扱わず、本文Corpusとの対応・代替根拠・欠損を検証して採点資料へ明示する。
5. 日本語検索・文単位・拒否・予算・品質入出力を実装し、Development実走と日英Calibrationへ進む。
   生データはGit管理外、Gitには小さいManifestと集計を置く。SourceのApache-2.0表記と、引用Wikipedia本文の出典・権利表示を区別して保持する。

日本語の本実験件数、内部モデル/指示文の採用、分析条件は未固定。Gate 11未通過、Phase 12未実施。

## 5. 取得CLIの実装と確認範囲

`scripts/prepare_japanese_corpus.py`でSource再取得と歴史的な記事全文の取得を行う。
計画には全参照Title・QA Source Hash・取得Config・実行Source Hashを保存する。

```bash
export PATH="$PWD/.tools/bin:$PATH"
export UV_CACHE_DIR="$PWD/.tools/uv-cache"
uv run python scripts/prepare_japanese_corpus.py plan --download-source \
  --output-dir data/raw/wikipedia_human_retrieval_ja/corpus-20231225-v1
uv run python scripts/prepare_japanese_corpus.py fetch \
  --output-dir data/raw/wikipedia_human_retrieval_ja/corpus-20231225-v1
```

現在版へのFallbackはせず、欠損・取得失敗も保存する。既存の終端失敗は上書きせず、
再取得の条件を変更するなら新Versionを使う。Sourceと記事の取得はモデル呼出し0回である。
過去HTMLはTemplate等の現行描画が混ざり得るため、保存した応答/本文Hashで入力を固定する。
各QAの収集日と共通のCorpus時点の差、Redirect対応、引用/要約との一致は後続監査に残す。

既知開発例の経済産業省1記事でRevision/本文の実取得を確認し、全284 TestとRuffが成功した。
これは全Corpus・検索・日本語LLM・品質の実走成功ではない。
[取得Preflight Manifest](../data/manifests/phase11_japanese_acquisition_preflight.json)を参照する。

## 6. QA取込みとGroup分割の準備（2026年10月21日）

`scripts/prepare_japanese_dataset.py`と`configs/phase11_japanese_dataset_v1.json`を追加し、
実838件を内部QAへ取り込んで原行HashとReference/引用Indexを確認した。
Source IDから安定IDを作り、言語を`ja`と記録する。人手要約は原文引用と別Fieldへ保持する。
非quoteの引用先を持つ94 QAも除外しない。回答なし433件をCorpus全体の回答不能と解釈しない。

Groupは各回答の引用先だけでなく同QAの全参照記事をつなぎ、Redirect/別名・Page ID・同じ記事全文Hash、
同文の質問/Reference回答の依存もまとめる。機械的な同文Hashの確認に限定し、未使用QA本文を調整に閲覧しない。
初期予約132件を含む成分は全て開発専用とする。Title/同文のみの現時点の監査では706 Group・開発予約142件。
Redirect解決後はさらに閉包が広がり得るため、まだ正式Splitとはしない。

分割目標は既存英語と同じDevelopment65%・Calibration10%・Evaluation25%、Seed42。
開発予約を優先し、残りのGroupをサイズ降順・Seed付きHash順に割り当て、目標QA数との二乗誤差の増分を
最小にする。大きいGroupを切り分けて件数を合わせない。実比率のずれを報告し、最終採用件数は別途決める。

`audit-source`は記事同一性を確定せず、全QAの`research_split=None`を保持する。
出力は`data/processed/wikipedia_human_retrieval_ja/02e85c8-source-audit-v1/`のQA/Group/Report。
同じCode/Config・Sourceでの再実行はByte不変、異なる既存出力の上書きは拒否する。
参照断片からCorpus Passageを作らず、`gold_passage_ids=[]`と`pending_passage_build`を明示する。
本文Passage化と引用対応の監査は後続で行い、人手回答の存在を共通Corpusの網羅性の証明にはしない。

```bash
uv run python scripts/prepare_japanese_dataset.py audit-source \
  --source-dir .tools/worktrees/phase11-japanese-corpus-v1/data/raw/wikipedia_human_retrieval_ja/source-02e85c83a64f345aee62fba3a35af99c075a331f \
  --output-dir data/processed/wikipedia_human_retrieval_ja/02e85c8-source-audit-v1
```

正式生成は`build --snapshot-dir <完了済みCorpus Directory>`を用いる。
取得完了の全記事記録・HTTP応答・過去Revision・本文・実行Source ArchiveのHash、件数と同一記事の整合を照合する。
取得の排他的Lockが残る実行中のCorpusには正式生成せず、部分取得や未解決の取得エラーでもSplitを生成しない。
取得中の実プロセスに対する生成拒否と出力QAなしを確認した。全338 Test（4.54秒）・Ruff成功。
確認根拠は`data/manifests/phase11_japanese_dataset_preflight.json`。記事取得・正式Split・検索・日本語Model実走と
品質確認・日英Calibration・最終Gateは未完了である。

## 7. 削除された過去本文の欠測規則

取得中に「出家」Revision95068750への削除本文の閲覧権限エラーを確認した。
原の失敗・保存応答・Hashを保持し、Dataset Config v2で過去Identityと指定API応答を検証する。
一致する場合もstatus=errorを変更せず、本文取得不能の監査情報を別保存する。
通信/別権限エラーの一括許容、現在版Fallback、QA除外・回答不能への変換は行わない。
v1とその監査は保持する。詳細は[本文欠測・Corpus準備](phase11_corpus_preparation.md)。

## 8. 全取得と正式Group分割の完了

2026年10月21日15:15 JST、Commit61b4a5cの専用Checkoutによる全2178 Titleの取得が終了した。
原記録は本文取得2126・取得不能50・エラー2。エラー2件は「出家」Revision95068750と
「阪神甲子園球場」Revision98510583の削除過去本文への指定権限エラーであり、v2の欠測規則で検証した。
原エラーを保持し、別時点の本文で補わない。取得成功した重複Pageをまとめると2118記事である。

全保存応答・過去Revision・本文/Source Hash・完了件数・同一Pageの整合を照合し、
`02e85c8-groups-v2`へ正式なQAとGroupを生成した。原838 QAを除外せず、706 Group・4790 Identity Keyの
Group間重複0、開発予約142 QAの全成分がDevelopmentにあることを別Scriptでも検証した。

| Split | QA数 |
|---|---:|
| Development | 545 |
| Calibration | 84 |
| Evaluation | 209 |

固定Sourceと全取得記録をMain側の`data/raw/wikipedia_human_retrieval_ja/`へ複製し、6494ファイルの
同一Byteを検証した。元CheckoutのRawも保持する。正規配置の全ファイル一覧・Hashは
`acquisition_file_index_v1.json`、正式Splitは
`data/processed/wikipedia_human_retrieval_ja/02e85c8-groups-v2/`にある。
根拠は`data/manifests/phase11_japanese_snapshot_group_manifest.json`。

未使用Calibration/Evaluation本文を調整に表示せず、機械的な原行・Group・Split照合だけを行った。
`gold_passage_ids=[]`と`pending_passage_build`は保持している。記事全体をPassageへ分割して参照対応と
欠測を監査する作業は未完了であり、209件を最終本実験の確定件数とはしない。
この取得・分割完了だけでGate 11を通さず、日英RAG実走・意味監査・未使用Calibration・最終固定へ続ける。
