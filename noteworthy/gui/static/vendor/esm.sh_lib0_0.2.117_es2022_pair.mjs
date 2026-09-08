/* esm.sh - lib0@0.2.117/pair */
var o=class{constructor(t,r){this.left=t,this.right=r}},c=(e,t)=>new o(e,t),s=(e,t)=>new o(t,e),h=(e,t)=>e.forEach(r=>t(r.left,r.right)),n=(e,t)=>e.map(r=>t(r.left,r.right));export{o as Pair,c as create,s as createReversed,h as forEach,n as map};
//# sourceMappingURL=pair.mjs.map