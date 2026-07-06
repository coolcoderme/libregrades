/** LibreGrades portal UX: keyboard shortcuts, command palette, grade undo */
(function () {
  function initGradebookKeyboard() {
    var table = document.querySelector(".table-bordered");
    if (!table) return;
    var inputs = table.querySelectorAll('input[type="number"], input[type="text"]');
    var lastGradeId = null;
    inputs.forEach(function (input, idx) {
      input.addEventListener("keydown", function (e) {
        var cols = table.querySelectorAll("tbody tr:first-child input").length || 1;
        var next = idx;
        if (e.key === "ArrowRight") next = idx + 1;
        else if (e.key === "ArrowLeft") next = idx - 1;
        else if (e.key === "ArrowDown") next = idx + cols;
        else if (e.key === "ArrowUp") next = idx - cols;
        else if (e.key === "Enter") {
          input.dispatchEvent(new Event("change", { bubbles: true }));
          return;
        } else if (e.ctrlKey && e.key === "z") {
          e.preventDefault();
          return;
        } else return;
        e.preventDefault();
        if (inputs[next]) {
          inputs[next].focus();
          inputs[next].classList.add("gradebook-cell-focus");
        }
      });
      input.addEventListener("change", function () {
        var form = input.closest("form");
        if (form) {
          var hid = form.querySelector('input[name="grade_id"]');
          if (hid) lastGradeId = hid.value;
        }
      });
      input.addEventListener("blur", function () {
        input.classList.remove("gradebook-cell-focus");
      });
    });
    document.addEventListener("keydown", function (e) {
      if (e.ctrlKey && e.key === "z" && lastGradeId) {
        var csrf = document.querySelector("[name=csrfmiddlewaretoken]");
        if (!csrf) return;
        var body = new FormData();
        body.append("grade_id", lastGradeId);
        body.append("csrfmiddlewaretoken", csrf.value);
        fetch("/api/grade-undo/", { method: "POST", body: body, credentials: "same-origin" });
      }
    });
  }

  function initCommandPalette() {
    var modal = document.createElement("div");
    modal.id = "command-palette";
    modal.className = "command-palette d-none";
    modal.innerHTML =
      '<div class="command-palette-backdrop"></div><div class="command-palette-panel card shadow">' +
      '<input type="search" class="form-control form-control-lg" placeholder="Jump to feature…" id="cmd-input">' +
      '<ul class="list-group list-group-flush" id="cmd-list"></ul></div>';
    document.body.appendChild(modal);
    var input = document.getElementById("cmd-input");
    var list = document.getElementById("cmd-list");
    var items = [];

    function openPalette() {
      modal.classList.remove("d-none");
      input.value = "";
      input.focus();
      fetch("/api/command-palette/", { credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          items = data.items || [];
          render("");
        });
    }

    function closePalette() {
      modal.classList.add("d-none");
    }

    function render(q) {
      list.innerHTML = "";
      var ql = q.toLowerCase();
      var navLinks = [
        { label: "Home — Dashboard", href: "/" },
        { label: "Grades", href: "/grades/" },
        { label: "My Sections", href: "/teacher/sections/" },
        { label: "Features — Wave 1", href: "/features/" },
        { label: "Advanced — Wave 2", href: "/features/advanced/" },
        { label: "Wave 3", href: "/features/wave3/" },
        { label: "Wave 4", href: "/features/wave4/" },
        { label: "Global search", href: "/search/" },
        { label: "Preferences", href: "/preferences/" },
      ];
      var merged = navLinks.map(function (n) {
        return { num: "→", label: n.label, href: n.href };
      }).concat(
        items.map(function (it) {
          return { num: it.num, label: it.label, href: "/features/advanced/" };
        })
      );
      merged
        .filter(function (it) {
          return !ql || it.label.toLowerCase().indexOf(ql) >= 0;
        })
        .slice(0, 14)
        .forEach(function (it) {
          var li = document.createElement("li");
          li.className = "list-group-item list-group-item-action";
          li.textContent = it.num + "  " + it.label;
          li.addEventListener("click", function () {
            window.location.href = it.href;
            closePalette();
          });
          list.appendChild(li);
        });
      if (!list.children.length) {
        var empty = document.createElement("li");
        empty.className = "list-group-item text-muted";
        empty.textContent = "No matches";
        list.appendChild(empty);
      }
    }

    input.addEventListener("input", function () {
      render(input.value);
    });
    modal.querySelector(".command-palette-backdrop").addEventListener("click", closePalette);
    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        openPalette();
      }
      if (e.key === "Escape") closePalette();
    });
  }

  function initTourHint() {
    if (window.location.search.indexOf("tour=1") >= 0) {
      var main = document.querySelector("main");
      if (main) {
        var hint = document.createElement("div");
        hint.className = "alert alert-info";
        hint.textContent = "Guided tour: use Ctrl+K for command palette, Features menu for all tools.";
        main.prepend(hint);
      }
    }
  }

  function initFeatureFilter() {
    var input = document.getElementById("feature-filter");
    if (!input) return;
    input.addEventListener("input", function () {
      var q = input.value.toLowerCase().trim();
      document.querySelectorAll(".feature-group").forEach(function (group) {
        var visible = 0;
        group.querySelectorAll(".feature-item").forEach(function (item) {
          var match = !q || item.getAttribute("data-label").indexOf(q) >= 0;
          item.style.display = match ? "" : "none";
          if (match) visible++;
        });
        group.style.display = visible || !q ? "" : "none";
      });
    });
  }

  function initPWA() {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/static/sw.js").catch(function () {});
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initGradebookKeyboard();
    initCommandPalette();
    initTourHint();
    initFeatureFilter();
    initPWA();
  });
})();
