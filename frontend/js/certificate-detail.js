// Este script recupera y muestra el detalle de un certificado a partir del parámetro "id" de la URL.

const accessToken = localStorage.getItem("access_token");
const currentActorId = localStorage.getItem("actor_id");
const currentActorType = localStorage.getItem("actor_type");

// Sin sesión iniciada no se puede consultar el detalle: se redirige al login.
if (!accessToken) {
    window.location.href = "index.html";
}

// Permite leer los parámetros de la URL. certificateId se reutiliza tanto para cargar el detalle como para la descarga/visualización del certificao.
const params = new URLSearchParams(window.location.search);
const certificateId = params.get("id");

// guardamos en el almacenamiento local del ciente las siguientes constantes Se utilizarán en la app posteriormente.
const loadingState = document.getElementById("detail-loading");
const errorState = document.getElementById("detail-error");
const contentState = document.getElementById("detail-content");

// Traducción del estado de registro devuelto por el backend (en inglés), igual que en certificates.js.
const REGISTRATION_STATUS_LABELS = {
    PENDING: "Pendiente",
    CONFIRMED: "Confirmado",
    ERROR: "Error",
};

// Oculta los tres estados de la pantalla antes de mostrar el que corresponda.
function hideAllStates() {
    loadingState.classList.add("d-none");
    errorState.classList.add("d-none");
    contentState.classList.add("d-none");
}

// Muestra un mensaje de error concreto (sin id, 403, 404 o error genérico) y oculta el resto de estados.
function showError(message) {
    hideAllStates();
    errorState.textContent = message;
    errorState.classList.remove("d-none");
}

// Indica si el actor autenticado puede revocar este certificado: un administrador puede revocar
// cualquiera; una organización solo el que ella misma emitió (certificate.organization.id es la
// organización emisora); un alumno nunca. Misma lógica que canRevoke() en certificates.js.
function canRevoke(certificate) {
    if (certificate.revoked) {
        return false;
    }
    if (currentActorType === "ADMINISTRATOR") {
        return true;
    }
    if (currentActorType === "ORGANIZATION") {
        return String(certificate.organization.id) === currentActorId;
    }
    return false;
}

// Devuelve la clase de badge de Bootstrap para el estado de registro (CONFIRMED/PENDING/ERROR).
function getRegistrationStatusBadgeClass(status) {
    if (status === "CONFIRMED") {
        return "bg-success";
    }
    if (status === "PENDING") {
        return "bg-warning text-dark";
    }
    return "bg-danger";
}

// Rellena la pantalla con los datos del certificado devuelto por la API.
function renderCertificate(certificate) {
    document.getElementById("detail-certificate-name").textContent = certificate.certificate_name;
    document.getElementById("detail-student").textContent = `${certificate.student.name} ${certificate.student.last_names}`;
    document.getElementById("detail-course").textContent = certificate.course.title;
    document.getElementById("detail-organization").textContent = certificate.organization.name;
    document.getElementById("detail-teacher").textContent = certificate.course.teacher;
    document.getElementById("detail-hours").textContent = certificate.course.hours;
    document.getElementById("detail-created-at").textContent = new Date(certificate.created_at).toLocaleDateString("es-ES");

    // Badge del estado de registro en blockchain (independiente de si está revocado).
    const statusBadge = document.getElementById("detail-status-badge");
    statusBadge.textContent = REGISTRATION_STATUS_LABELS[certificate.registration_status] || certificate.registration_status;
    statusBadge.className = `badge ${getRegistrationStatusBadgeClass(certificate.registration_status)}`;

    // Badge vigencia del certificado: revocado/activo, independiente del estado de registro.
    const revokedBadge = document.getElementById("detail-revoked-badge");
    if (certificate.revoked) {
        revokedBadge.textContent = "Revocado";
        revokedBadge.className = "badge bg-danger";
    } else {
        revokedBadge.textContent = "Activo";
        revokedBadge.className = "badge bg-success";
    }

    // El botón "Revocar certificado" solo se muestra si el actor autenticado puede revocar este certificado.
    // Se recalcula con if/else (no solo "remove") porque tras revocar se vuelve a llamar a renderCertificate
    // y el botón debe pasar de visible a oculto.
    if (canRevoke(certificate)) {
        revokeButton.classList.remove("d-none");
    } else {
        revokeButton.classList.add("d-none");
    }

    // Motivo y fecha de la revocación: solo se muestran si el certificado está revocado.
    const revocationDetails = document.getElementById("revocation-details");
    if (certificate.revoked) {
        document.getElementById("detail-revocation-reason").textContent = certificate.revocation_reason;
        document.getElementById("detail-revocation-date").textContent = certificate.revoked_at
            ? new Date(certificate.revoked_at).toLocaleDateString("es-ES")
            : "Sin fecha registrada";
        revocationDetails.classList.remove("d-none");
    } else {
        revocationDetails.classList.add("d-none");
    }

    document.getElementById("detail-sha256").textContent = certificate.sha256_hash;
    document.getElementById("detail-cid").textContent = certificate.cid;
    document.getElementById("detail-tx-hash").textContent = certificate.tx_hash;

    // obtenemos la fecha de registro del certificado en Cardano
    let cardanoDate;

    if (certificate.cardano_registration_date) {
        cardanoDate = new Date(certificate.cardano_registration_date).toLocaleDateString("es-ES");
    } else {
        cardanoDate = "Sin confirmar";
    }

    // Guardamos las variables en el almacenamiento local del cliente
    document.getElementById("detail-cardano-date").textContent = cardanoDate;
    document.getElementById("detail-content-type").textContent = certificate.content_type;
    document.getElementById("detail-size").textContent = `${certificate.size_bytes.toLocaleString("es-ES")} bytes`;

    // Aviso informativo en la sección de verificación si el certificado está revocado (la verificación de
    // integridad sigue funcionando igual; solo se avisa de que ya no es vigente).
    if (certificate.revoked) {
        document.getElementById("revoked-notice").classList.remove("d-none");
    }

    // se se muestra la información del estado, eliminamos la ocultación "d-none"
    contentState.classList.remove("d-none");
}

// Copia el valor de un campo (SHA-256, CID o TX Hash) al portapapeles al pulsar su botón "Copiar".
document.querySelectorAll(".copy-button").forEach(function (button) {
    button.addEventListener("click", function () {
        const value = document.getElementById(button.dataset.copyTarget).textContent;
        navigator.clipboard.writeText(value);

        const originalHTML = button.innerHTML;
        button.textContent = "Copiado";
        setTimeout(function () {
            button.innerHTML = originalHTML;
        }, 1500);
    });
});

// Abre el PDF del certificado en una pestaña nueva mediante una petición autenticada (un <a href> normal no puede enviar el header Authorization).
// Se abre en pestaña nueva en vez de forzar la descarga para no perder la página del detalle; desde el visor del navegador el usuario puede descargarlo si quiere.
const viewButton = document.getElementById("view-button");
const viewError = document.getElementById("view-error");
// guardaamos el contenido original del botón (icono + texto) en una variable porque cuando pinchemos se cambiará a "Abriendo..."
const viewButtonOriginalHTML = viewButton.innerHTML;

viewButton.addEventListener("click", async function () {
    // Si se hace clic en el botón, se oculta cualquier tipo de error anterior, se deshabilita (para que no se vuelva a clicar) y se cambia el texto a "Abriendo..."
    viewError.classList.add("d-none");
    viewButton.disabled = true;
    viewButton.textContent = "Abriendo...";

    try {
        //se llama a la API para solicitar el PDF del certificado seleccionado (en función del ID)
        const response = await fetch(`${API_BASE_URL}/certificates/${certificateId}/download`, {
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

        if (response.status === 403) {
            viewError.textContent = "No tienes permiso para consultar este certificado.";
            viewError.classList.remove("d-none");
            return;
        }

        if (response.status === 404) {
            viewError.textContent = "Certificado no encontrado.";
            viewError.classList.remove("d-none");
            return;
        }

        if (!response.ok) {
            throw new Error("Error al consultar el certificado");
        }

        // La respuesta no es texto (JSON) sino son bytes (PDF), por eso se utiliza blob.
        const blob = await response.blob();
        // Se crea una URL temporal para almacenar el BLOB (hay que tener presente que ahora está en memoria). 
        // Esto es necesario para visualizar el certificado en otra pestaña 
        const url = URL.createObjectURL(blob);
        // Se abre una nueva pestaña para visualizar el certificado
        const newTab = window.open(url, "_blank");

        // Si el navegador bloquea la apertura (política de ventanas emergentes), se avisa al usuario.
        if (!newTab) {
            viewError.textContent = "El navegador ha bloqueado la apertura del certificado. Permite las ventanas emergentes para este sitio.";
            viewError.classList.remove("d-none");
        }

    } catch (error) {
        viewError.textContent = "No se ha podido abrir el certificado.";
        viewError.classList.remove("d-none");

    } finally {
        viewButton.disabled = false;
        viewButton.innerHTML = viewButtonOriginalHTML;
    }
});

// Verifica la integridad del certificado almacenado: compara el hash registrado en Cardano con el hash
// recalculado a partir del contenido actual en IPFS. Mismo patrón que el botón "Ver certificado".
const verifyButton = document.getElementById("verify-button");
const verifyError = document.getElementById("verify-error");
const verifyResult = document.getElementById("verify-result");
// Se guarda el contenido original del botón antes de que se cambie a "Verificando.."
const verifyButtonOriginalHTML = verifyButton.innerHTML;

// Rellena la sección de resultado con la respuesta real del backend (hash esperado, hash calculado, CID, tx_hash).
function renderVerificationResult(result) {
    const resultAlert = document.getElementById("verify-result-alert");
    const resultHeadline = document.getElementById("verify-result-headline");
    const resultExplanation = document.getElementById("verify-result-explanation");

    // en función del resultado muestra un mensaje verde (OK integridad) o rojo (Verificación ha faalado), con una explicación sencilla debajo
    if (result.is_valid) {
        resultAlert.className = "alert alert-success mb-4";
        resultHeadline.textContent = "✅ Integridad verificada";
        resultExplanation.textContent = "El documento recuperado coincide con el registrado en el sistema, por lo que su integridad ha sido verificada correctamente.";
    } else {
        resultAlert.className = "alert alert-danger mb-4";
        resultHeadline.textContent = "❌ La verificación ha fallado";
        resultExplanation.textContent = "El documento recuperado no coincide con el registrado en el sistema, por lo que su integridad no ha podido confirmarse.";
    }

    // Se muestra por pantalla toda la información necesaria de la verificación: hashes, cid, tx_hash...
    document.getElementById("verify-expected-hash").textContent = result.expected_sha256_hash;
    document.getElementById("verify-calculated-hash").textContent = result.calculated_sha256_hash;
    document.getElementById("verify-cid").textContent = result.cid;
    document.getElementById("verify-tx-hash").textContent = result.tx_hash;
    
    verifyResult.classList.remove("d-none");
}

// Manejador del botón (click) de verificar: se activa cuando se selecciona el botón
verifyButton.addEventListener("click", async function () {
    verifyError.classList.add("d-none");
    verifyResult.classList.add("d-none");
    verifyButton.disabled = true;
    verifyButton.textContent = "Verificando...";

    try {
        // Endpoint de verificación: es un POST, no necesita cuerpo, solo el id del certificado en la URL.
        // lanzamos la petición al endpoint de la API "Verificar integridad certificado almacenado"
        const response = await fetch(`${API_BASE_URL}/certificates/${certificateId}/verify-stored-integrity`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${accessToken}`,
            },
        });

        if (response.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("actor_id");
            localStorage.removeItem("actor_type");
            localStorage.removeItem("display_name");

            window.location.href = "index.html";
            return;
        }

        if (response.status === 403) {
            verifyError.textContent = "No tienes permiso para verificar este certificado.";
            verifyError.classList.remove("d-none");
            return;
        }

        if (response.status === 404) {
            verifyError.textContent = "Certificado no encontrado.";
            verifyError.classList.remove("d-none");
            return;
        }

        if (!response.ok) {
            throw new Error("Error al verificar el certificado");
        }
        // Almaceno en la variable result el JSON que recibimos como respuesta de la verificación. Es lo que se utilizará para mostrar 
        // por pantalla en el detalle de la verificación
        const result = await response.json();
        
        // Se llama a la función que pinta por pantalla todo el detalle de la verificación
        renderVerificationResult(result);

    } catch (error) {
        verifyError.textContent = "No se ha podido realizar la verificación.";
        verifyError.classList.remove("d-none");

    } finally {
        verifyButton.disabled = false;
        verifyButton.innerHTML = verifyButtonOriginalHTML;
    }
});

// Compara un PDF aportado por el usuario con un certificado existente en la plataforma.
const compareFileInput = document.getElementById("compare-file");
const compareButton = document.getElementById("compare-button");
const compareError = document.getElementById("compare-error");
const compareResult = document.getElementById("compare-result");
const compareButtonOriginalHTML = compareButton.innerHTML;

// Rellena la sección de resultado con la respuesta real del backend (hash esperado y hash del PDF aportado).
function renderCompareResult(result) {
    const resultAlert = document.getElementById("compare-result-alert");
    const resultHeadline = document.getElementById("compare-result-headline");
    const resultExplanation = document.getElementById("compare-result-explanation");

    if (result.is_valid) {
        resultAlert.className = "alert alert-success mb-4";
        resultHeadline.textContent = "✅ El documento coincide exactamente con el certificado registrado.";
        resultExplanation.textContent = "El PDF aportado tiene el mismo hash SHA-256 que el certificado registrado en el sistema.";
    } else {
        resultAlert.className = "alert alert-danger mb-4";
        resultHeadline.textContent = "❌ El documento aportado no corresponde con este certificado.";
        resultExplanation.textContent = "El hash SHA-256 del PDF aportado no coincide con el registrado, por lo que no se puede confirmar que sea el mismo documento.";
    }

    document.getElementById("compare-expected-hash").textContent = result.expected_sha256_hash;
    document.getElementById("compare-uploaded-hash").textContent = result.uploaded_sha256_hash;

    compareResult.classList.remove("d-none");
}
// Manejador del botón "comparar pdf" --> se activa cuando pinchamos en el botón
compareButton.addEventListener("click", async function () {
    compareError.classList.add("d-none");
    compareResult.classList.add("d-none");

    const file = compareFileInput.files[0];

    // Validación básica de interfaz: archivo obligatorio y debe ser un PDF. Todo lo demás lo valida el backend.
    if (!file) {
        compareError.textContent = "Selecciona el archivo PDF que quieres comparar.";
        compareError.classList.remove("d-none");
        return;
    }
    if (file.type !== "application/pdf") {
        compareError.textContent = "El archivo debe ser un PDF.";
        compareError.classList.remove("d-none");
        return;
    }

    compareButton.disabled = true;
    compareButton.textContent = "Comparando...";

    // El endpoint espera multipart/form-data (incluye el propio archivo), no JSON.
    const formData = new FormData();
    formData.append("file", file);

    try {
        // certificate_id ya se conoce por la URL: no se busca el certificado, solo se sube el PDF a comparar.
        const response = await fetch(`${API_BASE_URL}/certificates/${certificateId}/verify-uploaded-integrity`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${accessToken}`,
            },
            body: formData,
        });

        if (response.status === 401) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("actor_id");
            localStorage.removeItem("actor_type");
            localStorage.removeItem("display_name");

            window.location.href = "index.html";
            return;
        }

        if (response.status === 403) {
            compareError.textContent = "No tienes permiso para comparar este certificado.";
            compareError.classList.remove("d-none");
            return;
        }

        if (response.status === 404) {
            compareError.textContent = "Certificado no encontrado.";
            compareError.classList.remove("d-none");
            return;
        }

        if (!response.ok) {
            throw new Error("Error al comparar el certificado");
        }

        const result = await response.json();
        renderCompareResult(result);

    } catch (error) {
        compareError.textContent = "No se ha podido realizar la comparación.";
        compareError.classList.remove("d-none");

    } finally {
        compareButton.disabled = false;
        compareButton.innerHTML = compareButtonOriginalHTML;
    }
});

// Revoca el certificado mostrado. Al pulsar "Revocar certificado" se abre un modal que pide el motivo
// (obligatorio); solo al confirmar ahí se llama a la API. Si sale bien, se recarga el detalle completo
// para que se actualicen el badge de Vigencia, el motivo/fecha, el aviso de Verificación y este botón.
const revokeButton = document.getElementById("revoke-button");
const revokeError = document.getElementById("revoke-error");

const revokeModalElement = document.getElementById("revoke-modal");
const revokeModal = new bootstrap.Modal(revokeModalElement);
const revokeReasonInput = document.getElementById("revoke-reason-input");
const revokeReasonError = document.getElementById("revoke-reason-error");
const revokeConfirmButton = document.getElementById("revoke-confirm-button");
const revokeConfirmButtonOriginalHTML = revokeConfirmButton.innerHTML;

revokeButton.addEventListener("click", function () {
    revokeError.classList.add("d-none");
    revokeReasonInput.value = "";
    revokeReasonError.classList.add("d-none");
    revokeModal.show();
});

revokeConfirmButton.addEventListener("click", async function () {
    const reason = revokeReasonInput.value.trim();

    // El motivo es obligatorio: si está vacío, se avisa dentro del propio modal y no se envía la petición.
    if (!reason) {
        revokeReasonError.classList.remove("d-none");
        return;
    }

    revokeConfirmButton.disabled = true;
    revokeConfirmButton.textContent = "Revocando...";

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
            revokeError.textContent = "No se ha podido revocar el certificado.";
            revokeError.classList.remove("d-none");
            return;
        }

        revokeModal.hide();
        // Se recarga el detalle completo para reflejar el nuevo estado (badge, motivo, fecha, aviso y este botón).
        loadCertificateDetail();

    } catch (error) {
        revokeModal.hide();
        revokeError.textContent = "No se ha podido revocar el certificado.";
        revokeError.classList.remove("d-none");
    } finally {
        revokeConfirmButton.disabled = false;
        revokeConfirmButton.innerHTML = revokeConfirmButtonOriginalHTML;
    }
});

// Consulta la API y muestra el detalle, o el mensaje de error correspondiente.
// Función principal que carga el detalle del certificado seleccionado.

async function loadCertificateDetail() {

    if (!certificateId) {
        showError("Falta el identificador del certificado en la URL.");
        return;
    }

    try {

        // Lanzamos la petición a la API para obtener el detalle del certificado
        const response = await fetch(`${API_BASE_URL}/certificates/${certificateId}`, {
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

        if (response.status === 403) {
            showError("No tienes permiso para consultar este certificado.");
            return;
        }

        if (response.status === 404) {
            showError("Certificado no encontrado.");
            return;
        }

        if (!response.ok) {
            throw new Error("Error al consultar el certificado");
        }

        // Obtenemos la respuesta de la API y llamamos a renderCertificate para pintar por pantalla todo el detalle
        const certificate = await response.json();
        hideAllStates();
        renderCertificate(certificate);

    } catch (error) {
        showError("No se ha podido cargar el certificado.");
    }
}

loadCertificateDetail();
