// Este script recupera y muestra el listado de certificados según el tipo de actor autenticado.

// guardamos en el almacen local las siguientes constante: token, actor_id y actor_type. No se pierde al cambiar de página.
const accessToken = localStorage.getItem("access_token");
const currentActorId = localStorage.getItem("actor_id");
const currentActorType = localStorage.getItem("actor_type");

// Sin sesión iniciada no se puede consultar el listado: se redirige al login.
if (!accessToken) {
    window.location.href = "index.html";
}

// guardamos en el almacen local las siguientes constante que después utilizaremos en la aplicación
const loadingState = document.getElementById("certificates-loading");
const emptyState = document.getElementById("certificates-empty");
const errorState = document.getElementById("certificates-error");
const noMatchesState = document.getElementById("certificates-no-matches");
const tableWrapper = document.getElementById("certificates-table-wrapper");
const tableBody = document.getElementById("certificates-table-body");

// Buscador y filtros: se aplican en memoria sobre los certificados ya cargados, sin volver a llamar a la API.
const filtersWrapper = document.getElementById("certificates-filters");
const searchInput = document.getElementById("certificates-search-input");
const statusFilter = document.getElementById("certificates-status-filter");
const originFilterWrapper = document.getElementById("certificates-origin-filter-wrapper");
const originFilter = document.getElementById("certificates-origin-filter");

// El filtro de origen (emitidos vs autorizados por permiso) solo aplica a una organización.
if (currentActorType === "ORGANIZATION") {
    originFilterWrapper.classList.remove("d-none");
}

// Certificados tal cual los devolvió la API. Se guardan para poder recalcular la lista
// visible cada vez que cambie la búsqueda o un filtro, sin volver a pedirlos al backend.
let allCertificates = [];

// Traducción del estado de registro devuelto por el backend (en inglés) para mostrarlo en español.
const REGISTRATION_STATUS_LABELS = {
    PENDING: "Pendiente",
    CONFIRMED: "Confirmado",
    ERROR: "Error",
};

// El botón "Emitir certificado" solo lo pueden usar organizaciones y administradores; se oculta para un alumno.
const issueCertificateLink = document.getElementById("issue-certificate-link");
if (issueCertificateLink && currentActorType === "STUDENT") {
    issueCertificateLink.classList.add("d-none");
}

// El enlace de autorizaciones lo puede usar cualquier actor: un alumno gestiona sus permisos (conceder/
// revocar); una organización o un administrador solo los consultan (permissions.js adapta la pantalla y
// las columnas de la tabla según el actor, sin switch ni acciones en esos dos casos).
const permissionsLink = document.getElementById("permissions-link");
if (permissionsLink) {
    permissionsLink.classList.remove("d-none");
    if (currentActorType !== "STUDENT") {
        permissionsLink.innerHTML = '<i class="bi bi-shield-lock me-1"></i>Autorizaciones';
    }
}

// La columna "Origen" (emitido vs acceso por permiso) solo tiene sentido para una organización:
// un administrador ve todos los certificados y un alumno solo ve los suyos, así que no aporta información.
const originColumnHeader = document.getElementById("origin-column-header");
if (originColumnHeader && currentActorType === "ORGANIZATION") {
    originColumnHeader.classList.remove("d-none");
}

// Según el tipo de actor autenticado, se consulta el endpoint de certificados correspondiente.
let endpoint;

if (currentActorType === "STUDENT") {
    endpoint = `${API_BASE_URL}/students/${currentActorId}/certificates`;
} else if (currentActorType === "ORGANIZATION") {
    endpoint = `${API_BASE_URL}/organizations/${currentActorId}/certificates`;
} else if (currentActorType === "ADMINISTRATOR") {
    endpoint = `${API_BASE_URL}/certificates`;
}

// Oculta todos los estados de la interfaz antes de mostrar el que corresponda (no afecta a la barra de búsqueda/filtros)
function hideAllStates() {
    loadingState.classList.add("d-none");
    emptyState.classList.add("d-none");
    errorState.classList.add("d-none");
    noMatchesState.classList.add("d-none");
    tableWrapper.classList.add("d-none");
}

// Devuelve el estado de un certificado para poder filtrar
function getEffectiveStatus(certificate) {
    if (certificate.revoked) {
        return "REVOKED";
    }
    return certificate.registration_status;
}

// Búsqueda simple por contenido: nombre certificado, alumno, curso y organización emisora.
function matchesSearch(certificate, searchText) {
    if (!searchText) {
        return true;
    }
    const haystack = [
        certificate.certificate_name,
        certificate.student_name,
        certificate.course_title,
        certificate.organization_name,
    ].join(" ").toLowerCase();

    return haystack.includes(searchText);
}

// Filtro por estado (Todos/Confirmado/Pendiente/Error/Revocado).
function matchesStatus(certificate, statusValue) {
    if (statusValue === "ALL") {
        return true;
    }
    return getEffectiveStatus(certificate) === statusValue;
}

// Filtro por origen (Todos/Emitidos por mi organización/Autorizados por alumnos).
function matchesOrigin(certificate, originValue) {
    if (originValue === "ALL") {
        return true;
    }
    return certificate.access_type === originValue;
}

// Recalcula la lista visible aplicando a la vez la búsqueda y los filtros activos sobre los certificados
// ya cargados, y vuelve a pintar la tabla.
function applyFilters() {
    const searchText = searchInput.value.trim().toLowerCase();
    const statusValue = statusFilter.value;
    // El filtro de origen solo existe para las organizaciones
    const originValue = currentActorType === "ORGANIZATION" ? originFilter.value : "ALL";
    
    //Se recorre todos los certificados (allCertificates) uno por uno (filter) y para cada certificado (certificate)
    // miro si se cumple la triple condicion (&&), si se cumple se añade el certificado a FilteredCertificates
    const filteredCertificates = allCertificates.filter(
        function (certificate) {
        return matchesSearch(certificate, searchText)
            && matchesStatus(certificate, statusValue)
            && matchesOrigin(certificate, originValue);
        }
    );

    //Se oculta la tabla y el aviso
    tableWrapper.classList.add("d-none");
    noMatchesState.classList.add("d-none");

    // Si no hay certificados filtrados muestra el aviso
    if (filteredCertificates.length === 0) {
        noMatchesState.classList.remove("d-none");
        return;
    }

    // Se recorre cada uno de los certificados filtrados y para cada uno de ellos se crea una fila con
    //la información del certificado y se añade a la tabla principal 
    tableBody.innerHTML = "";
    filteredCertificates.forEach(function (certificate) {
        tableBody.appendChild(buildCertificateRow(certificate));
    });
    tableWrapper.classList.remove("d-none");
    // Los botones de icono (Ver detalle/Revocar) recién creados necesitan inicializar tooltip.
    initActionTooltips();
}

// Devuelve la clase del badge (etiqueta estado) de Bootstrap según el estado del certificado (revocado tiene prioridad sobre registration_status).
function getStatusBadgeClass(certificate) {
    if (certificate.revoked) {
        return "bg-danger";
    }
    if (certificate.registration_status === "CONFIRMED") {
        return "bg-success";
    }
    if (certificate.registration_status === "PENDING") {
        return "bg-warning text-dark";
    }
    return "bg-danger";
}

// Devuelve el <td> de la columna "Origen" (solo para una organización); el origen lo indica el
// backend con access_type, no se deduce en el frontend comparando nombres ni otros datos.
function buildOriginCell(certificate) {
    if (currentActorType !== "ORGANIZATION") {
        return "";
    }
    if (certificate.access_type === "ISSUED") {
        return '<td><span class="badge bg-success">Emitido</span></td>';
    }
    return '<td><span class="badge bg-info text-dark">Autorizado</span></td>';
}

// Indica si el actor autenticado puede revocar este certificado: un administrador puede revocar
// cualquiera; una organización solo el que ella misma emitió; un alumno nunca. 
// Un certificado ya revocado no se puede volver a revocar.
function canRevoke(certificate) {
    if (certificate.revoked) {
        return false;
    }
    if (currentActorType === "ADMINISTRATOR") {
        return true;
    }
    if (currentActorType === "ORGANIZATION") {
        return certificate.access_type === "ISSUED";
    }
    return false;
}

// Construye la fila <tr> de la tabla a partir de un certificado devuelto por el backend.
function buildCertificateRow(certificate) {
    let statusLabel;

    if (certificate.revoked) {
        statusLabel = "Revocado";
    } else {
        // devuelve el valor traducido del campo estado registro. Si no hay una traducción, en vez de devolver null, devuelve el texto que tiene la variable sin traducir
        statusLabel = REGISTRATION_STATUS_LABELS[certificate.registration_status] || certificate.registration_status;
    }

    // El botón "Revocar" solo se añade cuando el actor puede revocar este certificado concreto.
    // Son botones de solo icono; el texto se muestra como tooltip de Bootstrap al pasar por encima.
    const revokeButton = canRevoke(certificate)
        ? `<button type="button" class="btn btn-sm btn-outline-danger ms-1 revoke-button" data-certificate-id="${certificate.certificate_id}" data-bs-toggle="tooltip" title="Revocar"><i class="bi bi-x-circle"></i></button>`
        : "";

    const row = document.createElement("tr");

    row.innerHTML = `
        <td>${certificate.certificate_name}</td>
        <td>${certificate.student_name}</td>
        <td>${certificate.course_title}</td>
        <td>${certificate.organization_name}</td>
        <td>${new Date(certificate.created_at).toLocaleDateString("es-ES")}</td>
        <td><span class="badge ${getStatusBadgeClass(certificate)}">${statusLabel}</span></td>
        ${buildOriginCell(certificate)}
        <td class="text-nowrap"><a class="btn btn-sm btn-outline-primary" href="certificate-detail.html?id=${certificate.certificate_id}" data-bs-toggle="tooltip" title="Ver detalle"><i class="bi bi-eye"></i></a>${revokeButton}</td>
    `;

    return row;
}

// Inicializa los tooltips de Bootstrap de los botones de icono de la tabla. 
// Se llama después de cada carga porque las filas se recrean.
function initActionTooltips() {
    tableBody.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (element) {
        new bootstrap.Tooltip(element);
    });
}

// Al pulsar el icono "Revocar" de una fila se abre el modal que pide el motivo (obligatorio); la petición
// a la API solo se envía al confirmar dentro del modal. Delegación de eventos sobre tableBody porque las
// filas (y sus botones "Revocar") se recrean cada vez que se carga el listado.
const revokeModalElement = document.getElementById("revoke-modal");
const revokeModal = new bootstrap.Modal(revokeModalElement);
const revokeReasonInput = document.getElementById("revoke-reason-input");
const revokeReasonError = document.getElementById("revoke-reason-error");
const revokeConfirmButton = document.getElementById("revoke-confirm-button");
const revokeConfirmButtonOriginalHTML = revokeConfirmButton.innerHTML;

// Guarda el botón de la fila sobre la que se pidió revocar, para saber a qué certificado afecta cuando se confirme en el modal.
let pendingRevokeButton = null;

tableBody.addEventListener("click", function (event) {
    const button = event.target.closest(".revoke-button");
    if (!button) {
        return;
    }

    pendingRevokeButton = button;
    revokeReasonInput.value = "";
    revokeReasonError.classList.add("d-none");
    revokeModal.show();
});

revokeConfirmButton.addEventListener("click", async function () {
    if (!pendingRevokeButton) {
        return;
    }

    const reason = revokeReasonInput.value.trim();

    // El motivo es obligatorio: si está vacío, se avisa dentro del propio modal y no se envía la petición.
    if (!reason) {
        revokeReasonError.classList.remove("d-none");
        return;
    }

    const button = pendingRevokeButton;
    const certificateId = button.dataset.certificateId;
    const buttonOriginalHTML = button.innerHTML;

    revokeConfirmButton.disabled = true;
    revokeConfirmButton.textContent = "Revocando...";
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span>';

    try {
        const response = await fetch(`${API_BASE_URL}/certificates/${certificateId}/revoke`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${accessToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ reason: reason }),
        });

        // Sesión no válida o caducada: se elimina y se vuelve al login.
        if (response.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("actor_id");
            localStorage.removeItem("actor_type");
            localStorage.removeItem("display_name");

            window.location.href = "index.html";
            return;
        }

        if (!response.ok) {
            revokeModal.hide();
            window.alert("No se ha podido revocar el certificado.");
            button.disabled = false;
            button.innerHTML = buttonOriginalHTML;
            return;
        }

        revokeModal.hide();
        // Se recarga el listado para que la fila pase a mostrar "Revocado" y el botón desaparezca.
        loadCertificates();

    } catch (error) {
        revokeModal.hide();
        window.alert("No se ha podido revocar el certificado.");
        button.disabled = false;
        button.innerHTML = buttonOriginalHTML;
    } finally {
        revokeConfirmButton.disabled = false;
        revokeConfirmButton.innerHTML = revokeConfirmButtonOriginalHTML;
        pendingRevokeButton = null;
    }
});

// Consulta la API y muestra la tabla, el mensaje de lista vacía o el mensaje de error según corresponda.
async function loadCertificates() {
    if (!endpoint) {
        return;
    }

    try {
        const response = await fetch(endpoint, {
            headers: {
                "Authorization": `Bearer ${accessToken}`,
            },
        });

        // Sesión no válida o caducada: se elimina y se vuelve al login.
        if (response.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("actor_id");
            localStorage.removeItem("actor_type");
            localStorage.removeItem("display_name");

            window.location.href = "index.html";
            return;
        }

        if (!response.ok) {
            throw new Error("Error al consultar los certificados");
        }

        // se obtiene los certificados que devuelve la API (en función del actor identificado). El JSON de respuesta se convierte en un array de objetivos JS.
        // Se guarda en allCertificates (sin filtrar) para poder recalcular la lista visible en memoria, sin volver a pedirla al backend.
        allCertificates = await response.json();

        hideAllStates();
        // si no hay ningún certificado (antes de aplicar ningún filtro), se devuelve el estado vacío definido en certificates.html; no tiene sentido mostrar el buscador.
        if (allCertificates.length === 0) {
            filtersWrapper.classList.add("d-none");
            emptyState.classList.remove("d-none");
            return;
        }

        // Hay certificados: se muestra el buscador/filtros y se pinta la lista visible según su estado actual
        // (los valores de búsqueda/filtro se conservan tal cual entre recargas, p.ej. tras revocar un certificado).
        filtersWrapper.classList.remove("d-none");
        applyFilters();

    } catch (error) {
        hideAllStates();
        filtersWrapper.classList.add("d-none");
        errorState.classList.remove("d-none");
    }
}

// Búsqueda en tiempo real (mientras se escribe) y filtros: recalculan la lista visible en memoria,
// sin volver a llamar a la API.
// Manejadores tanto del campo de búsqueda como de los filtros.
searchInput.addEventListener("input", applyFilters);
statusFilter.addEventListener("change", applyFilters);
originFilter.addEventListener("change", applyFilters);

// Llamamos a la función principal que ejecuta la carga de certificados en la tabla de contenido
loadCertificates();
