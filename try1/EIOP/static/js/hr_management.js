// ==========================================================
// HR MANAGEMENT
// ==========================================================

let currentPage = 1;

let selectedUser = null;

document.addEventListener(
    "DOMContentLoaded",
    function () {

        initializeEvents();

    }
);

// ==========================================================
// INITIALIZATION
// ==========================================================

function initializeEvents() {

    const search = document.getElementById(
        "searchInput"
    );

    if (search) {

        search.addEventListener(

            "keyup",

            debounce(function () {

                currentPage = 1;

                refreshUserTable();

            }, 300)

        );

    }

    [
        "roleFilter",
        "typeFilter",
        "statusFilter"
    ].forEach(id => {

        const element = document.getElementById(id);

        if (!element) return;

        element.addEventListener(
            "change",
            function () {

                currentPage = 1;

                refreshUserTable();

            }
        );

    });

    const reset = document.getElementById(
        "resetFilters"
    );

    if (reset) {

        reset.addEventListener(
            "click",
            resetFilters
        );

    }

    bindTableEvents();

}

// ==========================================================
// RESET FILTERS
// ==========================================================

function resetFilters() {

    document.getElementById(
        "searchInput"
    ).value = "";

    document.getElementById(
        "roleFilter"
    ).value = "";

    document.getElementById(
        "typeFilter"
    ).value = "";

    document.getElementById(
        "statusFilter"
    ).value = "";

    currentPage = 1;

    refreshUserTable();

}

// ==========================================================
// LOAD TABLE
// ==========================================================

function refreshUserTable() {

    const params = new URLSearchParams({

        search:
            document.getElementById(
                "searchInput"
            ).value,

        role:
            document.getElementById(
                "roleFilter"
            ).value,

        type:
            document.getElementById(
                "typeFilter"
            ).value,

        status:
            document.getElementById(
                "statusFilter"
            ).value,

        page: currentPage

    });

    fetch(

        "/hr/search/?"

        + params.toString(),

        {

            headers: {

                "X-Requested-With":

                    "XMLHttpRequest"

            }

        }

    )

    .then(response => response.text())

    .then(html => {

        document.getElementById(

            "user-table-container"

        ).innerHTML = html;

        bindTableEvents();

    })

    .catch(showAjaxError);

}

// ==========================================================
// TABLE EVENTS
// ==========================================================

function bindTableEvents() {

    document.querySelectorAll(

        ".user-row"

    ).forEach(row => {

        row.addEventListener(

            "click",

            function () {

                loadUserProfile(

                    this.dataset.userId

                );

            }

        );

    });

    document.querySelectorAll(

        ".page-number"

    ).forEach(button => {

        button.addEventListener(

            "click",

            function (e) {

                e.preventDefault();

                currentPage =

                    this.dataset.page;

                refreshUserTable();

            }

        );

    });

}
// ==========================================================
// LOAD USER PROFILE
// ==========================================================

function loadUserProfile(userId) {

    selectedUser = userId;

    highlightSelectedRow(userId);

    fetch(

        "/hr/profile/" + userId + "/",

        {

            headers: {

                "X-Requested-With":

                    "XMLHttpRequest"

            }

        }

    )

    .then(response => response.text())

    .then(html => {

        document.getElementById(

            "profile-panel"

        ).innerHTML = html;

        bindProfileEvents();

    })

    .catch(showAjaxError);

}

// ==========================================================
// HIGHLIGHT SELECTED USER
// ==========================================================

function highlightSelectedRow(userId) {

    document.querySelectorAll(

        ".user-row"

    ).forEach(row => {

        row.classList.remove(

            "table-primary"

        );

    });

    const row = document.querySelector(

        '.user-row[data-user-id="' +

        userId +

        '"]'

    );

    if (row) {

        row.classList.add(

            "table-primary"

        );

    }

}

// ==========================================================
// PROFILE EVENTS
// ==========================================================

function bindProfileEvents() {

    bindEditButton();

    bindDeleteButton();

    bindRestoreButton();

    bindPromoteButton();

    bindDemoteButton();

    bindAuditButton();

}

// ==========================================================
// EDIT
// ==========================================================

function bindEditButton() {

    const button = document.querySelector(

        ".edit-user-btn"

    );

    if (!button) return;

    button.addEventListener(

        "click",

        function () {

            openEditModal(

                this.dataset.user

            );

        }

    );

}

// ==========================================================
// DELETE
// ==========================================================

function bindDeleteButton() {

    const button = document.querySelector(

        ".delete-user-btn"

    );

    if (!button) return;

    button.addEventListener(

        "click",

        function () {

            deleteUser(

                this.dataset.user

            );

        }

    );

}

// ==========================================================
// RESTORE
// ==========================================================

function bindRestoreButton() {

    const button = document.querySelector(

        ".restore-user-btn"

    );

    if (!button) return;

    button.addEventListener(

        "click",

        function () {

            restoreUser(

                this.dataset.user

            );

        }

    );

}

// ==========================================================
// PROMOTE
// ==========================================================

function bindPromoteButton() {

    const button = document.querySelector(

        ".promote-user-btn"

    );

    if (!button) return;

    button.addEventListener(

        "click",

        function () {

            promoteUser(

                this.dataset.user

            );

        }

    );

}

// ==========================================================
// DEMOTE
// ==========================================================

function bindDemoteButton() {

    const button = document.querySelector(

        ".demote-user-btn"

    );

    if (!button) return;

    button.addEventListener(

        "click",

        function () {

            demoteUser(

                this.dataset.user

            );

        }

    );

}

// ==========================================================
// AUDIT
// ==========================================================

function bindAuditButton() {

    const button = document.querySelector(

        ".view-audit-btn"

    );

    if (!button) return;

    button.addEventListener(

        "click",

        function () {

            viewAudit(

                this.dataset.user

            );

        }

    );

}
// ==========================================================
// CREATE USER
// ==========================================================

const createButton = document.getElementById(
    "createUserButton"
);

if (createButton) {

    createButton.addEventListener(

        "click",

        openCreateModal

    );

}

function openCreateModal() {

    fetch(

        "/hr/request/create/",

        {

            headers: {

                "X-Requested-With":

                    "XMLHttpRequest"

            }

        }

    )

    .then(response => response.text())

    .then(html => {

        document.getElementById(

            "userModalContent"

        ).innerHTML = html;

        new bootstrap.Modal(

            document.getElementById(

                "userModal"

            )

        ).show();

        bindCreateForm();

    })

    .catch(showAjaxError);

}

function bindCreateForm() {

    const form = document.getElementById(

        "createUserForm"

    );

    if (!form) return;

    form.addEventListener(

        "submit",

        submitCreateRequest

    );

}

function submitCreateRequest(e) {

    e.preventDefault();

    const form = e.target;

    fetch(

        form.action,

        {

            method: "POST",

            body: new FormData(form),

            headers: {

                "X-CSRFToken":

                    getCSRFToken()

            }

        }

    )

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            bootstrap.Modal.getInstance(

                document.getElementById(

                    "userModal"

                )

            ).hide();

            showSuccess(

                data.message

            );

            refreshUserTable();

        }

        else {

            showError(

                data.message

            );

        }

    })

    .catch(showAjaxError);

}

// ==========================================================
// EDIT USER REQUEST
// ==========================================================

function openEditModal(userId) {

    fetch(

        "/hr/request/" +

        userId +

        "/edit/",

        {

            headers: {

                "X-Requested-With":

                    "XMLHttpRequest"

            }

        }

    )

    .then(response => response.text())

    .then(html => {

        document.getElementById(

            "userModalContent"

        ).innerHTML = html;

        new bootstrap.Modal(

            document.getElementById(

                "userModal"

            )

        ).show();

        bindEditForm();

    })

    .catch(showAjaxError);

}

function bindEditForm() {

    const form = document.getElementById(

        "editUserForm"

    );

    if (!form) return;

    form.addEventListener(

        "submit",

        submitEditRequest

    );

}

function submitEditRequest(e) {

    e.preventDefault();

    const form = e.target;

    fetch(

        form.action,

        {

            method: "POST",

            body: new FormData(form),

            headers: {

                "X-CSRFToken":

                    getCSRFToken()

            }

        }

    )

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            bootstrap.Modal.getInstance(

                document.getElementById(

                    "userModal"

                )

            ).hide();

            showSuccess(

                data.message

            );

            refreshUserTable();

            loadUserProfile(

                selectedUser

            );

        }

        else {

            showError(

                data.message

            );

        }

    })

    .catch(showAjaxError);

}

// ==========================================================
// DELETE USER
// ==========================================================

function deleteUser(userId) {

    if (

        !confirm(

            "Submit a delete request?"

        )

    ) return;

    fetch(

        "/hr/user/" +

        userId +

        "/delete/",

        {

            method: "POST",

            headers: {

                "X-CSRFToken":

                    getCSRFToken()

            }

        }

    )

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            showSuccess(

                data.message

            );

            refreshUserTable();

        }

        else {

            showError(

                data.message

            );

        }

    })

    .catch(showAjaxError);

}

// ==========================================================
// RESTORE USER
// ==========================================================

function restoreUser(userId) {

    fetch(

        "/hr/user/" +

        userId +

        "/restore/",

        {

            method: "POST",

            headers: {

                "X-CSRFToken":

                    getCSRFToken()

            }

        }

    )

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            showSuccess(

                data.message

            );

            refreshUserTable();

            loadUserProfile(userId);

        }

        else {

            showError(

                data.message

            );

        }

    })

    .catch(showAjaxError);

}

// ==========================================================
// PROMOTE
// ==========================================================

function promoteUser(userId) {

    if (

        !confirm(

            "Promote this staff member?"

        )

    ) return;

    fetch(

        "/hr/user/" +

        userId +

        "/promote/",

        {

            method: "POST",

            headers: {

                "X-CSRFToken":

                    getCSRFToken()

            }

        }

    )

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            showSuccess(

                data.message

            );

            refreshUserTable();

            loadUserProfile(userId);

        }

        else {

            showError(

                data.message

            );

        }

    })

    .catch(showAjaxError);

}

// ==========================================================
// DEMOTE
// ==========================================================

function demoteUser(userId) {

    if (

        !confirm(

            "Demote this manager?"

        )

    ) return;

    fetch(

        "/hr/user/" +

        userId +

        "/demote/",

        {

            method: "POST",

            headers: {

                "X-CSRFToken":

                    getCSRFToken()

            }

        }

    )

    .then(response => response.json())

    .then(data => {

        if (data.success) {

            showSuccess(

                data.message

            );

            refreshUserTable();

            loadUserProfile(userId);

        }

        else {

            showError(

                data.message

            );

        }

    })

    .catch(showAjaxError);

}

// ==========================================================
// AUDIT
// ==========================================================

function viewAudit(userId) {

    window.location.href =

        "/hr/audit/" +

        userId +

        "/";

}

// ==========================================================
// UTILITIES
// ==========================================================

function getCSRFToken() {

    return document.querySelector(

        "[name=csrfmiddlewaretoken]"

    ).value;

}

function debounce(func, wait) {

    let timeout;

    return function () {

        clearTimeout(timeout);

        timeout = setTimeout(

            () => func.apply(

                this,

                arguments

            ),

            wait

        );

    };

}

function showSuccess(message) {

    alert(message);

}

function showError(message) {

    alert(message);

}

function showAjaxError(error) {

    console.error(error);

    alert(

        "An unexpected error occurred."

    );

}