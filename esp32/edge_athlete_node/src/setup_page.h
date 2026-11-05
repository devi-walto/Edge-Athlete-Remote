// setup_page.h — the page an athlete's phone opens when it joins the sensor's own
// Wi-Fi (EdgeAthlete-<id>), to set the sensor up with no computer (spec 14 Phase 8).
//
// Why it looks like this: it follows the approved boards (Final designs, F_Setup1–5,
// version 2 of 2026-11-05, from watching a real athlete set one up): pick the Wi-Fi →
// its password, tried right away (and once more by itself) → the school code (Remote;
// filled in when the sensor already knows its school) or the base station (Local) →
// the sensor code in 8 boxes, the dash built in → done. Big green-bar steps, because
// small numbered ones were missed; one word for each thing ("school code", "sensor
// code"), the same as on the athlete's Add my sensor page. The sensor's Wi-Fi has no internet, so the page is this one
// small file with the phone's own font, and it talks only to the sensor (/api/...).
// While the sensor joins the chosen Wi-Fi the phone may drop off for a moment; every
// request here simply tries again.
#pragma once

static const char SETUP_PAGE[] = R"PAGE(<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Set up your sensor</title>
<style>
:root{--bg:#070b0e;--s:#10171b;--s2:#151e23;--l:#263239;--l2:#5c6a72;--ink:#f5f7f2;--ink2:#c9d1d5;--m:#89969d;
--lime:#a9f04d;--limebg:#121b14;--amber:#f2b84b;--coral:#ff646b;--coralbg:#1e1213;
--mono:ui-monospace,"SF Mono",Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;flex-direction:column;background:var(--bg);color:var(--ink);
font:16px -apple-system,system-ui,"Segoe UI",Roboto,sans-serif}
header{display:flex;flex-direction:column;gap:14px;padding:16px;border-bottom:1px solid var(--l)}
.top{display:flex;justify-content:space-between;align-items:center}
.top b{font-size:15px;font-weight:800}.top span{color:var(--m);font:12px var(--mono)}
.steps{display:flex;flex-direction:column;gap:8px}.steps b{color:var(--lime);font-size:14px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
.prog{display:flex;gap:6px}.prog i{flex:1;height:8px;border-radius:4px;background:var(--l)}.prog i.f{background:var(--lime)}
main{flex:1;display:flex;flex-direction:column;gap:14px;padding:20px 16px 0}
footer{display:flex;flex-direction:column;gap:10px;padding:14px 16px 26px}
h1{margin:0;font-size:30px;font-weight:850;letter-spacing:-.02em;line-height:1.1}
.sub{margin:-4px 0 0;color:var(--ink2);font-size:16px;line-height:1.4}
.note{margin:0;color:var(--m);font-size:13px;line-height:1.5}
.caps{color:var(--m);font-size:10px;font-weight:800;letter-spacing:.1em;text-transform:uppercase}
button{font:inherit;cursor:pointer}
.go{width:100%;min-height:52px;border:0;border-radius:6px;background:var(--lime);color:var(--bg);font-size:16px;font-weight:800}
.go:disabled{opacity:.4}
.ghost{width:100%;min-height:52px;border:1px solid var(--l);border-radius:6px;background:none;color:var(--ink);font-size:16px;font-weight:800}
.link{align-self:flex-start;min-height:40px;padding:0;border:0;background:none;color:var(--lime);font-size:14px;font-weight:700}
.nets{display:flex;flex-direction:column;gap:6px}
.net{display:flex;align-items:center;gap:12px;min-height:54px;padding:0 14px;background:var(--s);border:1px solid var(--l);color:var(--ink);text-align:left}
.net.on{background:var(--limebg);border-color:var(--lime)}
.net b{flex:1;font-size:16px;font-weight:700}.net small{color:var(--m)}
.bars{display:flex;align-items:flex-end;gap:2px;height:16px}.bars i{width:4px;border-radius:1px;background:var(--l2)}.bars i.f{background:var(--ink)}
label.f{display:flex;flex-direction:column;gap:6px}
.box{display:flex;align-items:center;min-height:54px;padding:0 14px;background:var(--s);border:1.5px solid var(--l2);border-radius:6px}
.box:focus-within{border-color:var(--lime)}.box.bad{border-color:var(--coral)}
.box input{flex:1;min-width:0;padding:0;border:0;background:none;color:var(--ink);font:600 17px -apple-system,system-ui,sans-serif;outline:none}
.box input.code{font:800 22px var(--mono);letter-spacing:.08em;text-transform:uppercase}
.box em{color:var(--m);font-style:normal;font-size:17px;white-space:nowrap}
.check{display:flex;align-items:center;gap:8px;color:var(--ink2);font-size:14px}
.st{display:flex;align-items:center;gap:10px;min-height:48px;padding:10px 14px;background:var(--s);border:1px solid var(--l);font-size:14px;font-weight:700;line-height:1.4}
.st:before{content:"";flex:none;width:10px;height:10px;border-radius:50%;background:var(--amber)}
.st.ok{background:var(--limebg);border-color:var(--lime)}.st.ok:before{background:var(--lime)}
.st.bad{background:var(--coralbg);border-color:var(--coral)}.st.bad:before{background:var(--coral)}
.sw{display:flex;gap:4px;padding:4px;background:var(--s);border:1px solid var(--l);border-radius:8px}
.sw button{flex:1;min-height:46px;border:0;border-radius:5px;background:none;color:var(--ink2);font-size:15px;font-weight:800}
.sw button.on{background:var(--lime);color:var(--bg)}
.lime{color:var(--lime)}.caps.lime{font-size:12px}
.code8{position:relative;display:flex;align-items:center;gap:5px}
.code8 span{display:grid;place-items:center;width:36px;height:54px;background:var(--s);border:1.5px solid var(--l);border-radius:6px;font:800 24px var(--mono)}
.code8 span.has{border-color:var(--l2)}.code8 span.at{border:2px solid var(--lime)}
.code8 span.odd{background:#241c0e;border:2px solid var(--amber);color:var(--amber)}.code8.bad span{border-color:var(--coral)}
.code8 .dash{width:14px;border:0;background:none;color:var(--m)}
.code8 #c8b,.code8 #c8b span{pointer-events:none}.code8 input{position:absolute;inset:0;width:100%;height:100%;opacity:.01;border:0;font-size:16px;color:transparent;caret-color:transparent;background:none}
.st.warn{background:#241c0e;border-color:var(--amber)}
.icon{display:grid;place-items:center;width:56px;height:56px;border-radius:50%;background:#241c0e;border:2px solid var(--amber)}
.row{display:flex;justify-content:space-between;align-items:center}
.tick{display:grid;place-items:center;width:64px;height:64px;margin-top:18px;border-radius:50%;background:var(--lime);color:var(--bg);font-size:34px;font-weight:900}
.facts{display:flex;flex-direction:column;background:var(--s);border:1px solid var(--l)}
.facts div{display:flex;justify-content:space-between;gap:12px;min-height:48px;align-items:center;padding:0 14px;border-top:1px solid var(--l);font-size:14px}
.facts div:first-child{border-top:0}.facts span{color:var(--m)}.facts b{text-align:right}
</style></head><body>
<header><div class="top"><b>Edge Athlete sensor</b><span id="sid"></span></div><div class="steps" id="steps"></div></header>
<main id="main"></main><footer id="foot"></footer>
<script>
var S={id:"",domain:"",linked:"",nets:[],ssid:"",pass:"",local:false,sub:"",pref:false,host:"",name:"",gateway:"",code:"",screen:"nets"};
// Codes are made from these (one_time_secrets.py); O, 0, I, 1 and L are left out so nothing can be mixed up.
var ALPHABET="ABCDEFGHJKMNPQRSTUVWXYZ23456789";
var LOCK='<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#89969d" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Password protected"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>';
var $=function(i){return document.getElementById(i)};
function esc(t){return String(t).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
// Every request tries again for a while: the phone drops off the sensor's Wi-Fi for a
// moment whenever the sensor changes channel to join the chosen network.
function api(path,body,tries){tries=tries==null?8:tries;
 var o=body?{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams(body).toString()}:{};
 return fetch(path,o).then(function(r){return r.json()}).catch(function(e){
  if(tries<=0)throw e;return new Promise(function(ok){setTimeout(ok,1500)}).then(function(){return api(path,body,tries-1)})})}
function steps(n){var names=S.local?["Wi-Fi","Base station"]:["Wi-Fi","School code","Sensor code"];
 if(n<0){$("steps").innerHTML="";return}
 var bars=names.map(function(t,i){return '<i class="'+(i<=n?"f":"")+'"></i>'}).join("");
 $("steps").innerHTML="<b>Step "+(n+1)+" of "+names.length+" &middot; "+names[n]+'</b><div class="prog">'+bars+"</div>"}
function show(main,foot,step){steps(step);$("main").innerHTML=main;$("foot").innerHTML=foot||""}
function st(cls,text){return '<div class="st '+cls+'" id="st">'+text+"</div>"}
function bars(r){var n=r>-55?4:r>-67?3:r>-78?2:1,h="";for(var i=0;i<4;i++)h+='<i class="'+(i<n?"f":"")+'" style="height:'+(4+4*i)+'px"></i>';return '<span class="bars">'+h+"</span>"}

function netsScreen(rescan){S.screen="nets";
 var list=S.nets.length?S.nets.map(function(n,i){return '<button class="net'+(n.ssid==S.ssid?" on":"")+'" onclick="pick('+i+')"><b>'+esc(n.ssid)+"</b>"+(n.lock?LOCK:"")+bars(n.rssi)+"</button>"}).join(""):st("","Looking for Wi-Fi&hellip;");
 show('<h1>Pick your Wi-Fi</h1><p class="sub">The sensor uses this to reach your school when you lift.</p><div class="nets">'+list+
  '</div><button class="link" onclick="typed()">Not listed? Type its name</button><p class="note">Only 2.4 GHz Wi-Fi shows here; the sensor can&rsquo;t use 5 GHz. If yours is missing, it may be 5 GHz only.</p>',
  '<button class="go" onclick="passScreen()" '+(S.ssid?"":"disabled")+">Next</button>",0);
 if(!S.nets.length||rescan)scan(rescan)}
function scan(again){api("/api/scan"+(again?"?again=1":"")).then(function(r){
 if(r.scanning){setTimeout(function(){if(S.screen=="nets")scan()},1500);return}
 S.nets=r.nets;if(S.screen=="nets")netsScreen()})}
function pick(i){S.ssid=S.nets[i].ssid;netsScreen()}
function typed(){var n=prompt("The Wi-Fi's name, exactly as it's spelled");if(n){S.ssid=n;passScreen()}}

function passScreen(){S.screen="pass";
 show("<h1>"+esc(S.ssid)+'</h1><p class="sub">Type its Wi-Fi password. The sensor tries it right away.</p>'+
  '<label class="f"><span class="caps">Wi-Fi password</span><span class="box" id="pbox"><input id="pw" type="password" autocomplete="off" value="'+esc(S.pass)+'"></span></label>'+
  '<label class="check"><input type="checkbox" onchange="$(\'pw\').type=this.checked?\'text\':\'password\'"> Show password</label><div id="out"></div>'+
  '<p class="note">While it tries, your phone may drop off the sensor&rsquo;s Wi-Fi for a moment. This page finds it again on its own.</p>',
  '<button class="go" id="b" onclick="tryWifi()">Connect</button><button class="link" onclick="netsScreen()">&lsaquo; Pick another Wi-Fi</button>',0)}
function tryWifi(){S.pass=$("pw").value;$("b").disabled=true;$("pbox").className="box";
 $("out").innerHTML=st("","Connecting to "+esc(S.ssid)+"&hellip; This can take up to a minute.");
 api("/api/wifi",{ssid:S.ssid,password:S.pass}).then(function(){setTimeout(pollWifi,1500)})}
// The sensor tries up to 3 times by itself; until the last try is done the page only
// says it's still connecting, never that it failed (a first try often needs a second).
function pollWifi(){api("/api/wifi").then(function(r){
 if(S.screen!="pass")return;
 if(r.state=="connecting"){if(r.try>1)$("out").innerHTML=st("","Still connecting&hellip; (try "+r.try+" of "+r.tries+")");
  setTimeout(pollWifi,1000);return}
 if(r.state=="connected"){S.gateway=r.gateway;$("out").innerHTML=st("ok","Connected to "+esc(S.ssid));
  $("b").outerHTML='<button class="go" onclick="serverScreen()">Next</button>';return}
 var why={wrong_password:"Wrong password. Check it and try again.",not_found:"Can&rsquo;t find "+esc(S.ssid)+". It may be out of range, or 5 GHz only."}[r.state]||"Couldn&rsquo;t join "+esc(S.ssid)+". Try again.";
 if(r.state=="wrong_password")$("pbox").className="box bad";
 $("out").innerHTML=st("bad",why);$("b").disabled=false;$("b").textContent="Try again"}).catch(function(){
 // The phone dropped off the sensor's Wi-Fi for longer than usual: keep asking.
 if(S.screen=="pass")setTimeout(pollWifi,1500)})}

function serverScreen(){S.screen="server";
 var sw='<div class="sw"><button aria-pressed="'+!S.local+'" class="'+(S.local?"":"on")+'" onclick="S.local=false;serverScreen()">Remote server</button><button aria-pressed="'+S.local+'" class="'+(S.local?"on":"")+'" onclick="S.local=true;serverScreen()">Local install</button></div>';
 if(S.local){show(sw+"<h1>The gym&rsquo;s base station</h1>"+
   '<div id="out"></div><p class="note">Nothing to type. Your coach links the sensor to a rack.</p>',
   '<button class="go" id="b" onclick="checkServer()">Finish</button>',1);return}
 show(sw+"<h1>Enter your school code</h1>"+
  (S.pref?'<p class="sub">Already filled in: this sensor remembers its school.</p>':'<p class="sub">It&rsquo;s the <b class="lime">green</b> word on your Add my sensor page.</p>')+
  '<label class="f"><span class="caps lime">School code</span><span class="box" id="sbox"><input id="sub" autocapitalize="none" autocorrect="off" spellcheck="false" value="'+esc(S.sub)+'"></span></label><div id="out"></div>',
  '<button class="go" id="b" onclick="checkServer()">Next</button>',1);
 if(S.pref)checkServer()}
function checkServer(){var body;
 if(S.local){body={kind:"local"}}
 else{S.sub=$("sub").value.trim().toLowerCase();if(!S.sub)return;body={kind:"remote",sub:S.sub}}
 $("b").disabled=true;$("out").innerHTML=st("","Looking for it&hellip;");
 api("/api/server",body).then(function(r){
  if(!r.ok){S.pref=false;$("out").innerHTML=st("bad",esc(r.detail));$("b").disabled=false;if(!S.local)$("sbox").className="box bad";return}
  S.host=r.host;S.linked=r.linked;
  S.name=r.name||"";
  $("out").innerHTML=st("ok",S.local?"Found the gym&rsquo;s base station":"Found "+esc(S.name||r.host));
  setTimeout(S.local?finish:codeScreen,S.pref?1400:900)})}

function codeScreen(){S.screen="code";S.code="";
 show("<h1>Enter your sensor code</h1><p class=\"sub\">Under the school code on your Add my sensor page.</p>"+
  '<label class="f"><span class="caps lime">Sensor code</span><div class="code8" id="c8"><div class="code8" id="c8b"></div>'+
  '<input id="code" autocapitalize="characters" autocorrect="off" autocomplete="one-time-code" spellcheck="false" aria-label="Sensor code" maxlength="12" oninput="typedCode(this)"></div></label>'+
  '<p class="note" style="font-size:14px">The dash is added for you.</p><div id="out"></div>',
  '<button class="go" id="b" onclick="claim()" disabled>Link my sensor</button>'+(S.linked?'<button class="link" onclick="finish()">Already linked to this school: keep it</button>':""),2);
 drawCode()}
// One real input lies over 8 drawn boxes: the phone's own keyboard and paste work, and
// whatever is typed (small letters, a dash or not) becomes the 8 characters.
function drawCode(){var c=S.code,box="",odd=-1;
 for(var i=0;i<8;i++){var ch=c.charAt(i),bad=ch&&ALPHABET.indexOf(ch)<0;if(bad&&odd<0)odd=i;
  box+=(i==4?'<span class="dash" aria-hidden="true">&ndash;</span>':"")+'<span class="'+(bad?"odd":ch?"has":i==c.length?"at":"")+'">'+esc(ch)+"</span>"}
 $("c8b").innerHTML=box;
 if(odd>=0){var w=c.charAt(odd),hint=(w=="O"||w=="0")?"It&rsquo;s probably a Q or D.":"Check it on your Add my sensor page.";
  $("out").innerHTML=st("warn","Codes never use "+esc(w)+". Check box "+(odd+1)+": "+hint)}
 else if($("out").firstChild&&$("out").firstChild.className.indexOf("warn")>=0)$("out").innerHTML="";
 $("b").disabled=odd>=0||c.length<8}
function typedCode(el){S.code=el.value.toUpperCase().replace(/[^A-Z0-9]/g,"").slice(0,8);if(el.value!=S.code)el.value=S.code;$("c8").className="code8";drawCode()}
function claim(takeover){var c=S.code;if(c.length<8)return;$("b").disabled=true;
 $("out").innerHTML=st("","Linking&hellip;");
 api("/api/claim",takeover?{code:c,takeover:"1"}:{code:c},2).then(function(r){
  if(r.ok){finish();return}
  if(r.owned){takeoverScreen();return}
  $("c8").className="code8 bad";$("out").innerHTML=st("bad",esc(r.detail));$("b").disabled=false;$("b").textContent="Try again"})}
function takeoverScreen(){S.screen="takeover";
 show('<span class="icon"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#f2b84b" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l10 18H2z"/><path d="M12 10v5"/><path d="M12 18h.01"/></svg></span>'+
  "<h1>This sensor belongs to another athlete</h1><p class=\"sub\">Make it yours and it comes off their account. Their history stays theirs.</p><div id=\"out\"></div>",
  '<button class="go" id="b" onclick="claim(true)">Make it mine</button><button class="ghost" onclick="codeScreen()">Cancel, it&rsquo;s not mine</button>',2)}

function finish(){api("/api/finish",{}).then(function(){S.screen="done";
 var facts=[["Sensor",S.id],["Wi-Fi",S.ssid],["Server",S.local?"the gym\u2019s base station":S.host]];if(!S.local)facts.push(["Linked to","your athlete account"]);
 var rows=facts.map(function(f){return "<div><span>"+f[0]+"</span><b>"+esc(f[1])+"</b></div>"}).join("");
 show('<div class="tick">&#10003;</div>'+(S.local?
   '<h1>Your sensor is on the gym&rsquo;s Wi-Fi</h1><p class="sub">One more step, for your coach: link sensor <b style="font-family:var(--mono);color:var(--ink)">'+esc(S.id)+"</b> to a rack in Room Layout.</p>":
   '<h1>Your sensor is ready</h1><p class="sub">Switch it on whenever you lift. It connects by itself.</p>')+
  '<div class="facts">'+rows+'</div><p class="note">The sensor&rsquo;s own Wi-Fi closes now. To set it up again, hold its button for 3 seconds.</p>',
  '<button class="go" onclick="window.close()">Close</button>',-1)})}

api("/api/info").then(function(r){S.id=r.id;S.domain=r.domain;S.linked=r.linked;$("sid").textContent=r.id;
 // Setting up again: the sensor remembers its school, so its school code is filled in.
 var end="."+r.domain;if(r.linked&&r.linked.slice(-end.length)==end){S.sub=r.linked.slice(0,-end.length);S.pref=true}
 netsScreen()});
</script></body></html>)PAGE";
