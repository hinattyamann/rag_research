"""Self-contained local annotation form; no private assignments or network access."""

import json

from rag_research.experiments.quality import blank_annotations


def render_form(packet):
    data = json.dumps({"packet": packet, "answers": blank_annotations(packet)}, ensure_ascii=False)
    data = data.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return TEMPLATE.replace("__SAFE_DATA__", data)


TEMPLATE = r'''<!doctype html>
<html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'none'; connect-src 'none'">
<title>回答品質の確認</title>
<style>
body{font:16px/1.7 system-ui,sans-serif;background:#f3f5f7;color:#162331;max-width:1000px;margin:auto;padding:24px}
article,header,details.rubric{background:white;border:1px solid #ccd5df;border-radius:10px;padding:24px;margin:20px 0}
pre,.text{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}h1{font-size:26px}h2{font-size:21px}
button,select,input,textarea{font:inherit;padding:8px;border:1px solid #a8b5c3;border-radius:5px}
button{background:#174b75;color:white;cursor:pointer;margin:8px 8px 8px 0}label{display:block;margin:12px 0}
textarea{display:block;width:95%;min-height:80px}details{margin:12px 0}summary{cursor:pointer;font-weight:600}
.answer{background:#f1f7ff;border-left:4px solid #2973ab;padding:18px}.small{font-size:14px;color:#42546a}
.status{font-weight:bold}#message{white-space:pre-wrap;color:#8c2705}input[type=text]{width:70%}
</style>
<header><h1>回答品質の確認</h1>
<p>質問・回答・実際に使用された根拠を確認してください。ReferenceとGold根拠は採点専用です。
Referenceとの表現の違いやGoldが検索されていないことだけで、不正解にはしません。</p>
<p>候補ごとに「採点開始」を押し、3観点・必須要点・理由・根拠を記録してください。
確認時間は採点中の経過秒です。休憩中は停止してください。必要なら手入力で直せます。</p>
<p class="small">未採点と判定不能は区別します。明確な失敗が1つあればY=0、全観点が合格ならY=1です。
表示上は条件名や生成段階を隠しています。過去に見た例を覚えている可能性は残ります。</p>
<label>確認者名 <input id="annotator" type="text" placeholder="氏名または研究用ID"></label>
<button id="save">採点JSONを保存（途中保存も可能）</button>
<label>保存したJSONから再開 <input id="load" type="file" accept=".json"></label>
<p id="message" role="status"></p></header>
<details class="rubric"><summary>採点基準</summary><pre id="rubric"></pre></details>
<main id="cases"></main>
<script type="application/json" id="data">__SAFE_DATA__</script>
<script>
'use strict';
const initial=JSON.parse(document.getElementById('data').textContent);
const packet=initial.packet; let answers=initial.answers;
const names={essential_answer:'質問の必須要点に答えている',no_major_error:'重大な誤り・矛盾・条件の脱落がない',context_support:'事実主張が実使用の根拠で支持される'};
const labels={pending:'未採点',reliable:'Y=1 / 信頼できる',unreliable:'Y=0 / 明確な不足・誤りがある',indeterminate:'判定不能'};
let running=null, started=0;
const $=id=>document.getElementById(id);
const show=message=>$('message').textContent=message;
const el=(tag,text,parent)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(parent)parent.append(x);return x};
function stop(){if(running!==null){const a=answers.annotations[running];a.elapsed_seconds=(a.elapsed_seconds||0)+(Date.now()-started)/1000;running=null;render();}}
function status(a){const values=Object.values(a.criteria);return values.includes('fail')?'unreliable':values.includes('pending')?'pending':values.includes('uncertain')?'indeterminate':'reliable';}
function update(a){a.label=status(a);a.confirmed_at_utc=a.label==='pending'?null:new Date().toISOString();}
function textArea(parent,title,value,set){const label=el('label',title,parent);const x=el('textarea',undefined,label);x.value=value;x.oninput=()=>set(x.value);return x;}
function docs(parent,title,documents){const d=el('details',undefined,parent);el('summary',title,d);for(const doc of documents){el('h3',doc.passage_id+' / '+doc.title,d);el('pre',doc.text,d);}}
function render(){
 $('rubric').textContent=packet.rubric;$('cases').replaceChildren();
 packet.cases.forEach((c,i)=>{const a=answers.annotations.find(x=>x.annotation_id===c.annotation_id);
 const index=answers.annotations.indexOf(a); const card=el('article',undefined,$('cases'));
 el('h2',(i+1)+' / '+packet.cases.length+'　'+c.annotation_id,card);
 el('h3','質問',card);el('pre',c.question,card);el('h3','回答',card);el('pre',c.answer,card).className='answer';
 docs(card,'実使用の根拠（モデルが読んだ本文）',c.documents);
 const ref=el('details',undefined,card);el('summary','Reference（唯一の正解表現ではありません）',ref);
 c.reference_answers.forEach((r,j)=>{el('h3','Reference '+(j+1),ref);el('pre',r,ref);el('pre',(c.selected_sentences_by_reference[j]||[]).join('\n'),ref);});
 docs(card,'Gold根拠（採点専用。モデル未取得の場合があります）',c.gold_documents);
 const timer=el('button',running===index?'時間計測を停止':'この候補の採点開始',card);
 timer.onclick=()=>{const was=running===index;stop();if(!was){running=index;started=Date.now();render();}};
 const sec=el('label','確認時間（秒） ',card);const seconds=el('input',undefined,sec);seconds.type='number';seconds.min='0';seconds.step='0.1';seconds.value=a.elapsed_seconds??'';
 seconds.oninput=()=>{a.elapsed_seconds=seconds.value===''?null:Number(seconds.value)};
 for(const key of packet.criteria){const line=el('label',names[key]+' ',card);const select=el('select',undefined,line);
 for(const [value,title] of [['pending','未確認'],['pass','合格'],['fail','明確な失敗'],['uncertain','判断が難しい']]){const o=el('option',title,select);o.value=value;}
 select.value=a.criteria[key];select.onchange=()=>{a.criteria[key]=select.value;update(a);card.querySelector('.status').textContent=labels[a.label];};}
 el('p',labels[a.label],card).className='status';
 textArea(card,'質問に答えるために必要な要点',a.essential_points,v=>{a.essential_points=v;update(a)});
 textArea(card,'判定理由（不足・誤り・曖昧さの内容）',a.reason,v=>{a.reason=v;update(a)});
 const label=el('label','根拠箇所（1行につき passage_id | 本文の完全一致する引用）',card);
 const evidence=el('textarea',undefined,label);evidence.value=a.evidence.map(e=>e.passage_id+' | '+e.quote).join('\n');
 evidence.oninput=()=>{a.evidence=evidence.value.split('\n').filter(x=>x.trim()).map(line=>{const split=line.indexOf('|');return {passage_id:split<0?'':line.slice(0,split).trim(),quote:split<0?line:line.slice(split+1).trim()}});update(a);};
 });
}
$('save').onclick=()=>{stop();const annotator=$('annotator').value.trim();const errors=[];
 for(const a of answers.annotations){update(a);if(a.label==='pending')continue;a.annotator=annotator;
 if(!annotator||!a.reason.trim()||!a.essential_points.trim()||!(a.elapsed_seconds>0))errors.push(a.annotation_id+': 確認者・必須要点・理由・正の確認時間が必要です。');
 if(a.label==='reliable'&&!a.evidence.length)errors.push(a.annotation_id+': Y=1には根拠箇所が必要です。');
 const c=packet.cases.find(x=>x.annotation_id===a.annotation_id);const docs=[...c.documents,...c.gold_documents];
 for(const e of a.evidence)if(!e.quote.trim()||!docs.some(d=>d.passage_id===e.passage_id&&d.text.includes(e.quote)))errors.push(a.annotation_id+': 引用が根拠本文と完全一致しません。');}
 if(errors.length){show(errors.join('\n'));return;}
 const blob=new Blob([JSON.stringify(answers,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const link=el('a');link.href=url;link.download='quality-annotations.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);show('JSONを保存しました。採点結果はCLIで読み込むまで実験結果に反映されません。');render();};
$('load').onchange=async event=>{try{const file=event.target.files[0];if(!file)return;const value=JSON.parse(await file.text());
 if(value.packet_sha256!==packet.packet_sha256||value.rubric_version!==packet.rubric_version||value.schema_version!==1)throw Error('別の採点票です');
 if(value.annotations.length!==packet.cases.length||new Set(value.annotations.map(a=>a.annotation_id)).size!==packet.cases.length)throw Error('候補数・IDが一致しません');
 for(const c of packet.cases){const a=value.annotations.find(x=>x.annotation_id===c.annotation_id);if(!a||a.candidate_sha256!==c.candidate_sha256)throw Error('候補Hashが一致しません');}
 stop();answers=value;$('annotator').value=value.annotations.find(a=>a.annotator)?.annotator||'';render();show('途中保存を読み込みました。');}catch(e){show('読込失敗: '+e.message);}};
window.addEventListener('pagehide',()=>{running=null});
render();
</script></html>'''
