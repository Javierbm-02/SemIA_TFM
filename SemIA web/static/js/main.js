/**
 * SemIA — main.js
 * Lógica del predictor agrícola y chatbot conversacional
 */

// ─────────────────────────────────────────────────────────────────────────────
// Estado global
// ─────────────────────────────────────────────────────────────────────────────
let semestreSeleccionado = 'A';
let municipiosPorDepto   = {};

// ─────────────────────────────────────────────────────────────────────────────
// Inicialización
// ─────────────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    inicializarNavbar();
    cargarMunicipios();
    inicializarScrollAnimaciones();
    inicializarContadores();
});

// ─────────────────────────────────────────────────────────────────────────────
// Navbar: scroll shadow + menú hamburger
// ─────────────────────────────────────────────────────────────────────────────
function inicializarNavbar() {
    const navbar = document.getElementById('navbar');
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
    });
}

function toggleMenu() {
    const nav  = document.getElementById('navLinks');
    const ham  = document.getElementById('hamburger');
    nav.classList.toggle('open');
    ham.classList.toggle('active');
}

function closeMenu() {
    document.getElementById('navLinks').classList.remove('open');
    document.getElementById('hamburger').classList.remove('active');
}

// ─────────────────────────────────────────────────────────────────────────────
// Cargar municipios desde el backend
// ─────────────────────────────────────────────────────────────────────────────
async function cargarMunicipios() {
    try {
        const resp = await fetch('/api/municipios');
        if (!resp.ok) throw new Error('Error al cargar municipios');
        const data = await resp.json();
        municipiosPorDepto = data.departamentos || {};

        const selDepto = document.getElementById('sel-depto');
        const deptos   = Object.keys(municipiosPorDepto).sort();

        deptos.forEach(d => {
            const opt = document.createElement('option');
            opt.value = d;
            opt.textContent = d;
            selDepto.appendChild(opt);
        });
    } catch (err) {
        console.warn('No se pudieron cargar los municipios:', err);
        // Fallback: campo de texto libre
        reemplazarSelectsConInputs();
    }
}

function reemplazarSelectsConInputs() {
    const grpDepto = document.getElementById('sel-depto').parentElement;
    const grpMun   = document.getElementById('sel-municipio').parentElement;

    grpDepto.innerHTML = `
        <label><i class="fas fa-map"></i> Departamento</label>
        <input type="text" id="sel-depto" placeholder="Ej: CUNDINAMARCA">
    `;
    grpMun.innerHTML = `
        <label><i class="fas fa-map-marker-alt"></i> Municipio</label>
        <input type="text" id="sel-municipio" placeholder="Ej: SOACHA">
    `;
}

function onDeptoChange() {
    const selDepto  = document.getElementById('sel-depto');
    const selMun    = document.getElementById('sel-municipio');
    const depto     = selDepto.value;

    // Limpiar municipios
    selMun.innerHTML = '<option value="">-- Selecciona municipio --</option>';

    if (!depto) {
        selMun.disabled = true;
        return;
    }

    const municipios = municipiosPorDepto[depto] || [];
    municipios.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        selMun.appendChild(opt);
    });

    selMun.disabled = false;
}

// ─────────────────────────────────────────────────────────────────────────────
// Semestre toggle
// ─────────────────────────────────────────────────────────────────────────────
function setSemestre(s) {
    semestreSeleccionado = s;
    document.getElementById('btn-sem-a').classList.toggle('active', s === 'A');
    document.getElementById('btn-sem-b').classList.toggle('active', s === 'B');
}

// ─────────────────────────────────────────────────────────────────────────────
// Hacer predicción
// ─────────────────────────────────────────────────────────────────────────────
async function hacerPrediccion() {
    const municipio = getMunicipioValue();
    const anio      = document.getElementById('inp-anio').value.trim();
    const area      = document.getElementById('inp-area').value.trim();

    // Validación básica en frontend
    if (!municipio) {
        agregarMensajeError('Por favor selecciona un municipio antes de predecir.');
        return;
    }
    if (!anio || isNaN(anio)) {
        agregarMensajeError('Por favor ingresa un año válido (ej: 2025).');
        return;
    }
    if (!area || isNaN(area) || parseFloat(area) <= 0) {
        agregarMensajeError('Por favor ingresa un área válida en hectáreas (ej: 10.5).');
        return;
    }

    // Mensaje del usuario en el chat
    const depto = getDeptoValue();
    agregarMensajeUsuario(
        `📍 Municipio: ${municipio}${depto ? ' (' + depto + ')' : ''}\n` +
        `📅 Año: ${anio} | 🌤️ Semestre: ${semestreSeleccionado} | 📐 Área: ${area} ha`
    );

    // Mostrar indicador de carga
    const btnPredict = document.getElementById('btn-predict');
    btnPredict.classList.add('loading');
    btnPredict.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';
    mostrarTyping(true);

    try {
        const resp = await fetch('/api/recomendar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                municipio,
                anio:     parseInt(anio),
                semestre: semestreSeleccionado,
                area:     parseFloat(area),
            }),
        });

        const data = await resp.json();
        mostrarTyping(false);

        if (data.tipo === 'prediccion') {
            agregarResultadoPrediccion(data);
        } else if (data.tipo === 'error') {
            agregarMensajeError(data.respuesta || 'Ocurrió un error inesperado.');
        } else {
            agregarMensajeBot(data.respuesta || 'Respuesta inesperada del servidor.');
        }

    } catch (err) {
        mostrarTyping(false);
        agregarMensajeError(
            '❌ No se pudo conectar con el servidor. Asegúrate de que el backend esté corriendo.'
        );
    } finally {
        btnPredict.classList.remove('loading');
        btnPredict.innerHTML = '<i class="fas fa-magic"></i> Predecir Cultivos';
    }
}

function getMunicipioValue() {
    const el = document.getElementById('sel-municipio');
    if (!el) return '';
    // Puede ser <select> o <input>
    return (el.tagName === 'SELECT') ? el.value : el.value.trim().toUpperCase();
}

function getDeptoValue() {
    const el = document.getElementById('sel-depto');
    if (!el) return '';
    return (el.tagName === 'SELECT') ? el.value : el.value.trim().toUpperCase();
}

// ─────────────────────────────────────────────────────────────────────────────
// Small talk / pregunta libre
// ─────────────────────────────────────────────────────────────────────────────
async function enviarSmallTalk() {
    const input = document.getElementById('inp-smalltalk');
    const texto = input.value.trim();
    if (!texto) return;

    agregarMensajeUsuario(texto);
    input.value = '';
    mostrarTyping(true);

    try {
        const resp = await fetch('/api/recomendar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mensaje: texto }),
        });

        const data = await resp.json();
        mostrarTyping(false);

        if (data.respuesta) {
            agregarMensajeBot(data.respuesta);
        } else {
            agregarMensajeBot('No entendí tu mensaje. Intenta con una pregunta diferente.');
        }
    } catch {
        mostrarTyping(false);
        agregarMensajeError('❌ No se pudo conectar con el servidor.');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Funciones de renderizado del chat
// ─────────────────────────────────────────────────────────────────────────────
function agregarMensajeUsuario(texto) {
    const chatWindow = document.getElementById('chat-window');
    const row = document.createElement('div');
    row.className = 'msg-row user-row';
    row.innerHTML = `
        <div class="msg-avatar"><i class="fas fa-user"></i></div>
        <div class="msg-bubble user-bubble">${escapeHtml(texto).replace(/\n/g, '<br>')}</div>
    `;
    chatWindow.appendChild(row);
    scrollAlFinal();
}

function agregarMensajeBot(texto) {
    const chatWindow = document.getElementById('chat-window');
    const row = document.createElement('div');
    row.className = 'msg-row bot-row';

    // Usar marked.js si está disponible para renderizar markdown
    const htmlContent = (typeof marked !== 'undefined')
        ? marked.parse(texto)
        : escapeHtml(texto).replace(/\n/g, '<br>');

    row.innerHTML = `
        <div class="msg-avatar"><i class="fas fa-seedling"></i></div>
        <div class="msg-bubble bot-bubble">${htmlContent}</div>
    `;
    chatWindow.appendChild(row);
    scrollAlFinal();
}

function agregarMensajeError(texto) {
    const chatWindow = document.getElementById('chat-window');
    const row = document.createElement('div');
    row.className = 'msg-row bot-row';
    row.innerHTML = `
        <div class="msg-avatar" style="background:#e53935"><i class="fas fa-exclamation-triangle"></i></div>
        <div class="msg-bubble bot-bubble error-bubble">${escapeHtml(texto)}</div>
    `;
    chatWindow.appendChild(row);
    scrollAlFinal();
}

function agregarResultadoPrediccion(data) {
    const chatWindow = document.getElementById('chat-window');

    // Mensaje introductorio del bot
    const msgRow = document.createElement('div');
    msgRow.className = 'msg-row bot-row';
    msgRow.innerHTML = `
        <div class="msg-avatar"><i class="fas fa-seedling"></i></div>
        <div class="msg-bubble bot-bubble">
            <p>🌾 ¡Aquí tienes el análisis para <strong>${data.municipio}</strong>!</p>
            <p>Proyección para el <strong>Semestre ${data.semestre} de ${data.anio}</strong> con un área de <strong>${data.area} ha</strong>:</p>
        </div>
    `;
    chatWindow.appendChild(msgRow);

    // Tabla de resultados
    const resultRow = document.createElement('div');
    resultRow.className = 'msg-row bot-row';

    const recomendaciones = data.recomendaciones || [];
    let filasHtml = '';

    recomendaciones.forEach((r, i) => {
        const rend    = parseFloat(r['Rendimiento_Proyectado_t_ha']).toFixed(2);
        const prod    = parseFloat(r['Produccion_Total_Estimada_t']).toFixed(2);
        const ciclo   = r['Ciclo_Cultivo'] || '';
        const cicloCls = ciclo.toUpperCase().includes('PERM') ? 'perm' : 'trans';
        const rankNum = i + 1;
        const rankCls = rankNum <= 3 ? `rank-${rankNum}` : '';

        filasHtml += `
            <tr>
                <td><span class="rank-badge ${rankCls}">${rankNum}</span></td>
                <td><strong>${r['Cultivo'] || '–'}</strong><br>
                    <small style="color:var(--gray-600)">${r['Grupo_Cultivo'] || ''}</small>
                </td>
                <td><span class="ciclo-badge ${cicloCls}">${ciclo}</span></td>
                <td class="rend-val">${rend} t/ha</td>
                <td class="prod-val">${prod} t</td>
            </tr>
        `;
    });

    resultRow.innerHTML = `
        <div class="msg-avatar" style="opacity:0;pointer-events:none"></div>
        <div style="flex:1;max-width:calc(100% - 42px)">
            <div class="result-card">
                <div class="result-header">
                    <i class="fas fa-trophy" style="font-size:1.2rem"></i>
                    <div>
                        <h4>Top ${recomendaciones.length} Cultivos Recomendados</h4>
                        <div class="result-meta">
                            ${data.municipio} · Sem. ${data.semestre} ${data.anio} · ${data.area} ha
                        </div>
                    </div>
                </div>
                <table class="result-table">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Cultivo</th>
                            <th>Ciclo</th>
                            <th>Rendimiento</th>
                            <th>Producción Est.</th>
                        </tr>
                    </thead>
                    <tbody>${filasHtml}</tbody>
                </table>
            </div>
            <div style="margin-top:0.6rem; font-size:0.78rem; color:var(--gray-600); padding:0 0.2rem">
                <i class="fas fa-info-circle" style="color:var(--verde)"></i>
                Predicciones basadas en datos históricos EVA del MADR (2007–2024).
                Úsalas como guía de planificación.
            </div>
        </div>
    `;
    chatWindow.appendChild(resultRow);

    // Sugerencias de seguimiento
    const suggestions = [
        `¿Y para el Semestre ${data.semestre === 'A' ? 'B' : 'A'}?`,
        `¿Qué datos usas para las predicciones?`,
        `¿Cómo funcionas?`,
    ];
    const sugRow = document.createElement('div');
    sugRow.className = 'msg-row bot-row';
    sugRow.innerHTML = `
        <div class="msg-avatar" style="opacity:0;pointer-events:none"></div>
        <div style="display:flex;gap:0.5rem;flex-wrap:wrap;max-width:80%">
            ${suggestions.map(s => `
                <button onclick="sugerirConsulta(this, '${s.replace(/'/g,"\\'")}', '${data.municipio}', ${data.anio}, '${data.semestre}', ${data.area})"
                        style="background:var(--verde-pale);border:1px solid rgba(40,167,69,0.3);
                               color:var(--verde-dark);font-family:'Outfit',sans-serif;
                               font-size:0.8rem;font-weight:600;padding:0.35rem 0.8rem;
                               border-radius:50px;cursor:pointer;transition:all 0.2s"
                        onmouseover="this.style.background='var(--verde)';this.style.color='white'"
                        onmouseout="this.style.background='var(--verde-pale)';this.style.color='var(--verde-dark)'">
                    ${escapeHtml(s)}
                </button>
            `).join('')}
        </div>
    `;
    chatWindow.appendChild(sugRow);
    scrollAlFinal();
}

function sugerirConsulta(btn, texto, municipio, anio, semestre, area) {
    // Deshabilitar todos los botones de sugerencia del grupo
    const grupo = btn.parentElement;
    grupo.querySelectorAll('button').forEach(b => {
        b.disabled = true;
        b.style.opacity = '0.5';
        b.style.cursor = 'default';
    });

    if (texto.includes('Semestre')) {
        // Cambiar semestre y predecir
        const nuevoSemestre = texto.includes('Semestre B') ? 'B' : 'A';
        setSemestre(nuevoSemestre);
        agregarMensajeUsuario(texto);
        hacerPrediccionDirecta(municipio, anio, nuevoSemestre, area);
    } else {
        // Small talk
        agregarMensajeUsuario(texto);
        enviarSmallTalkTexto(texto);
    }
}

async function hacerPrediccionDirecta(municipio, anio, semestre, area) {
    mostrarTyping(true);
    const btnPredict = document.getElementById('btn-predict');
    btnPredict.classList.add('loading');
    btnPredict.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';

    try {
        const resp = await fetch('/api/recomendar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ municipio, anio, semestre, area }),
        });
        const data = await resp.json();
        mostrarTyping(false);
        if (data.tipo === 'prediccion') agregarResultadoPrediccion(data);
        else agregarMensajeError(data.respuesta || 'Error inesperado.');
    } catch {
        mostrarTyping(false);
        agregarMensajeError('❌ No se pudo conectar con el servidor.');
    } finally {
        btnPredict.classList.remove('loading');
        btnPredict.innerHTML = '<i class="fas fa-magic"></i> Predecir Cultivos';
    }
}

async function enviarSmallTalkTexto(texto) {
    mostrarTyping(true);
    try {
        const resp = await fetch('/api/recomendar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mensaje: texto }),
        });
        const data = await resp.json();
        mostrarTyping(false);
        agregarMensajeBot(data.respuesta || 'Sin respuesta.');
    } catch {
        mostrarTyping(false);
        agregarMensajeError('❌ No se pudo conectar con el servidor.');
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Typing indicator
// ─────────────────────────────────────────────────────────────────────────────
function mostrarTyping(visible) {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.style.display = visible ? 'flex' : 'none';
    if (visible) scrollAlFinal();
}

function scrollAlFinal() {
    setTimeout(() => {
        const chatWindow = document.getElementById('chat-window');
        if (chatWindow) chatWindow.scrollTop = chatWindow.scrollHeight;
    }, 50);
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilidades
// ─────────────────────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// ─────────────────────────────────────────────────────────────────────────────
// Scroll animations (Intersection Observer)
// ─────────────────────────────────────────────────────────────────────────────
function inicializarScrollAnimaciones() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    document.querySelectorAll('.fade-in, .feature-card, .stat-box').forEach(el => {
        el.classList.add('reveal');
        el.classList.remove('fade-in');
        observer.observe(el);
    });
}

// ─────────────────────────────────────────────────────────────────────────────
// Contadores animados
// ─────────────────────────────────────────────────────────────────────────────
function inicializarContadores() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animarContador(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.stat-number[data-target]').forEach(el => {
        observer.observe(el);
    });
}

function animarContador(el) {
    const target   = parseInt(el.getAttribute('data-target'), 10);
    const duracion = 1800; // ms
    const paso     = Math.ceil(duracion / 60);
    let current    = 0;

    const increment = target / (duracion / paso);
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        // Formatear con separador de miles
        el.textContent = Math.floor(current).toLocaleString('es-CO');
        // Añadir sufijo si es porcentaje
        if (el.getAttribute('data-target') === '95') el.textContent += '%';
    }, paso);
}
