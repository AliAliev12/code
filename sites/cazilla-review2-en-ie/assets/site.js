(function(){
  'use strict';
  var AGE_COOKIE='cazilla_review2_ie_age_ok';
  var COOKIE_COOKIE='cazilla_review2_ie_cookie_choice';
  var AGE_TTL=3*24*60*60;
  var ageGate=document.getElementById('ageGate');
  var cookieGate=document.getElementById('cookieGate');
  var content=document.getElementById('siteContent');
  var ageUnder=document.getElementById('ageUnder');
  var ageOk=document.getElementById('ageOk');
  var cookieAccept=document.getElementById('cookieAccept');
  var cookieReject=document.getElementById('cookieReject');

  function getCookie(name){
    var m=document.cookie.match(new RegExp('(?:^|; )'+name.replace(/([.$?*|{}()\[\]\\/+^])/g,'\\$1')+'=([^;]*)'));
    return m?decodeURIComponent(m[1]):'';
  }
  function setCookie(name,val,maxAge){
    document.cookie=name+'='+encodeURIComponent(val)+';path=/;max-age='+String(maxAge)+';SameSite=Lax';
  }
  function show(el){if(!el)return;el.removeAttribute('hidden');document.body.classList.add('isLocked');}
  function hide(el){if(!el)return;el.setAttribute('hidden','hidden');if((!ageGate||ageGate.hasAttribute('hidden'))&&(!cookieGate||cookieGate.hasAttribute('hidden'))){document.body.classList.remove('isLocked');}}
  function setBlur(on){if(!content)return;content.classList.toggle('isBlurred',!!on);if(on){document.body.classList.add('isLocked');}}

  function init(){
    if(getCookie(AGE_COOKIE)==='1'){
      hide(ageGate);setBlur(false);
      if(!getCookie(COOKIE_COOKIE)){show(cookieGate);} else {hide(cookieGate);}
      return;
    }
    show(ageGate);hide(cookieGate);setBlur(false);
  }

  if(ageUnder){ageUnder.addEventListener('click',function(){hide(ageGate);setBlur(true);});}
  if(ageOk){ageOk.addEventListener('click',function(){setCookie(AGE_COOKIE,'1',AGE_TTL);hide(ageGate);setBlur(false);if(!getCookie(COOKIE_COOKIE)){show(cookieGate);}});}
  if(cookieAccept){cookieAccept.addEventListener('click',function(){setCookie(COOKIE_COOKIE,'accept',365*24*60*60);hide(cookieGate);});}
  if(cookieReject){cookieReject.addEventListener('click',function(){setCookie(COOKIE_COOKIE,'reject',365*24*60*60);hide(cookieGate);});}
  init();
})();
