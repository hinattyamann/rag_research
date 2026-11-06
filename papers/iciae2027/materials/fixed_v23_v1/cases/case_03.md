# case_03 — cal/en

QA: `clapnq:c508d78:train:-5607690022829878056:answerable`

選定: First lexicographic unused any language QA satisfying same_quality。結果閲覧後の説明例であり、頻度の推定に使わない。

[全文・Referenceと実使用根拠・A/B・来歴](../inputs/cal_en_736a378735160bb469f1b9b7.json)

## 質問

where did the idea of fried green tomatoes come from

## 初回回答 A

The idea of fried green tomatoes did not originate from the passage provided. The passages focus on the introduction and acceptance of tomatoes in Europe, their culinary use, and the development of tomato sauces in Neapolitan cuisine. There is no mention of fried green tomatoes or their origin. [810572008_5677-6655]

外部AI品質: unreliable / Y=0

## 書換え B

None of the provided documents mention the origin of fried green tomatoes. The texts cover tomato introduction in Europe [810572008_5677-6655], pre-Columbian agriculture [837717284_33570-34159], acceptance history [810572008_4761-5676], mechanized harvesting of green tomatoes for processing [827724067_10159-11489], and Columbian Exchange [810572008_3809-4436]. None specify the origin of fried green tomatoes.

状態: ok / 外部AI品質: unreliable / Y=0

## 順序別の対応

| Trial | 根拠ID列 | F | 判断 | Action |
|---|---|---|---|---|
| reversed | 810572008_3809-4436, 827724067_10159-11489, 810572008_4761-5676, 837717284_33570-34159, 810572008_5677-6655 | 1.0 | accept | keep_initial |
| repeat_2 | 810572008_5677-6655, 837717284_33570-34159, 810572008_4761-5676, 827724067_10159-11489, 810572008_3809-4436 | 0.6666666666666666 | rewrite | rewrite_requested |
| shuffle_2 | 837717284_33570-34159, 810572008_4761-5676, 827724067_10159-11489, 810572008_3809-4436, 810572008_5677-6655 | 0.6666666666666666 | rewrite | rewrite_requested |
| repeat_5 | 810572008_5677-6655, 837717284_33570-34159, 810572008_4761-5676, 827724067_10159-11489, 810572008_3809-4436 | 0.6666666666666666 | rewrite | rewrite_requested |
| shuffle_1 | 837717284_33570-34159, 827724067_10159-11489, 810572008_3809-4436, 810572008_5677-6655, 810572008_4761-5676 | 0.6666666666666666 | rewrite | rewrite_requested |
| repeat_3 | 810572008_5677-6655, 837717284_33570-34159, 810572008_4761-5676, 827724067_10159-11489, 810572008_3809-4436 | 0.6666666666666666 | rewrite | rewrite_requested |
| shuffle_3 | 827724067_10159-11489, 810572008_3809-4436, 810572008_5677-6655, 837717284_33570-34159, 810572008_4761-5676 | 0.6666666666666666 | rewrite | rewrite_requested |
| repeat_4 | 810572008_5677-6655, 837717284_33570-34159, 810572008_4761-5676, 827724067_10159-11489, 810572008_3809-4436 | 0.6666666666666666 | rewrite | rewrite_requested |
| original | 810572008_5677-6655, 837717284_33570-34159, 810572008_4761-5676, 827724067_10159-11489, 810572008_3809-4436 | 0.6666666666666666 | rewrite | rewrite_requested |

Fは固定文の支持割合であり、回答全体の正答率ではない。Label・根拠引用・経路費用は同名JSONとリンク先へ保存。

## 根拠の表示用抜粋

全文とは別の機械的な先頭抜粋。意味の説明に必要な範囲は元の全文で確認する。

### 810572008_5677-6655 — Columbian Exchange

出典: https://en.wikipedia.org/wiki/Columbian_Exchange / 範囲0:240文字

```text
In the early years , tomatoes were mainly grown as ornamentals in Italy . For example , the Florentine aristocrat Giovan Vettorio Soderini wrote how they `` were to be sought only for their beauty '' and were grown only in gardens or flower
```

### 837717284_33570-34159 — Pre-Columbian era

出典: https://en.wikipedia.org/wiki/Pre-Columbian_era / 範囲0:240文字

```text
Early inhabitants of the Americas developed agriculture , developing and breeding maize ( corn ) from ears 2 -- 5 cm in length to the current size are familiar today . Potatoes , tomatoes , tomatillos ( a husked green tomato ) , pumpkins , 
```

### 810572008_4761-5676 — Columbian Exchange

出典: https://en.wikipedia.org/wiki/Columbian_Exchange / 範囲0:240文字

```text
It took three centuries after their introduction in Europe for tomatoes to become widely accepted . Of all the New World plants introduced to Italy , only the potato took as long as the tomato to gain acceptance . In large part this was due
```

### 827724067_10159-11489 — Mechanised agriculture

出典: https://en.wikipedia.org/wiki/Mechanised_agriculture / 範囲0:240文字

```text
According to a 1977 report by the California Agrarian Action Project , during the summer of 1976 in California , many harvest machines had been equipped with a photo - electric scanner that sorted out green tomatoes among the ripe red ones 
```

### 810572008_3809-4436 — Columbian Exchange

出典: https://en.wikipedia.org/wiki/Columbian_Exchange / 範囲0:240文字

```text
Tomatoes , which came to Europe from the New World via Spain , were initially prized in Italy mainly for their ornamental value ( see below ) . From the 19th century tomato sauces became typical of Neapolitan cuisine and , ultimately , Ital
```
