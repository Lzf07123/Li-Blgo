(function () {
  "use strict";

  function enhance(select) {
    if (!select || select.dataset.customDropdown === "1") return;
    select.dataset.customDropdown = "1";

    var label = select.getAttribute("aria-label") || select.name || "";
    var wrap = document.createElement("div");
    wrap.className = "custom-select";

    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "custom-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    if (label) trigger.setAttribute("aria-label", label);

    var valueEl = document.createElement("span");
    valueEl.className = "custom-select-value";

    var chevron = document.createElement("span");
    chevron.className = "custom-select-chevron";
    chevron.setAttribute("aria-hidden", "true");
    chevron.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';

    trigger.appendChild(valueEl);
    trigger.appendChild(chevron);

    var menu = document.createElement("ul");
    menu.className = "custom-select-menu";
    menu.setAttribute("role", "listbox");
    menu.hidden = true;

    var optionEls = [];
    Array.prototype.forEach.call(select.options, function (opt) {
      var li = document.createElement("li");
      li.className = "custom-select-option" + (opt.selected ? " is-selected" : "");
      li.setAttribute("role", "option");
      li.setAttribute("aria-selected", opt.selected ? "true" : "false");
      li.dataset.value = opt.value;
      li.textContent = opt.textContent;
      li.tabIndex = -1;
      menu.appendChild(li);
      optionEls.push(li);
    });

    select.classList.add("custom-select-native");
    select.setAttribute("aria-hidden", "true");
    select.tabIndex = -1;
    select.parentNode.insertBefore(wrap, select);
    wrap.appendChild(trigger);
    wrap.appendChild(menu);

    function syncValue() {
      var selected = select.options[select.selectedIndex];
      valueEl.textContent = selected ? selected.textContent : "";
      optionEls.forEach(function (li) {
        var isSelected = li.dataset.value === select.value;
        li.classList.toggle("is-selected", isSelected);
        li.setAttribute("aria-selected", isSelected ? "true" : "false");
      });
    }

    function activeOption() {
      return menu.querySelector(".is-active") ||
        menu.querySelector(".is-selected") ||
        optionEls[0];
    }

    function setActive(li) {
      optionEls.forEach(function (el) { el.classList.remove("is-active"); });
      if (li) {
        li.classList.add("is-active");
        li.focus();
      }
    }

    function open() {
      menu.hidden = false;
      wrap.classList.add("is-open");
      trigger.setAttribute("aria-expanded", "true");
      setActive(activeOption());
    }

    function close() {
      menu.hidden = true;
      wrap.classList.remove("is-open");
      trigger.setAttribute("aria-expanded", "false");
    }

    function choose(li) {
      if (!li) return;
      select.value = li.dataset.value;
      syncValue();
      close();
      trigger.focus();
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    trigger.addEventListener("click", function () {
      if (menu.hidden) open();
      else close();
    });

    optionEls.forEach(function (li) {
      li.addEventListener("click", function () { choose(li); });
      li.addEventListener("mouseenter", function () { setActive(li); });
    });

    trigger.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp" ||
          e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });

    menu.addEventListener("keydown", function (e) {
      var idx = Math.max(optionEls.indexOf(activeOption()), 0);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive(optionEls[Math.min(idx + 1, optionEls.length - 1)]);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive(optionEls[Math.max(idx - 1, 0)]);
      } else if (e.key === "Home") {
        e.preventDefault();
        setActive(optionEls[0]);
      } else if (e.key === "End") {
        e.preventDefault();
        setActive(optionEls[optionEls.length - 1]);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        choose(activeOption());
      } else if (e.key === "Escape") {
        e.preventDefault();
        close();
        trigger.focus();
      }
    });

    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) close();
    });

    syncValue();
  }

  document.querySelectorAll("select[data-custom-dropdown]").forEach(enhance);
})();
