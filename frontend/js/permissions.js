// Pantalla de permisos de acceso. El comportamiento depende del actor autenticado:
// - un alumno gestiona sus permisos (cruza GET /organizations con GET /permissions y usa un switch por
//   organización, que llama a /permissions/grant o /permissions/revoke al cambiar);
// - una organización y un administrador solo consultan (GET /permissions también, pero de solo lectura:
//   sin switch, sin acciones), viendo qué alumnos les han concedido acceso.

const accessToken = localStorage.getItem("access_token");
const currentActorType = localStorage.getItem("actor_type");

// Sin sesión iniciada no se puede consultar esta pantalla: se redirige al login.
if (!accessToken) {
    window.location.href = "index.html";
}

const loadingState = document.getElementById("permissions-loading");
const emptyState = document.getElementById("permissions-empty");
const errorState = document.getElementById("permissions-error");
const noMatchesState = document.getElementById("permissions-no-matches");
const tableWrapper = document.getElementById("permissions-table-wrapper");
const tableBody = document.getElementById("permissions-table-body");
const tableHeadRow = document.getElementById("permissions-table-head-row");
const toggleError = document.getElementById("permission-toggle-error");

// Buscador: se aplica en memoria sobre los datos ya cargados, sin volver a llamar a la API.
const searchWrapper = document.getElementById("permissions-search-wrapper");
const searchInput = document.getElementById("permissions-search-input");

// Filas ya preparadas para renderizar. Se guardan para poder recalcular la lista visible al buscar, sin volver a pedirlas al backend.
let allRows = [];

// Ajusta el título, la descripción, las columnas de la tabla y el buscador según el actor autenticado:
// un alumno gestiona sus propios permisos; una organización o un administrador solo consultan, sin switch ni acciones.
if (currentActorType === "ORGANIZATION") {
    document.getElementById("permissions-title").textContent = "Autorizaciones recibidas";
    document.getElementById("permissions-description").textContent = "Alumnos que te han concedido acceso a sus certificados.";
    // Cabecera tabla de autorizaciones
    tableHeadRow.innerHTML = "<th>Alumno</th><th>Fecha de concesión</th>";
    searchInput.placeholder = "Buscar alumno...";
} else if (currentActorType === "ADMINISTRATOR") {
    document.getElementById("permissions-title").textContent = "Autorizaciones";
    document.getElementById("permissions-description").textContent = "Todos los permisos de acceso activos en la plataforma.";
    // Cabecera tabla de autorizaciones
    tableHeadRow.innerHTML = "<th>Alumno</th><th>Organización</th><th>Fecha de concesión</th>";
    searchInput.placeholder = "Buscar alumno u organización...";
} else {
    // Alumno: título y columnas ya definidos en el propio HTML.
    // Cabecera tabla de autorizaciones
    tableHeadRow.innerHTML = "<th>Organización</th><th>Tipo</th><th>Acceso</th>";
    searchInput.placeholder = "Buscar organización...";
}

// Construye la fila <tr> correcta según el actor autenticado (un alumno ve organizaciones con switch;
// una organización o un administrador ven permisos de solo lectura).
function buildPermissionRow(row) {
    if (currentActorType === "ORGANIZATION") {
        return buildOrganizationPermissionRow(row);
    }
    if (currentActorType === "ADMINISTRATOR") {
        return buildAdminPermissionRow(row);
    }
    return buildStudentPermissionRow(row);
}

// Devuelve el texto sobre el que se busca, según el actor autenticado
function getSearchableText(row) {
    if (currentActorType === "ORGANIZATION") {
        return `${row.student_name} ${formatDate(row.granted_at)}`;
    }
    if (currentActorType === "ADMINISTRATOR") {
        return `${row.student_name} ${row.organization_name} ${formatDate(row.granted_at)}`;
    }
    return `${row.organization_name} ${row.organization_type}`;
}

// Oculta los cuatro estados de la carga inicial
function hideAllStates() {
    loadingState.classList.add("d-none");
    emptyState.classList.add("d-none");
    errorState.classList.add("d-none");
    noMatchesState.classList.add("d-none");
    tableWrapper.classList.add("d-none");
}

// Búsqueda simple por contenido en función de los campos que tenga la tabla.
// ¿La fila coincide con el texto buscado?
function matchesSearch(row, searchText) {
    // si no hay texto a buscar
    if (!searchText) {
        return true;
    }
    // devuelve TRUE si la fila indicada contiene el texto de búsqueda introducido
    return getSearchableText(row).toLowerCase().includes(searchText);
}

// Recalcula la lista visible aplicando la búsqueda sobre los datos ya cargados, y vuelve a pintar la tabla
function applySearch() {
    // texto introducido en el buscador
    const searchText = searchInput.value.trim().toLowerCase();
    
    // Recorre todas las filas (allRows) y se queda con aquellas que la función (matchesSearch) = TRUE.
    //Es decir, con aquellas filas que se encuentre el texto buscado
    const filteredRows = allRows.filter(function (row) {
        return matchesSearch(row, searchText);
    });
    // Se oculta la tabla y el mensaje de no hay resultados
    tableWrapper.classList.add("d-none");
    noMatchesState.classList.add("d-none");

    // Si no hay resultados se muestra el mensaje de que no hay resultados
    if (filteredRows.length === 0) {
        noMatchesState.classList.remove("d-none");
        return;
    }
    // Se vacía la tabla
    tableBody.innerHTML = "";
    // Se recorren todas las filas en las que hay coincidencias y para cada una de ellas, se añade a la tabla de resultado
    filteredRows.forEach(function (row) {
        tableBody.appendChild(buildPermissionRow(row));
    });
    tableWrapper.classList.remove("d-none");
}

// Cierra la sesión y vuelve al login (mismo criterio que el resto de pantallas ante un 401).
function handleUnauthorized() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("actor_id");
    localStorage.removeItem("actor_type");
    localStorage.removeItem("display_name");
    window.location.href = "index.html";
}

// Extrae el mensaje de error devuelto por la API (string o lista de validación de FastAPI).
async function extractErrorMessage(response, fallback) {
    try {
        const data = await response.json();
        if (typeof data.detail === "string") {
            return data.detail;
        }
        if (Array.isArray(data.detail)) {
            return data.detail.map(function (item) { return item.msg; }).join(" ");
        }
    } catch (error) {
        // Respuesta sin JSON: se usa el mensaje genérico.
    }
    return fallback;
}

// Da formato de fecha en español a una fecha ISO devuelta por la API.
function formatDate(isoDate) {
    return new Date(isoDate).toLocaleDateString("es-ES");
}

// Construye la fila <tr> de una organización (vista de alumno): nombre, tipo y un switch que refleja si
// tiene permiso activo.
function buildStudentPermissionRow(organization) {
    const row = document.createElement("tr");

    // Atributo "checked" del switch: se calcula aparte para no utilizar un operador ternario dentro del HTML.
    let checkedAttribute = "";
    if (organization.active) {
        checkedAttribute = "checked";
    }

    row.innerHTML = `
        <td>${organization.organization_name}</td>
        <td>${organization.organization_type}</td>
        <td>
            <div class="form-check form-switch mb-0">
                <input
                    class="form-check-input permission-switch"
                    type="checkbox"
                    role="switch"
                    data-organization-id="${organization.organization_id}"
                    ${checkedAttribute}
                >
            </div>
        </td>
    `;

    return row;
}

// Construye la fila <tr> de un permiso (vista de organización): solo alumno y fecha, sin acciones.
function buildOrganizationPermissionRow(permission) {
    const row = document.createElement("tr");

    row.innerHTML = `
        <td>${permission.student_name}</td>
        <td>${formatDate(permission.granted_at)}</td>
    `;

    return row;
}

// Construye la fila <tr> de un permiso (vista de administrador): alumno, organización y fecha, sin acciones.
function buildAdminPermissionRow(permission) {
    const row = document.createElement("tr");

    row.innerHTML = `
        <td>${permission.student_name}</td>
        <td>${permission.organization_name}</td>
        <td>${formatDate(permission.granted_at)}</td>
    `;

    return row;
}

// Carga la vista de un alumno: cruza el listado completo de organizaciones con las que ya tienen permiso
// activo, y pinta un switch por organización.
async function loadStudentPermissions() {
    const [organizationsResponse, permissionsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/organizations`, { headers: { "Authorization": `Bearer ${accessToken}` } }),
        fetch(`${API_BASE_URL}/permissions`, { headers: { "Authorization": `Bearer ${accessToken}` } }),
    ]);

    if (organizationsResponse.status === 401 || permissionsResponse.status === 401) {
        handleUnauthorized();
        return;
    }

    if (!organizationsResponse.ok) {
        hideAllStates();
        errorState.textContent = await extractErrorMessage(organizationsResponse, "No se han podido cargar las organizaciones.");
        errorState.classList.remove("d-none");
        return;
    }

    if (!permissionsResponse.ok) {
        hideAllStates();
        errorState.textContent = await extractErrorMessage(permissionsResponse, "No se han podido cargar los permisos.");
        errorState.classList.remove("d-none");
        return;
    }

    const organizations = await organizationsResponse.json();
    const permissions = await permissionsResponse.json();

    // Ids de las organizaciones con permiso activo, para saber qué switches deben empezar marcados.
    const activeOrganizationIds = [];
    permissions.forEach(function (permission) {
        activeOrganizationIds.push(permission.organization_id);
    });

    hideAllStates();

    if (organizations.length === 0) {
        searchWrapper.classList.add("d-none");
        emptyState.classList.remove("d-none");
        return;
    }

    organizations.forEach(function (organization) {
        organization.active = activeOrganizationIds.includes(organization.organization_id);
    });

    // Hay organizaciones: se guardan para poder buscar en memoria y se muestra el buscador.
    allRows = organizations;
    searchWrapper.classList.remove("d-none");
    applySearch();
}

// Carga la vista de solo lectura de una organización o de un administrador: un único GET /permissions,
// cuya respuesta ya viene en el formato adecuado según el actor autenticado (buildPermissionRow decide cómo pintar cada fila).
async function loadReadOnlyPermissions() {
    const response = await fetch(`${API_BASE_URL}/permissions`, { headers: { "Authorization": `Bearer ${accessToken}` } });

    if (response.status === 401) {
        handleUnauthorized();
        return;
    }

    if (!response.ok) {
        hideAllStates();
        errorState.textContent = await extractErrorMessage(response, "No se han podido cargar los permisos.");
        errorState.classList.remove("d-none");
        return;
    }

    const permissions = await response.json();

    hideAllStates();

    if (permissions.length === 0) {
        searchWrapper.classList.add("d-none");
        emptyState.classList.remove("d-none");
        return;
    }

    // Hay permisos: se guardan para poder buscar en memoria y se muestra el buscador.
    allRows = permissions;
    searchWrapper.classList.remove("d-none");
    applySearch();
}

// Función principal: decide qué vista cargar según el actor autenticado.
async function loadPermissions() {
    hideAllStates();
    loadingState.classList.remove("d-none");
    toggleError.classList.add("d-none");

    try {
        if (currentActorType === "ORGANIZATION" || currentActorType === "ADMINISTRATOR") {
            await loadReadOnlyPermissions();
        } else {
            await loadStudentPermissions();
        }
    } catch (error) {
        hideAllStates();
        errorState.textContent = "No se han podido cargar los permisos.";
        errorState.classList.remove("d-none");
    }
}

// Al cambiar un switch se concede o revoca el permiso según su nuevo estado (solo existe esta interacción
// en la vista de alumno; en las vistas de solo lectura no hay ningún switch, así que nunca se dispara).
// Delegación de eventos sobre tableBody porque las filas se recrean cada vez que se llama a loadPermissions().
tableBody.addEventListener("change", async function (event) {
    const toggle = event.target.closest(".permission-switch");
    if (!toggle) {
        return;
    }

    toggleError.classList.add("d-none");

    const organizationId = Number(toggle.dataset.organizationId);
    const endpoint = toggle.checked ? "grant" : "revoke";
    toggle.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/permissions/${endpoint}`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${accessToken}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ organization_id: organizationId }),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            // El backend no ha aceptado el cambio: se revierte el switch a su estado anterior.
            toggle.checked = !toggle.checked;
            toggleError.textContent = await extractErrorMessage(response, "No se ha podido actualizar el permiso.");
            toggleError.classList.remove("d-none");
        } else {
            // Se mantiene sincronizado el estado en memoria (allRows) con el del botón seleccionable. Si no se actualizara
            // tras dar permiso a una organización, éste no saldría en el filtro, pese a haberlo concedido. 
            const matchingOrganization = allRows.find(function (organization) {
                return organization.organization_id === organizationId;
            });
            if (matchingOrganization) {
                matchingOrganization.active = toggle.checked;
            }
        }

    } catch (error) {
        toggle.checked = !toggle.checked;
        toggleError.textContent = "No se ha podido actualizar el permiso.";
        toggleError.classList.remove("d-none");
    } finally {
        toggle.disabled = false;
    }
});

// Búsqueda en tiempo real (mientras se escribe): recalcula la lista visible en memoria, sin llamar a la API.
// Manejador que gestionar el campo de búsqueda. 
searchInput.addEventListener("input", applySearch);

loadPermissions();
