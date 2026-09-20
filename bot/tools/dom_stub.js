// Минимальный DOM-стаб, чтобы скрипт из SquirtCar_0.1.2.html выполнился в jsc.
var __els = {};
function __ctxStub() {
  return {
    clearRect(){}, beginPath(){}, moveTo(){}, lineTo(){}, stroke(){}, fill(){},
    setLineDash(){}, fillText(){}, measureText(){ return { width: 10 }; },
    strokeStyle:'', fillStyle:'', lineWidth:1, font:'', textAlign:'', globalAlpha:1,
  };
}
function __mkEl(id) {
  var el = {
    id: id,
    value: '',
    checked: true,
    textContent: '',
    innerHTML: '',
    className: '',
    width: 1100,
    height: 340,
    style: {},
    _classes: {},
    classList: {
      add(c){ el._classes[c] = true; },
      remove(c){ delete el._classes[c]; },
      toggle(c){ if (el._classes[c]) delete el._classes[c]; else el._classes[c] = true; },
      contains(c){ return !!el._classes[c]; },
    },
    addEventListener(){}, removeEventListener(){},
    querySelectorAll(){ return []; },
    appendChild(){}, removeChild(){},
    getContext(){ return __ctxStub(); },
    getAttribute(){ return null; },
    setAttribute(){},
    focus(){}, click(){},
  };
  return el;
}
var __theme = 'light';
var document = {
  documentElement: {
    setAttribute(k, v){ if (k === 'data-theme') __theme = v; },
    getAttribute(k){ return k === 'data-theme' ? __theme : null; },
  },
  body: { appendChild(){}, removeChild(){} },
  getElementById(id){ if (!__els[id]) __els[id] = __mkEl(id); return __els[id]; },
  createElement(){ return __mkEl('tmp'); },
  querySelectorAll(){ return []; },
  addEventListener(){},
};
var window = globalThis;
window.addEventListener = function(){};
var localStorage = {
  _d: {},
  getItem(k){ return this._d[k] === undefined ? null : this._d[k]; },
  setItem(k, v){ this._d[k] = String(v); },
};
var console = globalThis.console || { warn(){}, log(){}, error(){} };
if (!console.warn) console.warn = function(){};
var URL = { createObjectURL(){ return ''; }, revokeObjectURL(){} };
function Blob(){}
function setTimeout(fn){ return 0; }
