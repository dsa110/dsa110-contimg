import{r as o,j as e}from"./index-DVX6Veo3.js";const K=({min:t,max:u,minValue:k,maxValue:p,step:n=1,label:z,unit:h="",onChange:b,onChangeComplete:i,showInputs:B=!0,histogram:g,className:P="",decimals:R=2,disabled:m=!1,formatValue:y})=>{const[r,w]=o.useState(k??t),[s,f]=o.useState(p??u),[S,j]=o.useState(null),M=o.useRef(null);o.useEffect(()=>{k!==void 0&&w(k),p!==void 0&&f(p)},[k,p]);const $=o.useCallback(a=>y?y(a):a.toFixed(R),[y,R]),F=o.useCallback(a=>(a-t)/(u-t)*100,[t,u]),D=o.useCallback(a=>{const l=t+a/100*(u-t),c=Math.round(l/n)*n;return Math.max(t,Math.min(u,c))},[t,u,n]),V=o.useCallback(a=>{if(m||!M.current)return;const l=M.current.getBoundingClientRect(),c=(a.clientX-l.left)/l.width*100,x=D(c),N=Math.abs(x-r),T=Math.abs(x-s);if(N<=T){const d=Math.min(x,s-n);w(d),b?.(d,s),i?.(d,s)}else{const d=Math.max(x,r+n);f(d),b?.(r,d),i?.(r,d)}},[m,D,r,s,n,b,i]),H=o.useCallback(a=>{const l=Math.min(parseFloat(a.target.value)||t,s-n);w(l),b?.(l,s)},[t,s,n,b]),U=o.useCallback(a=>{const l=Math.max(parseFloat(a.target.value)||u,r+n);f(l),b?.(r,l)},[u,r,n,b]),E=o.useCallback(()=>{i?.(r,s)},[r,s,i]),X=o.useCallback(a=>{const l=parseFloat(a.target.value),c=Math.min(l,s-n);w(c),b?.(c,s)},[s,n,b]),q=o.useCallback(a=>{const l=parseFloat(a.target.value),c=Math.max(l,r+n);f(c),b?.(r,c)},[r,n,b]),v=o.useCallback(()=>{j(null),i?.(r,s)},[r,s,i]),A=o.useCallback(()=>{w(t),f(u),b?.(t,u),i?.(t,u)},[t,u,b,i]),I=F(r),G=F(s);return e.jsxs("div",{className:`space-y-2 ${P}`,children:[e.jsxs("div",{className:"flex items-center justify-between",children:[z&&e.jsx("span",{className:"text-sm font-medium text-gray-700",children:z}),e.jsx("button",{type:"button",onClick:A,disabled:m,className:"text-xs text-blue-600 hover:text-blue-800 disabled:text-gray-400",children:"Reset"})]}),g&&g.length>0&&e.jsx("div",{className:"h-8 flex items-end gap-px",children:g.map((a,l)=>{const c=Math.max(...g),x=c>0?a/c*100:0,N=t+l/g.length*(u-t),d=t+(l+1)/g.length*(u-t)>=r&&N<=s;return e.jsx("div",{className:`flex-1 rounded-t transition-colors ${d?"bg-blue-400":"bg-gray-300"}`,style:{height:`${x}%`,minHeight:a>0?"2px":"0"}},l)})}),e.jsxs("div",{className:"relative h-6 flex items-center",children:[e.jsx("div",{ref:M,className:"absolute w-full h-2 bg-gray-200 rounded-full cursor-pointer",onClick:V,children:e.jsx("div",{className:"absolute h-full bg-blue-500 rounded-full",style:{left:`${I}%`,width:`${G-I}%`}})}),e.jsx("input",{type:"range",min:t,max:u,step:n,value:r,onChange:X,onMouseUp:v,onTouchEnd:v,onMouseDown:()=>j("min"),disabled:m,className:`absolute w-full h-2 appearance-none bg-transparent pointer-events-none
            [&::-webkit-slider-thumb]:pointer-events-auto
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-5
            [&::-webkit-slider-thumb]:h-5
            [&::-webkit-slider-thumb]:bg-white
            [&::-webkit-slider-thumb]:border-2
            [&::-webkit-slider-thumb]:border-blue-500
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:shadow
            [&::-webkit-slider-thumb]:cursor-grab
            [&::-webkit-slider-thumb]:active:cursor-grabbing
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-webkit-slider-thumb]:transition-transform
            [&::-moz-range-thumb]:pointer-events-auto
            [&::-moz-range-thumb]:appearance-none
            [&::-moz-range-thumb]:w-5
            [&::-moz-range-thumb]:h-5
            [&::-moz-range-thumb]:bg-white
            [&::-moz-range-thumb]:border-2
            [&::-moz-range-thumb]:border-blue-500
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:shadow
            [&::-moz-range-thumb]:cursor-grab`,style:{zIndex:S==="min"?2:1}}),e.jsx("input",{type:"range",min:t,max:u,step:n,value:s,onChange:q,onMouseUp:v,onTouchEnd:v,onMouseDown:()=>j("max"),disabled:m,className:`absolute w-full h-2 appearance-none bg-transparent pointer-events-none
            [&::-webkit-slider-thumb]:pointer-events-auto
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:w-5
            [&::-webkit-slider-thumb]:h-5
            [&::-webkit-slider-thumb]:bg-white
            [&::-webkit-slider-thumb]:border-2
            [&::-webkit-slider-thumb]:border-blue-500
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:shadow
            [&::-webkit-slider-thumb]:cursor-grab
            [&::-webkit-slider-thumb]:active:cursor-grabbing
            [&::-webkit-slider-thumb]:hover:scale-110
            [&::-webkit-slider-thumb]:transition-transform
            [&::-moz-range-thumb]:pointer-events-auto
            [&::-moz-range-thumb]:appearance-none
            [&::-moz-range-thumb]:w-5
            [&::-moz-range-thumb]:h-5
            [&::-moz-range-thumb]:bg-white
            [&::-moz-range-thumb]:border-2
            [&::-moz-range-thumb]:border-blue-500
            [&::-moz-range-thumb]:rounded-full
            [&::-moz-range-thumb]:shadow
            [&::-moz-range-thumb]:cursor-grab`,style:{zIndex:S==="max"?2:1}})]}),B?e.jsxs("div",{className:"flex items-center gap-2 text-sm",children:[e.jsxs("div",{className:"flex-1",children:[e.jsx("label",{className:"sr-only",children:"Minimum value"}),e.jsxs("div",{className:"relative",children:[e.jsx("input",{type:"number",min:t,max:s-n,step:n,value:r,onChange:H,onBlur:E,disabled:m,className:"w-full px-2 py-1 pr-8 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"}),h&&e.jsx("span",{className:"absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs",children:h})]})]}),e.jsx("span",{className:"text-gray-400",children:"—"}),e.jsxs("div",{className:"flex-1",children:[e.jsx("label",{className:"sr-only",children:"Maximum value"}),e.jsxs("div",{className:"relative",children:[e.jsx("input",{type:"number",min:r+n,max:u,step:n,value:s,onChange:U,onBlur:E,disabled:m,className:"w-full px-2 py-1 pr-8 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"}),h&&e.jsx("span",{className:"absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs",children:h})]})]})]}):e.jsxs("div",{className:"flex justify-between text-sm text-gray-600",children:[e.jsxs("span",{children:[$(r),h&&` ${h}`]}),e.jsxs("span",{children:[$(s),h&&` ${h}`]})]})]})};export{K as R};
//# sourceMappingURL=RangeSlider-DlBl9Jvu.js.map
