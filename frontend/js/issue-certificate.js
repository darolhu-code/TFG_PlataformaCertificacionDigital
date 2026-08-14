// Formulario de emisión de certificados: organización -> curso -> alumno matriculado, con desplegables de búsqueda (Tom Select).
const accessToken = localStorage.getItem("access_token");
const currentActorType = localStorage.getItem("actor_type");

// Sin sesión iniciada no se puede emitir certificados: se redirige al login.
if (!accessToken) {
    window.location.href = "index.html";
}

const issueForm = document.getElementById("issue-form");
const issueError = document.getElementById("issue-error");
const issueSuccess = document.getElementById("issue-success");
const organizationField = document.getElementById("organization-field");
const submitButton = document.getElementById("issue-submit-button");
const submitButtonOriginalHTML = submitButton.innerHTML;

// El desplegable de organización solo tiene sentido para un administrador: una organización siempre
// emite bajo su propio id, así que no necesita elegirla.
if (currentActorType === "ADMINISTRATOR") {
    organizationField.classList.remove("d-none");
}

// Desplegables con búsqueda (Tom Select), vacíos hasta que llega la información real de la API.
const organizationSelect = new TomSelect("#issue-organization-select", {
    valueField: "organization_id",
    labelField: "organization_name",
    searchField: "organization_name",
    placeholder: "Busca una organización...",
});

const courseSelect = new TomSelect("#issue-course-select", {
    valueField: "course_id",
    labelField: "title",
    searchField: "title",
    placeholder: "Busca un curso...",
});
courseSelect.disable();

const studentSelect = new TomSelect("#issue-student-select", {
    valueField: "student_id",
    labelField: "full_name",
    searchField: "full_name",
    placeholder: "Busca un alumno...",
});
studentSelect.disable();

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

// Vacía y rellena el desplegable de alumnos, dejándolo deshabilitado.
function resetStudentSelect() {
    studentSelect.clear();
    studentSelect.clearOptions();
    studentSelect.disable();
}

// Rellena el desplegable de cursos con la lista indicada (ya filtrada si corresponde) y lo habilita.
function fillCourseSelect(courses) {
    courseSelect.clear();
    courseSelect.clearOptions();
    courses.forEach(function (course) {
        courseSelect.addOption({ course_id: course.course_id, title: course.title });
    });
    courseSelect.enable();
}

// Se guardan todos los cursos ya cargados para poder filtrarlos por organización en el cliente,
// sin volver a pedirlos al backend
let allCourses = [];

// Carga los cursos visibles para el actor autenticado: una organización recibe solo los suyos,
// un administrador recibe todos (el backend ya aplica ese filtro).
async function loadCourses() {
    try {
        const response = await fetch(`${API_BASE_URL}/courses`, {
            headers: { "Authorization": `Bearer ${accessToken}` },
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            issueError.textContent = await extractErrorMessage(response, "No se han podido cargar los cursos.");
            issueError.classList.remove("d-none");
            return;
        }

        allCourses = await response.json();

        if (currentActorType === "ADMINISTRATOR") {
            // Las organizaciones se obtienen de cada curso (tiene esa información). Los cursos no se muestran hasta que se elige una organización.
            const seenOrganizationIds = [];
            allCourses.forEach(function (course) {
                if (!seenOrganizationIds.includes(course.organization_id)) {
                    seenOrganizationIds.push(course.organization_id);
                    organizationSelect.addOption({
                        organization_id: course.organization_id,
                        organization_name: course.organization_name,
                    });
                }
            });
        } else {
            // Una organización ya recibe únicamente sus propios cursos: se muestran directamente.
            fillCourseSelect(allCourses);
        }
    } catch (error) {
        issueError.textContent = "No se han podido cargar los cursos.";
        issueError.classList.remove("d-none");
    }
}

// Al elegir una organización (solo administrador), se filtran los cursos ya cargados por esa organización.
organizationSelect.on("change", function (organizationId) {
    resetStudentSelect();

    if (!organizationId) {
        courseSelect.clear();
        courseSelect.clearOptions();
        courseSelect.disable();
        return;
    }

    const filteredCourses = allCourses.filter(function (course) {
        return String(course.organization_id) === organizationId;
    });
    fillCourseSelect(filteredCourses);
});

// Al elegir un curso, se cargan únicamente los alumnos matriculados en él.
courseSelect.on("change", async function (courseId) {
    resetStudentSelect();

    if (!courseId) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/courses/${courseId}/students`, {
            headers: { "Authorization": `Bearer ${accessToken}` },
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            issueError.textContent = await extractErrorMessage(response, "No se han podido cargar los alumnos matriculados.");
            issueError.classList.remove("d-none");
            return;
        }

        const students = await response.json();
        students.forEach(function (student) {
            studentSelect.addOption({ student_id: student.student_id, full_name: student.full_name });
        });
        studentSelect.enable();
    } catch (error) {
        issueError.textContent = "No se han podido cargar los alumnos matriculados.";
        issueError.classList.remove("d-none");
    }
});

issueForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    issueError.classList.add("d-none");
    issueSuccess.classList.add("d-none");

    // Validación básica de interfaz: solo comprueba que hay algo seleccionado; 
    // el backend ya valida matrícula, permisos y pertenencia del curso a la organización.
    if (currentActorType === "ADMINISTRATOR" && !organizationSelect.getValue()) {
        issueError.textContent = "Selecciona una organización.";
        issueError.classList.remove("d-none");
        return;
    }
    if (!courseSelect.getValue()) {
        issueError.textContent = "Selecciona un curso.";
        issueError.classList.remove("d-none");
        return;
    }
    if (!studentSelect.getValue()) {
        issueError.textContent = "Selecciona un alumno.";
        issueError.classList.remove("d-none");
        return;
    }
    if (!document.getElementById("issue-certificate-name").value.trim()) {
        issueError.textContent = "Introduce el nombre del certificado.";
        issueError.classList.remove("d-none");
        return;
    }
    if (!document.getElementById("issue-file").files[0]) {
        issueError.textContent = "Selecciona el archivo PDF del certificado.";
        issueError.classList.remove("d-none");
        return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Emitiendo...";

    // El endpoint de emisión espera multipart/form-data (incluye el propio archivo PDF), no JSON.
    // FormData es un objeto pensado para construir una petición multipart/form-data. Se le añaden diferentes campos.
    const formData = new FormData();
    formData.append("student_id", studentSelect.getValue());
    formData.append("course_id", courseSelect.getValue());
    formData.append("certificate_name", document.getElementById("issue-certificate-name").value);
    // se incluye el propio archivo pdf
    formData.append("file", document.getElementById("issue-file").files[0]);

    // Si el usuario identificado es administrador, también debe indicar organización emisora.
    if (currentActorType === "ADMINISTRATOR") {
        formData.append("issuing_organization_id", organizationSelect.getValue());
    }

    try {
        // No se indica Content-Type: el navegador lo calcula solo (incluye el "boundary" del multipart), y si lo forzamos a mano se rompe.
        const response = await fetch(`${API_BASE_URL}/certificates/upload`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${accessToken}` },
            body: formData,
        });
         
        // Sesión no válida o caducada: se elimina y se vuelve al login.
        if (response.status === 401) {
            handleUnauthorized();
            return;
        }

        if (!response.ok) {
            issueError.textContent = await extractErrorMessage(response, "No se ha podido emitir el certificado.");
            issueError.classList.remove("d-none");
            return;
        }
        
        // Éxito: el backend ya ha registrado el certificado (PostgreSQL + Cardano + IPFS).
        const certificate = await response.json();
        
        // Mostramos un aviso de que se ha emitido correctamente, con un enlace directo a su detalle.
        // Texto y botón en la misma línea (en vez de apilados) para que el aviso ocupe menos alto.
        issueSuccess.innerHTML = `
            <div class="d-flex align-items-center justify-content-between gap-3">
                <span>Certificado emitido correctamente.</span>
                <a href="certificate-detail.html?id=${certificate.certificate_id}" class="btn btn-sm btn-success text-nowrap">Ver detalle</a>
            </div>
        `;

        issueSuccess.classList.remove("d-none");
        // Inicializamos los campos del formulario
        issueForm.reset();
        
        // Si en unos segundos (10 segundos) no se ha elegido "Ver detalle", se vuelve al listado.
        setTimeout(function () {
            window.location.href = "certificates.html";
        }, 10000);

    } catch (error) {
        issueError.textContent = "No se ha podido emitir el certificado.";
        issueError.classList.remove("d-none");
      
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = submitButtonOriginalHTML;
    }
});

loadCourses();
