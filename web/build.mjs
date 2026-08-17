import esbuild from "esbuild";

await esbuild.build({
  entryPoints: ["src/main.jsx"],
  bundle: true,
  minify: true,
  format: "iife",
  jsx: "automatic",
  target: ["es2020"],
  outfile: "../themes/blog-theme/static/js/effects-react.js",
  logLevel: "info",
});

console.log("effects-react.js built -> themes/blog-theme/static/js/");
