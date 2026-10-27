// setup_page.h — the page an athlete's phone opens when it joins the sensor's own
// Wi-Fi (EdgeAthlete-<id>), to set the sensor up with no computer (spec 14 Phase 8).
//
// Why it looks like this: it follows the approved boards (Final designs, F_Setup1–5):
// pick the Wi-Fi → its password, tried right away → where reps go (Remote server: type
// only the school's subdomain; Local install: the base station, filled in) → the code
// (remote only) → done. The sensor's Wi-Fi has no internet, so the page is this one
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
header{display:flex;flex-direction:column;gap:12px;padding:16px 16px 14px;border-bottom:1px solid var(--l)}
.top{display:flex;justify-content:space-between;align-items:center}
.top b{font-size:15px;font-weight:800}.top span{color:var(--m);font:12px var(--mono)}
.steps{display:flex;gap:18px}.step{display:flex;align-items:center;gap:6px;color:var(--m);font-size:12px;font-weight:800}
.step i{display:grid;place-items:center;width:20px;height:20px;border-radius:50%;border:1.5px solid var(--l2);font-style:normal;font-size:11px}
.step.now{color:var(--ink)}.step.now i{border-color:var(--lime);color:var(--lime)}
.step.done{color:var(--lime)}.step.done i{background:var(--lime);border-color:var(--lime);color:var(--bg)}
main{flex:1;display:flex;flex-direction:column;gap:14px;padding:20px 16px 0}
footer{display:flex;flex-direction:column;gap:10px;padding:14px 16px 26px}
h1{margin:0;font-size:26px;font-weight:850;letter-spacing:-.02em}
.sub{margin:-6px 0 0;color:var(--ink2);font-size:14px;line-height:1.45}
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
.sw button{flex:1;min-height:44px;border:0;border-radius:5px;background:none;color:var(--ink2);font-size:14px;font-weight:800}
.sw button.on{background:var(--lime);color:var(--bg)}
.addr{display:flex;flex-direction:column;gap:8px;padding:14px;background:var(--s);border:1px solid var(--l)}
.bar{display:flex;align-items:center;gap:8px;min-height:40px;padding:0 12px;background:var(--s2);border-radius:20px;font-size:15px;white-space:nowrap;overflow:hidden}
.bar span{color:var(--m)}.bar mark{padding:2px 4px;border-radius:4px;background:var(--lime);color:var(--bg);font-weight:800}
.row{display:flex;justify-content:space-between;align-items:center}
.tick{display:grid;place-items:center;width:64px;height:64px;margin-top:18px;border-radius:50%;background:var(--lime);color:var(--bg);font-size:34px;font-weight:900}
.facts{display:flex;flex-direction:column;background:var(--s);border:1px solid var(--l)}
.facts div{display:flex;justify-content:space-between;gap:12px;min-height:48px;align-items:center;padding:0 14px;border-top:1px solid var(--l);font-size:14px}
.facts div:first-child{border-top:0}.facts span{color:var(--m)}.facts b{text-align:right}
</style></head><body>
<header><div class="top"><b>Edge Athlete sensor</b><span id="sid"></span></div><div class="steps" id="steps"></div></header>
<main id="main"></main><footer id="foot"></footer>
<script>
var S={id:"",domain:"",linked:"",nets:[],ssid:"",pass:"",local:false,sub:"",host:"",gateway:"",screen:"nets"};
var $=function(i){return document.getElementById(i)};
function esc(t){return String(t).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
// Every request tries again for a while: the phone drops off the sensor's Wi-Fi for a
// moment whenever the sensor changes channel to join the chosen network.
function api(path,body,tries){tries=tries==null?8:tries;
 var o=body?{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:new URLSearchParams(body).toString()}:{};
 return fetch(path,o).then(function(r){return r.json()}).catch(function(e){
  if(tries<=0)throw e;return new Promise(function(ok){setTimeout(ok,1500)}).then(function(){return api(path,body,tries-1)})})}
function steps(n){var names=S.local?["Wi-Fi","Server"]:["Wi-Fi","Server","Code"];
 $("steps").innerHTML=n<0?"":names.map(function(t,i){var c=i<n?"done":i==n?"now":"";
  return '<span class="step '+c+'"><i>'+(i<n?"&#10003;":i+1)+"</i>"+t+"</span>"}).join("")}
function show(main,foot,step){steps(step);$("main").innerHTML=main;$("foot").innerHTML=foot||""}
function st(cls,text){return '<div class="st '+cls+'" id="st">'+text+"</div>"}
function bars(r){var n=r>-55?4:r>-67?3:r>-78?2:1,h="";for(var i=0;i<4;i++)h+='<i class="'+(i<n?"f":"")+'" style="height:'+(4+4*i)+'px"></i>';return '<span class="bars">'+h+"</span>"}

function netsScreen(rescan){S.screen="nets";
 var list=S.nets.length?S.nets.map(function(n,i){return '<button class="net'+(n.ssid==S.ssid?" on":"")+'" onclick="pick('+i+')"><b>'+esc(n.ssid)+"</b>"+(n.lock?"<small>&#128274;</small>":"")+bars(n.rssi)+"</button>"}).join(""):st("","Looking for Wi-Fi&hellip;");
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
 $("out").innerHTML=st("","Trying "+esc(S.ssid)+"&hellip;");
 api("/api/wifi",{ssid:S.ssid,password:S.pass}).then(function(){setTimeout(pollWifi,1500)})}
function pollWifi(){api("/api/wifi").then(function(r){
 if(S.screen!="pass")return;
 if(r.state=="connecting"){setTimeout(pollWifi,1000);return}
 if(r.state=="connected"){S.gateway=r.gateway;$("out").innerHTML=st("ok","Connected to "+esc(S.ssid));
  $("b").outerHTML='<button class="go" onclick="serverScreen()">Next</button>';return}
 var why={wrong_password:"Wrong password. Check it and try again.",not_found:"Can&rsquo;t find "+esc(S.ssid)+". It may be out of range, or 5 GHz only."}[r.state]||"Couldn&rsquo;t join "+esc(S.ssid)+". Try again.";
 if(r.state=="wrong_password")$("pbox").className="box bad";
 $("out").innerHTML=st("bad",why);$("b").disabled=false;$("b").textContent="Try again"})}

function serverScreen(){S.screen="server";
 if(!S.host)S.host=S.gateway||"192.168.4.1";
 var sw='<div class="sw"><button class="'+(S.local?"":"on")+'" onclick="S.local=false;serverScreen()">Remote server</button><button class="'+(S.local?"on":"")+'" onclick="S.local=true;serverScreen()">Local install</button></div>'+
  '<p class="note" style="margin-top:-8px">'+(S.local?"In the gym, on the base station&rsquo;s own Wi-Fi.":"At home or anywhere with internet: your school&rsquo;s server.")+"</p>";
 if(S.local){show("<h1>Where to send reps</h1>"+sw+
   '<label class="f"><span class="caps">Base station</span><span class="box"><input id="host" value="'+esc(S.host)+'" readonly></span></label>'+
   '<div class="row" style="margin-top:-6px"><span class="note">Filled in from the gym&rsquo;s Wi-Fi.</span><button class="link" style="min-height:36px" onclick="var h=$(\'host\');h.readOnly=false;h.focus()">Change</button></div>'+
   '<div id="out"></div><p class="note">No code on a local install: your coach links the sensor to a rack.</p>',
   '<button class="go" id="b" onclick="checkServer()">Finish</button>',1);return}
 var sub=S.sub||"test";
 show("<h1>Where to send reps</h1>"+sw+
  '<div class="addr"><span class="caps">Your login link looks like this</span><div class="bar"><span>&#128274;</span><span><span>https://</span><mark id="mk">'+esc(sub)+"</mark><span>."+esc(S.domain)+'/&hellip;</span></span></div>'+
  '<p class="note" style="color:var(--ink2)">Type only the <b style="color:var(--lime)">green part</b>. Your coach sent it in your login link, and it&rsquo;s in the address bar on your athlete page.</p></div>'+
  '<label class="f"><span class="caps">School</span><span class="box" id="sbox"><input id="sub" autocapitalize="none" autocorrect="off" spellcheck="false" value="'+esc(S.sub)+'" placeholder="test" style="flex:none" oninput="$(\'mk\').textContent=this.value||\'test\';fit(this)"><em>.'+esc(S.domain)+"</em></span></label><div id=\"out\"></div>",
  '<button class="go" id="b" onclick="checkServer()">Next</button>',1);fit($("sub"))}
// The school field is exactly as wide as what's typed, so the domain follows right
// after it and reads as one address, like the picture above it.
function fit(el){var c=fit.c||(fit.c=document.createElement("canvas").getContext("2d"));
 c.font=getComputedStyle(el).font;el.style.width=Math.ceil(c.measureText(el.value||el.placeholder).width)+2+"px"}
function checkServer(){var body;
 if(S.local){S.host=$("host").value.trim();body={kind:"local",host:S.host}}
 else{S.sub=$("sub").value.trim().toLowerCase();if(!S.sub)return;body={kind:"remote",sub:S.sub}}
 $("b").disabled=true;$("out").innerHTML=st("","Looking for it&hellip;");
 api("/api/server",body).then(function(r){
  if(!r.ok){$("out").innerHTML=st("bad",esc(r.detail));$("b").disabled=false;if(!S.local)$("sbox").className="box bad";return}
  S.host=r.host;S.linked=r.linked;
  $("out").innerHTML=st("ok",S.local?"Found the base station":"Found Edge Athlete at "+esc(r.host));
  setTimeout(S.local?finish:codeScreen,900)})}

function codeScreen(){S.screen="code";
 show('<h1>Your sensor&rsquo;s code</h1><p class="sub">On your athlete page: My sensor &rarr; Add my sensor. It works once, for 15 minutes.</p>'+
  '<label class="f"><span class="caps">Code</span><span class="box" id="cbox"><input id="code" class="code" autocapitalize="characters" autocorrect="off" spellcheck="false" placeholder="K7MQ-2XPR" maxlength="9"></span></label><div id="out"></div>'+
  '<p class="note">This is the only thing the sensor needs from your account. Never type your password here.</p>',
  '<button class="go" id="b" onclick="claim()">Link my sensor</button>'+(S.linked?'<button class="link" onclick="finish()">Already linked to this school: keep it</button>':""),2)}
function claim(){var c=$("code").value.trim();if(!c)return;$("b").disabled=true;$("cbox").className="box";
 $("out").innerHTML=st("","Linking&hellip;");
 api("/api/claim",{code:c},2).then(function(r){
  if(r.ok){finish();return}
  $("cbox").className="box bad";$("out").innerHTML=st("bad",esc(r.detail));$("b").disabled=false;$("b").textContent="Try again"})}

function finish(){api("/api/finish",{}).then(function(){S.screen="done";
 var facts=[["Sensor",S.id],["Wi-Fi",S.ssid],["Server",S.local?"base station, "+S.host:S.host]];if(!S.local)facts.push(["Linked to","your athlete account"]);
 var rows=facts.map(function(f){return "<div><span>"+f[0]+"</span><b>"+esc(f[1])+"</b></div>"}).join("");
 show('<div class="tick">&#10003;</div>'+(S.local?
   '<h1>Your sensor is on the gym&rsquo;s Wi-Fi</h1><p class="sub">One more step, for your coach: link sensor <b style="font-family:var(--mono);color:var(--ink)">'+esc(S.id)+"</b> to a rack in Room Layout.</p>":
   '<h1>Your sensor is ready</h1><p class="sub">Switch it on whenever you lift. It connects by itself.</p>')+
  '<div class="facts">'+rows+'</div><p class="note">The sensor&rsquo;s own Wi-Fi closes now. To set it up again, hold its button for 3 seconds.</p>',
  '<button class="go" onclick="window.close()">Close</button>',-1)})}

api("/api/info").then(function(r){S.id=r.id;S.domain=r.domain;S.linked=r.linked;$("sid").textContent=r.id;netsScreen()});
</script></body></html>)PAGE";
