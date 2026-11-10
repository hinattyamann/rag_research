# 具体例の節の改稿案

2026年11月10日 15:59 JST。対話後の日英一括改稿に向けた本文案。現行DOCX・生成入力・図表には未反映。以下の日英本文案は同内容とし、抜粋と選択結果を保存済み資料へ照合する。最終の表形式・配置・分量は全体改稿時に調整する。

## 英語本文案

### 5.3 Examples of answers and selection outcomes

The following cases illustrate changes in answer selection across evidence orders. A is the initial answer and B the common rewrite. Y is the external AI quality label. The cases were selected after inspecting the results. Quoted answers are excerpts; English cases are shown in their original language and the Japanese case is translated into English.

**United States involvement in the Vietnam War.** The question is “how and why did the united states escalate its role in the vietnam war”. The used evidence describes an increase of 5,000 advisers in July 1964 to a total of 21,000, and a separate passage explains the broader containment rationale. The two answers state:

- A: “The United States escalated its role in the Vietnam War due to the escalation of military advisers ordered to the Republic of Vietnam in 1964, bringing the total American troop level to 21,000. This increase was a direct response to the growing conflict and the need to support South Vietnam against North Vietnam's communist domination.”
- B: “This escalation was driven by an incentive to end growing communist domination in Vietnam and prevent a chain of neighbouring countries adopting the same ideology, which would change the balance of power throughout Southeast Asia”

The external assessor labels A unreliable (Y=0): the evidence gives a general containment rationale but does not link the specific adviser increase to the direct cause asserted by A. B also gives the date and adviser numbers and receives Y=1. With the original evidence order, F=1/3 and B is selected. Under shuffle_3, F=1 and A is retained. Reordering therefore changes the selected answer from B (Y=1) to A (Y=0).

**Moths and butterflies.** The question is “What's the difference between moths and butterflies?” The used evidence states, “The terms for both butterflies and moths are of Chinese origin.” The initial answer begins with a taxonomic distinction but then adds:

- A: “Butterflies are bilaterally symmetrical, and a shape whose ends spread out is sometimes named by likening it to a butterfly with its wings open.” “Moths are often called by a Chinese-derived term because their characteristics differ from those of butterflies.”
- B: “Other species of Lepidoptera are called moths, but dividing Lepidoptera into butterflies and moths is not a natural classification” “In Japanese, the names of many insects, such as flies and bees, are native Japanese words, whereas the terms for both butterflies and moths are of Chinese origin”

A mixes a figurative use of the word butterfly with biological differences and introduces an unsupported causal explanation for the name moth; it receives Y=0. B explains the classification and the naming without this causal claim and receives Y=1. With the original evidence order, F=3/4 and A is retained. Under shuffle_2, F=2/4 and B is selected. Here reordering changes the selected answer from A (Y=0) to B (Y=1).

**Fried green tomatoes.** The question is “where did the idea of fried green tomatoes come from”. The retrieved passages discuss tomato history and agriculture, without an account of the requested origin. Both answers report this information gap:

- A: “The passages focus on the introduction and acceptance of tomatoes in Europe, their culinary use, and the development of tomato sauces in Neapolitan cuisine. There is no mention of fried green tomatoes or their origin.”
- B: “None of the provided documents mention the origin of fried green tomatoes.”

Neither answer supplies the requested origin, and both receive Y=0. With the original evidence order, F=2/3 and B is selected; reversing the order gives F=1 and retains A. The selected text changes, while the quality label remains Y=0.

## 日本語本文案

### 5.3 回答と選択結果の具体例

以下では、根拠順序による回答選択の変化を具体例で示す。Aは初回回答、Bは共通の書換え回答、Yは外部AIによる品質ラベルである。例は結果の確認後に選定した。引用した回答は抜粋であり、英語の例は日本語に訳し、日本語の例は原文を示す。

**ベトナム戦争への米国の関与。** 質問は「米国はベトナム戦争への関与をどのように、なぜ拡大したのか」である。実使用根拠には、1964年7月に顧問団を5,000人増やして計21,000人としたことが記され、別の段落では封じ込めという全般的な動機が説明されている。両回答には次の記述がある。

- A：「米国は、1964年にベトナム共和国への軍事顧問団の派遣を増やし、米軍の総数を21,000人とすることにより、ベトナム戦争への関与を拡大した。この増員は、拡大する紛争と、北ベトナムの共産主義的支配に対抗して南ベトナムを支援する必要性への直接の対応であった。」
- B：「この関与拡大の動機は、ベトナムで拡大する共産主義的支配を終わらせ、近隣諸国が連鎖的に同じ思想を採用して東南アジア全体の勢力均衡を変える事態を防ぐことであった」

外部採点器はAを不良（Y=0）とした。根拠は封じ込めという全般的な動機を説明しているが、当該の顧問団増員とAが述べた直接の原因との関係までは示していないためである。Bは日付と顧問団の人数も述べ、Y=1とされた。元順序ではF=1/3となり、Bが選ばれた。一方、shuffle_3ではF=1となり、Aが採用された。したがって、並べ替えによって、選択される回答はB（Y=1）からA（Y=0）へ変わった。

**蛾と蝶の違い。** 質問は「蛾と蝶の違いってなんすか。」である。実使用根拠には「この蝶と蛾に関しては漢語である。」と記されている。初回回答は分類上の違いから始まるが、続いて次の記述を加えている。

- A：「蝶は左右対称で、その各端が広がっている形状を蝶が羽を開いた姿に例えて呼称することがあります。」「蛾はその特徴がチョウと異なるため、漢語で呼ばれることが多いです。」
- B：「その他のチョウ目の種はガ（蛾）と呼ばれるが、チョウ目をチョウとガに分けるのは自然な分類ではない」「日本語ではハエやハチなど多くの虫の名称が大和言葉であるのに対し、この蝶と蛾に関しては漢語である」

Aは「蝶」という語の比喩的用法を生物の違いと混在させ、蛾の名称について根拠のない因果説明を加えているため、Y=0とされた。Bはこの因果関係を述べずに分類と名称を説明し、Y=1とされた。元順序ではF=3/4となり、Aが採用された。一方、shuffle_2ではF=2/4となり、Bが選ばれた。この例では、並べ替えによって、選択される回答がA（Y=0）からB（Y=1）へ変わった。

**フライド・グリーン・トマト。** 質問は「フライド・グリーン・トマトのアイデアはどこから生まれたのか」である。検索された段落はトマトの歴史や農業を扱い、問われた起源の説明を含んでいない。両回答は、その情報不足を述べている。

- A：「これらの段落は、ヨーロッパへのトマトの導入と受容、料理への利用、ナポリ料理におけるトマトソースの発展を扱っている。フライド・グリーン・トマトやその起源への言及はない。」
- B：「提示された文書のいずれにも、フライド・グリーン・トマトの起源への言及はない。」

いずれの回答も問われた起源を答えておらず、両方ともY=0とされた。元順序ではF=2/3となり、Bが選ばれたが、逆順ではF=1となり、Aが採用された。選択される文章は変わったが、品質ラベルはY=0のままであった。

## 原稿外の照合事項

以下は執筆者用の確認事項であり、論文本文・補足資料には含めない。

- 原資料: [ベトナム戦争](../materials/fixed_v23_v1/inputs/cal_en_f94093f2dcb620bdcf4bdb09.json)、[蛾と蝶](../materials/fixed_v23_v1/inputs/cal_ja_7d88f788771d9ca5d8b6acf8.json)、[トマト](../materials/fixed_v23_v1/inputs/cal_en_736a378735160bb469f1b9b7.json)。選択経路・スコアは各[cases](../materials/fixed_v23_v1/cases/)のcase_01/02/03.jsonに照合する。
- 各引用は一つの連続した保存原文の抜粋とする。離れた文は別の引用符に分け、引用IDの手前で抜粋を終える。英語例の日本語と日本語例の英語は、本文全体と同様に対応する翻訳とする。
- 蛾と蝶のBには引用先のずれがある。抜粋では元の引用IDを含めていない。Bを全引用位置まで正しい回答と説明せず、保存済みAIラベルY=1として示す。
- トマトの質問には料理と作品名の曖昧さがある。保存採点はどちらの読みでも必要な答えを欠くとしている。料理の起源を正解だと補ったり、参考資料だけの映画情報を実使用根拠へ混ぜたりしない。
- 個々の引用箇所の意味判定がスコア変動の原因だったとは断定しない。ここで示すのは同じ候補・根拠内容のまま順序で選択が変わった対応であり、Yは保存済み外部AIラベルである。
- 表5を残す場合はトマトの元順序・逆順も含め、本文の3例すべてと結果を対応させる。本文に掲載する原文・翻訳・分量と図表配置は一括改稿時に再確認する。
