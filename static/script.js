function start() {
    let lang = localStorage.getItem("lang") || "ru";
    let text = {};

    const elements = getElements();

    const ids = {
        titleText: "title",
        subtitle: "subtitle",
        numberLabel: "number",
        degreeLabel: "degree",
        precisionLabel: "precision",
        complexLabel: "complex",
        analyticalLabel: "analytical",
        calculate: "calculate",
        resultTitle: "result",
        footer: "footer",
        supportButton: "support"
    };

    function getElements() {
        return {
            language: document.getElementById("language"),
            number: document.getElementById("number"),
            degree: document.getElementById("degree"),
            precision: document.getElementById("precision"),
            complexMode: document.getElementById("complexMode"),
            analytical: document.getElementById("analytical"),
            calculate: document.getElementById("calculate"),
            message: document.getElementById("message"),
            result: document.getElementById("result"),
            roots: document.getElementById("roots"),
            analyticalResult: document.getElementById("analyticalResult")
        };
    }

    function get(url) {
        return fetch(url + "?t=" + Date.now());
    }

    function setPlaceholder(element, value) {
        element.placeholder = value || "";
    }

    function clearMessage() {
        elements.message.classList.add("hidden");
        elements.message.textContent = "";
    }

    function showMessage(key) {
        const errors = text.errors || {};

        elements.message.textContent =
            errors[key] || errors.calculation_error || "Calculation error";

        elements.message.classList.remove("hidden");
    }

    function updateInterface() {
        for (const id in ids) {
            const element = document.getElementById(id);

            if (element && text[ids[id]]) {
                element.textContent = text[ids[id]];
            }
        }

        setPlaceholder(elements.number, text.numberPlaceholder);
        setPlaceholder(elements.degree, text.degreePlaceholder);
        setPlaceholder(elements.precision, text.precisionPlaceholder);

        elements.precision.title = text.precisionPlaceholder || "";
    }

    async function loadLanguage(code) {
        try {
            const response = await get("/language/" + code);

            if (!response.ok) {
                return;
            }

            text = await response.json();
            lang = code;

            localStorage.setItem("lang", lang);
            document.documentElement.lang = lang;

            updateInterface();
            clearMessage();
        } catch {
            showMessage("calculation_error");
        }
    }

    function addLanguages(list) {
        const current = Array.from(elements.language.options)
            .map(option => option.value);

        for (const code of list) {
            if (!current.includes(code)) {
                const option = document.createElement("option");

                option.value = code;
                option.textContent = code.toUpperCase();

                elements.language.appendChild(option);
            }
        }

        for (const option of Array.from(elements.language.options)) {
            if (!list.includes(option.value)) {
                option.remove();
            }
        }
    }

    async function loadLanguages(keepCurrent = true) {
        try {
            const response = await get("/languages");
            const list = await response.json();

            addLanguages(list);

            if (!list.length) {
                return;
            }

            const current = elements.language.value || lang;
            let selected = keepCurrent ? current : lang;

            if (!list.includes(selected)) {
                selected = list[0];
            }

            elements.language.value = selected;

            if (selected !== lang || !text.title) {
                await loadLanguage(selected);
            }
        } catch {
            showMessage("calculation_error");
        }
    }

    function showResult(data) {
        elements.roots.innerHTML = "";

        data.roots.forEach((root, index) => {
            const item = document.createElement("div");

            item.className = "root-item";

            if (data.roots.length > 1) {
                item.textContent = `x${index + 1} = ${root}`;
            } else {
                item.textContent = `x = ${root}`;
            }

            elements.roots.appendChild(item);
        });

        elements.analyticalResult.textContent = data.analytical || "";
        elements.result.classList.remove("hidden");
    }

    function getCalculationData() {
        return {
            number: elements.number.value,
            degree: elements.degree.value,
            precision: elements.precision.value,
            complex_mode: elements.complexMode.checked,
            analytical: elements.analytical.checked
        };
    }

    async function calculate() {
        clearMessage();
        elements.result.classList.add("hidden");
        elements.calculate.disabled = true;

        try {
            const response = await fetch("/calculate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(getCalculationData())
            });

            const answer = await response.json();

            if (!answer.ok) {
                showMessage(answer.error);
            } else {
                showResult(answer);
            }
        } catch {
            showMessage("calculation_error");
        } finally {
            elements.calculate.disabled = false;
        }
    }

    function addEvents() {
        elements.language.addEventListener("change", () => {
            loadLanguage(elements.language.value);
        });

        elements.number.addEventListener("input", clearMessage);
        elements.degree.addEventListener("input", clearMessage);
        elements.precision.addEventListener("input", clearMessage);

        elements.calculate.addEventListener("click", calculate);
    }

    async function init() {
        addEvents();

        await loadLanguages(false);

        setInterval(() => {
            loadLanguages(true);
        }, 3000);
    }

    init();
}

start();
