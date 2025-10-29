window.mermaid && mermaid.initialize({ startOnLoad: true });
if (window.mermaid && window.document$) {
    document$.subscribe(() =>
        mermaid.init(undefined, document.querySelectorAll('.mermaid'))
    );
}