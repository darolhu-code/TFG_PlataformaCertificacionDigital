//Este script maneja la lógica de autenticación en el frontend, incluyendo el inicio de sesión y la gestión de tokens de acceso.
const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");

// Traducción del tipo de actor devuelto por la API (en inglés) para mostrarlo en español en la interfaz.
const ACTOR_TYPE_LABELS = {
    STUDENT: "alumno",
    ORGANIZATION: "organización",
    ADMINISTRATOR: "administrador",
};


// =========================================================
// LOGIN - Ejecuta el código del login solamente si estamos en una página que tiene formulario de login
// =========================================================

if(loginForm) 
{
    // Se incluye un evento de escucha para el envío del formulario de inicio de sesión. 
    // Esperamos a que el usuario envíe sus credenciales y luego gestionamos la autenticación.
    loginForm.addEventListener("submit", async function (event) {

    // Prevenir el comportamiento predeterminado del formulario para evitar que la página se recargue al enviar el formulario.
    event.preventDefault();

    // Obtener los valores de correo electrónico y contraseña ingresados por el usuario en el formulario.
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    // Clase "d-none" se utiliza para ocultar el elemento de mensaje de inicio de sesión, antes de intentar autenticar al usuario nuevamente.
    loginMessage.classList.add("d-none");

    try {

        // Realizar una solicitud POST al endpoint de inicio de sesión de la API para autenticar al usuario.
        // fetch() se utiliza para enviar la solicitud y obtener la respuesta de la API. 
        // Await se utiliza para esperar la respuesta de manera asíncrona.
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },
            // Enviar los datos de correo electrónico y contraseña en el cuerpo de la solicitud en formato JSON.
            body: JSON.stringify({
                email: email,
                password: password
            })

        });

        // Verificar si la respuesta de la API indica un error. Se distingue entre credenciales incorrectas (401) y otros fallos del servidor.
        if (!response.ok) {
            throw new Error(response.status === 401 ? "Credenciales incorrectas" : "Error del servidor, inténtalo más tarde");
        }

        // Si la respuesta es exitosa, obtener el token de acceso de la respuesta JSON.
        const data = await response.json();

        // Se guarda el token de acceso en el almacenamiento local del navegador para su uso posterior en solicitudes autenticadas.
        localStorage.setItem(
            "access_token",
            data.access_token
        );

        // Se realiza una solicitud GET al endpoint de "me" de la API para obtener información del usuario autenticado.
        const meResponse = await fetch(`${API_BASE_URL}/auth/me`, {

            // Incluir el token de acceso en los encabezados de la solicitud para autenticar al usuario.
            headers: {
                "Authorization": `Bearer ${data.access_token}`
            }

        });


        if (!meResponse.ok) {
            throw new Error("No se ha podido validar la sesión");
        }

        // Obtener la información del usuario autenticado de la respuesta JSON.
        const user = await meResponse.json();

        // Se guarda el actor_id, el actor_type y el display_name en el almacenamiento local del navegaodr para su uso posterior en la app.
        localStorage.setItem("actor_id", user.actor_id);
        localStorage.setItem("actor_type", user.actor_type);
        localStorage.setItem("display_name", user.display_name);

        window.location.href = "certificates.html";
    }

    // si falla eliminamos cualquier dato de sesión (token y datos del actor) y se muestra una alerta/mensaje de error
    catch (error) {

        localStorage.removeItem("access_token");
        localStorage.removeItem("actor_id");
        localStorage.removeItem("actor_type");
        localStorage.removeItem("display_name");

        loginMessage.className = "alert alert-danger";

        loginMessage.textContent = error.message;

    }

    });

}

// =========================================================
// CERTIFICATES.HTML - Si no estamos en LOGIN, estamos en CERTIFICATES.HTML
// =========================================================

const actorType = document.getElementById("actor-type");
const actorDisplayName = document.getElementById("actor-display-name");
const actorTypeContent = document.getElementById("actor-type-content");
const actorId = document.getElementById("actor-id");
const logoutButton = document.getElementById("logout-button");

// Sin sesión iniciada no se puede ver esta página: se redirige al login.
if (logoutButton && !localStorage.getItem("access_token")) {
    window.location.href = "index.html";
}

// Se muestra el nombre real del actor y su tipo traducido al español (ver ACTOR_TYPE_LABELS), guardados en el login.
const actorTypeLabel = ACTOR_TYPE_LABELS[localStorage.getItem("actor_type")] || localStorage.getItem("actor_type");

if (actorDisplayName) {
    actorDisplayName.textContent = localStorage.getItem("display_name");
}

if (actorType) {
    actorType.textContent = actorTypeLabel;
}

if (actorTypeContent) {
    actorTypeContent.textContent = actorTypeLabel;
}

if (actorId) {
    actorId.textContent = localStorage.getItem("actor_id");
}

// Si existe un botón de salir... 
if (logoutButton) {

    // Si pinchamos en el botón de salir, eliminamos del almacenamiento local el token, actor_id y actor_typr. 
    // Después se redirige a index.html (login)
    logoutButton.addEventListener("click", function () {

        localStorage.removeItem("access_token");
        localStorage.removeItem("actor_id");
        localStorage.removeItem("actor_type");
        localStorage.removeItem("display_name");

        window.location.href = "index.html";

    });

}