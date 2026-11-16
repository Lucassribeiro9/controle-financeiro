# Chart.js (vendorizado)

Versão 4.5.1, arquivo `chart.umd.min.js` copiado do pacote oficial.

Alteração local: a última linha `//# sourceMappingURL=chart.umd.min.js.map`
foi removida. O `.map` não é versionado e o `CompressedManifestStaticFilesStorage`
de produção falha no `collectstatic` quando a referência não resolve (#303).
Ao atualizar a versão, remova essa linha de novo.
