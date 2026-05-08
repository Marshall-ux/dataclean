document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('file-input');
    const uploadForm = document.getElementById('upload-form');
    const loadingState = document.getElementById('loading-state');
    const successState = document.getElementById('success-state');
    const errorState = document.getElementById('error-state');
    const errorMsg = document.getElementById('error-message');
    const downloadBtn = document.getElementById('download-btn');
    const uploadClickable = document.getElementById('upload-clickable');
    const optionsPanel = document.getElementById('options-panel');

    // ── Drag & drop ─────────────────────────────────────────────────────────
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
        dropArea.addEventListener(evt, preventDefaults, false);
        document.body.addEventListener(evt, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(evt =>
        dropArea.addEventListener(evt, () => dropArea.classList.add('dragover'), false)
    );
    ['dragleave', 'drop'].forEach(evt =>
        dropArea.addEventListener(evt, () => dropArea.classList.remove('dragover'), false)
    );

    dropArea.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFile(files[0]);
    }, false);

    // ── Click en área clickeable (solo el ícono + título, NO el panel de opciones) ──
    uploadClickable.addEventListener('click', () => fileInput.click());

    // Evitar que los checkboxes y el <details> propaguen el click y abran el file dialog
    if (optionsPanel) {
        optionsPanel.addEventListener('click', e => e.stopPropagation());
    }

    fileInput.addEventListener('change', function () {
        if (this.files.length > 0) handleFile(this.files[0]);
    });

    // ── Validación del archivo ───────────────────────────────────────────────
    function handleFile(file) {
        const validTypes = [
            'text/csv',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel',
            'application/vnd.ms-excel.sheet.macroEnabled.12',
            'application/vnd.ms-excel.sheet.binary.macroEnabled.12',
        ];
        const validExts = ['.csv', '.xlsx', '.xls', '.xlsm', '.xlsb'];

        const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        const isValid = validTypes.includes(file.type) || validExts.includes(ext);

        if (!isValid) {
            showError('Formato de archivo no válido. Solo se admiten archivos .csv o Excel (.xlsx, .xls).');
            return;
        }

        uploadFile(file);
    }

    // ── Recolección de opciones de limpieza ──────────────────────────────────
    function getOpciones() {
        const opciones = {};
        if (!optionsPanel) return opciones;
        optionsPanel.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            opciones[cb.name] = cb.checked;
        });
        return opciones;
    }

    // ── Upload al servidor ───────────────────────────────────────────────────
    function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('opciones', JSON.stringify(getOpciones()));

        showLoading();

        fetch('/', { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showSuccess(data.download_url);
                } else {
                    showError(data.error || 'Ocurrió un error al procesar el archivo.');
                }
            })
            .catch(() => showError('Error de conexión al servidor.'));
    }

    // ── Gestión de estados de la UI ──────────────────────────────────────────
    function showLoading() {
        uploadForm.style.display   = 'none';
        successState.style.display = 'none';
        errorState.style.display   = 'none';
        loadingState.style.display = 'block';
    }

    function showSuccess(downloadUrl) {
        loadingState.style.display = 'none';
        successState.style.display = 'block';
        downloadBtn.href = downloadUrl;
    }

    function showError(msg) {
        loadingState.style.display = 'none';
        successState.style.display = 'none';
        uploadForm.style.display   = 'none';
        errorState.style.display   = 'block';
        errorMsg.textContent = msg;
    }

    window.resetForm = function () {
        fileInput.value            = '';
        loadingState.style.display = 'none';
        successState.style.display = 'none';
        errorState.style.display   = 'none';
        uploadForm.style.display   = 'block';
    };
});
