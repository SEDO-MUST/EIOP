const App = {
    urls: PEOPLE_URLS,
    refreshInterval: 30000,
    searchDelay: 350
};

const State = {
    page: 1,
    searchTimer: null
};

const DOM = {
    table: document.getElementById("userTableContainer"),
    toast: document.getElementById("toastContainer"),
    requestModal: document.getElementById("requestModal"),
    profileModal: document.getElementById("profileModal"),
    requestBody: document.getElementById("requestModalBody"),
    profileBody: document.getElementById("profileModalBody"),
    requestTitle: document.getElementById("requestModalTitle"),
    search: document.getElementById("searchInput"),
    role: document.getElementById("roleFilter"),
    type: document.getElementById("typeFilter"),
    status: document.getElementById("statusFilter"),
    permission: document.getElementById("permissionFilter"),
    reset: document.getElementById("resetFiltersBtn")
};

function getCookie(name) {
    let value = null;
    if (document.cookie) {
        document.cookie.split(";").forEach(cookie => {
            const item = cookie.trim();
            if (item.startsWith(name + "=")) {
                value = decodeURIComponent(item.substring(name.length + 1));
            }
        });
    }
    return value;
}

const csrftoken = getCookie("csrftoken");

class API {
    static async request(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            ...options,
            headers: {
                "X-CSRFToken": csrftoken,
                ...(options.headers || {})
            }
        });
        if (!response.ok) {
            throw new Error(await response.text());
        }
        return response;
    }
    static get(url) {
        return this.request(url);
    }
    static post(url, data = null) {
        return this.request(url, {
            method: "POST",
            body: data
        });
    }
}

const Utils = {
    loadingHTML() {
        return `<div class="loading-wrapper"><div class="loading-spinner"></div><div>Loading...</div></div>`;
    },
    showLoading(element) {
        if (element) {
            element.innerHTML = this.loadingHTML();
        }
    },
    getFilters() {
        return {
            search: DOM.search?.value || "",
            role: DOM.role?.value || "",
            type: DOM.type?.value || "",
            status: DOM.status?.value || "",
            permission: DOM.permission?.value || ""
        };
    },
    buildSearchURL(page = 1) {
        const params = new URLSearchParams(this.getFilters());
        params.set("page", page);
        return `${App.urls.search}?${params}`;
    }
};

class Modal {
    static open(modal) {
        if (!modal) return;
        modal.hidden = false;
        modal.style.display = "block";
        modal.classList.add("show");
        document.body.classList.add("modal-open");
    }
    static close(modal) {
        if (!modal) return;
        modal.classList.remove("show");
        modal.style.display = "none";
        modal.hidden = true;
        document.body.classList.remove("modal-open");
    }
    static closeAll() {
        this.close(DOM.requestModal);
        this.close(DOM.profileModal);
    }
}

class Toast {
    static show(type, message) {
        if (!DOM.toast) {
            alert(message);
            return;
        }
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = `<div class="toast-message">${message}</div><button class="toast-close">&times;</button>`;
        DOM.toast.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add("visible"));
        toast.querySelector(".toast-close").onclick = () => this.remove(toast);
        setTimeout(() => this.remove(toast), 4000);
    }
    static remove(toast) {
        if (!toast) return;
        toast.classList.remove("visible");
        setTimeout(() => toast.remove(), 300);
    }
    static success(message) {
        this.show("success", message);
    }
    static error(message) {
        this.show("error", message);
    }
}

class TableManager {
    static async load(page = 1) {
        State.page = page;
        Utils.showLoading(DOM.table);
        try {
            const response = await API.get(Utils.buildSearchURL(page));
            DOM.table.innerHTML = await response.text();
        } catch (error) {
            console.error(error);
            Toast.error("Unable to load users.");
        }
    }
}

class SelectManager {
    static populate(select, items, placeholder) {
        if (!select) return;
        select.innerHTML = "";
        select.appendChild(new Option(placeholder, ""));
        items.forEach(item => {
            select.appendChild(new Option(item.name, item.id));
        });
    }
}

class FilterManager {
    static async load() {
        try {
            const response = await API.get(App.urls.filterData);
            const data = await response.json();
            SelectManager.populate(DOM.role, data.roles || [], "All Roles");
            SelectManager.populate(DOM.type, data.types || [], "All Types");
            SelectManager.populate(DOM.status, data.statuses || [], "All Status");
            SelectManager.populate(DOM.permission, data.permissions || [], "All Permissions");
        } catch (error) {
            console.error(error);
            Toast.error("Unable to load filters.");
        }
    }
    static bind() {
        [DOM.role, DOM.type, DOM.status, DOM.permission].forEach(control => {
            control?.addEventListener("change", () => TableManager.load());
        });
        DOM.reset?.addEventListener("click", () => {
            DOM.search && (DOM.search.value = "");
            DOM.role && (DOM.role.value = "");
            DOM.type && (DOM.type.value = "");
            DOM.status && (DOM.status.value = "");
            DOM.permission && (DOM.permission.value = "");
            TableManager.load();
        });
    }
}

class SearchManager {
    static bind() {
        if (!DOM.search) return;
        DOM.search.addEventListener("input", () => {
            clearTimeout(State.searchTimer);
            State.searchTimer = setTimeout(() => TableManager.load(), App.searchDelay);
        });
    }
}

class UserManager {
    static async create() {
    try {

        console.log("1. Enter create()");
        console.log("URL:", App.urls.createRequest);

        const response = await API.get(App.urls.createRequest);

        console.log("2. Response:", response);

        const html = await response.text();

        console.log("3. HTML:");
        console.log(html);

        DOM.requestBody.innerHTML = html;
        const form = DOM.requestBody.querySelector("#requestForm");

        if (form) {

        UserManager.initializeRequestForm();

        form.addEventListener("submit", function (e) {

            e.preventDefault();

            FormManager.submit(form);

        });

        console.log("Request form initialized.");

        } else {
            console.error("requestForm not found.");
        }

        Modal.open(DOM.requestModal);

    } catch (error) {

        console.error(error);
        alert(error.stack);

    }
}

    static async profile(id) {
        try {
            Utils.showLoading(DOM.profileBody);
            Modal.open(DOM.profileModal);
            const response = await API.get(`${App.urls.profile}${id}/`);
            DOM.profileBody.innerHTML = await response.text();
        } catch (error) {
            console.error(error);
            Modal.close(DOM.profileModal);
            Toast.error("Unable to load profile.");
        }
    }
    static async execute(url, message) {
        try {
            const response = await API.post(url);
            const result = await response.json();
            if (!result.success) {
                Toast.error(result.message || "Operation failed.");
                return;
            }
            Toast.success(message);
            TableManager.load(State.page);
        } catch (error) {
            console.error(error);
            Toast.error("Server error.");
        }
    }
    static delete(id) {
        if (!confirm("Delete this user?")) return;
        this.execute(`${App.urls.delete}${id}/delete/`, "User deleted.");
    }
    static restore(id) {
        if (!confirm("Restore this user?")) return;
        this.execute(`${App.urls.restore}${id}/restore/`, "User restored.");
    }
    static promote(id) {
        if (!confirm("Promote this user?")) return;
        this.execute(`${App.urls.promote}${id}/promote/`, "Promotion request submitted.");
    }
    static demote(id) {
        if (!confirm("Demote this user?")) return;
        this.execute(`${App.urls.demote}${id}/demote/`, "Demotion request submitted.");
    }
    static cancel(id) {
        if (!confirm("Cancel this request?")) return;
        this.execute(`${App.urls.cancel}${id}/cancel/`, "Request cancelled.");
    }
    static audit(id) {
        location.href = `${App.urls.audit}${id}/`;
    }
}

class FormManager {
    static async submit(form) {
        const button = form.querySelector("button[type='submit']");
        if (button) button.disabled = true;
        try {
            const response = await API.post(form.action, new FormData(form));
            const result = await response.json();
            if (result.success) {
                Modal.close(DOM.requestModal);
                Toast.success(result.message);
                TableManager.load(State.page);
                return;
            }
            if (result.html) {
                DOM.requestBody.innerHTML = result.html;
            }
        } catch (error) {
            console.error(error);
            Toast.error("Unable to submit request.");
        } finally {
            if (button) button.disabled = false;
        }
    }
}

class RefreshManager {
    static start() {
        setInterval(() => TableManager.load(State.page), App.refreshInterval);
    }
}

document.addEventListener("submit", e => {
    if (e.target.id !== "requestForm") return;
    e.preventDefault();
    FormManager.submit(e.target);
});
innerHTML
document.addEventListener("click", e => {
    const target = e.target.closest("*");
    if (!target) return;
    if (target.id === "createUserBtn" || target.id === "createUserBtnSmall") {
        UserManager.create();
        return;
    }
    if (target.classList.contains("user-row")) {
        UserManager.profile(target.dataset.userId);
        return;
    }
    const actions = {
        "delete-user-btn": () => UserManager.delete(target.dataset.userId),
        "restore-user-btn": () => UserManager.restore(target.dataset.userId),
        "promote-user-btn": () => UserManager.promote(target.dataset.userId),
        "demote-user-btn": () => UserManager.demote(target.dataset.userId),
        "audit-btn": () => UserManager.audit(target.dataset.userId)
    };
    for (const key in actions) {
        if (target.classList.contains(key)) {
            e.stopPropagation();
            actions[key]();
            return;
        }
    }
    if (target.matches(".pagination a")) {
        e.preventDefault();
        const page = target.dataset.page;
        if (page) TableManager.load(page);
        return;
    }
    if (target.matches("[data-close-modal]")) {
        Modal.close(target.closest(".modal"));
        return;
    }
    if (target.classList.contains("modal")) {
        Modal.close(target);
    }
});

document.addEventListener("keydown", e => {
    if (e.key === "Escape") Modal.closeAll();
});

class PeopleApp {
    static async init() {
        await FilterManager.load();
        FilterManager.bind();
        SearchManager.bind();
        await TableManager.load();
        RefreshManager.start();
    }
}

class UserManager {

    static initializeRequestForm() {

        const form = document.getElementById("requestForm");

        if (!form) return;

        const userType = form.querySelector("#user_type");
        const common = form.querySelector("#commonSection");
        const staff = form.querySelector("#staffSection");
        const manager = form.querySelector("#managerSection");
        const admin = form.querySelector("#adminSection");

        function setSection(section, visible) {

            section.style.display = visible ? "block" : "none";

            section.querySelectorAll("input,select,textarea").forEach(field => {

                field.disabled = !visible;

                if (field.hasAttribute("data-required")) {
                    field.required = visible;
                }

            });

        }

        function setCommon(enabled) {

            common.style.display = enabled ? "block" : "none";

            common.querySelectorAll(".common-field").forEach(field => {

                field.disabled = !enabled;

                if (field.hasAttribute("data-required")) {
                    field.required = enabled;
                }

            });

        }

        function update() {

            setCommon(false);

            setSection(staff,false);
            setSection(manager,false);
            setSection(admin,false);

            switch(userType.value){

                case "STAFF":

                    setCommon(true);
                    setSection(staff,true);
                    break;

                case "MANAGER":

                    setCommon(true);
                    setSection(manager,true);
                    break;

                case "ORG_ADMIN":

                    setCommon(true);
                    setSection(admin,true);
                    break;

            }

        }

        userType.addEventListener("change",update);

        update();

    }

}

document.addEventListener("DOMContentLoaded", () => PeopleApp.init());