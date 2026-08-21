/**
 * 代码块一键复制（2026-08-22）
 * 为 .article-body 内每个 <pre> 注入右上角复制按钮；点击复制代码文本
 * （自动剔除 Chroma 行号 .ln），成功后按钮短暂显示「已复制」。
 * 文案由模板通过 data-* 注入（config/strings.yaml），JS 不硬编码可见文案。
 */
(function () {
  var root = document.querySelector(".article") || document.querySelector(".article-body");
  if (!root) return;
  var copyText = root.getAttribute("data-copy") || "复制";
  var copiedText = root.getAttribute("data-copied") || "已复制";
  var pres = root.querySelectorAll(".article-body pre");
  if (!pres.length) return;

  function fallbackCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
    } catch (e) {
      /* 忽略复制失败 */
    }
    document.body.removeChild(ta);
  }

  /** 提取代码文本：Chroma 结构剔除行号 .ln，保留每行前导缩进 */
  function codeText(pre) {
    var lines = pre.querySelectorAll(".line");
    if (lines.length) {
      var out = [];
      Array.prototype.forEach.call(lines, function (line) {
        var clone = line.cloneNode(true);
        var ln = clone.querySelector(".ln");
        if (ln) ln.remove();
        var text = (clone.innerText || clone.textContent || "").replace(/\s+$/, "");
        out.push(text);
      });
      return out.join("\n");
    }
    var code = pre.querySelector("code");
    if (code) return (code.innerText || code.textContent || "").trim();
    /* 无 <code> 时克隆 pre 并剔除复制按钮，避免把按钮文字复制进去 */
    var clone = pre.cloneNode(true);
    Array.prototype.forEach.call(clone.querySelectorAll(".code-copy"), function (b) {
      b.remove();
    });
    return (clone.innerText || clone.textContent || "").trim();
  }

  Array.prototype.forEach.call(pres, function (pre) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "code-copy";
    btn.textContent = copyText;
    btn.setAttribute("aria-label", copyText);
    pre.appendChild(btn);

    btn.addEventListener("click", function () {
      var text = codeText(pre);
      function done() {
        btn.textContent = copiedText;
        btn.setAttribute("data-copied", "true");
        setTimeout(function () {
          btn.textContent = copyText;
          btn.removeAttribute("data-copied");
        }, 2000);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () {
          fallbackCopy(text);
          done();
        });
      } else {
        fallbackCopy(text);
        done();
      }
    });
  });
})();
