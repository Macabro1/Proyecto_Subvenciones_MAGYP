document.getElementById("provincia").addEventListener("change", function() {

    const provinciaId = this.options[this.selectedIndex].getAttribute("data-id");

    fetch(`/cantones/${provinciaId}`)
    .then(response => response.json())
    .then(data => {

        const cantonSelect = document.getElementById("canton");
        cantonSelect.innerHTML = '<option value="">Seleccione...</option>';

        data.forEach(c => {
            cantonSelect.innerHTML += 
            `<option value="${c.nombre}" data-id="${c.id}">${c.nombre}</option>`;
        });
    });
});


document.getElementById("canton").addEventListener("change", function() {

    const cantonId = this.options[this.selectedIndex].getAttribute("data-id");

    fetch(`/parroquias/${cantonId}`)
    .then(response => response.json())
    .then(data => {

        const parroquiaSelect = document.getElementById("parroquia");
        parroquiaSelect.innerHTML = '<option value="">Seleccione...</option>';

        data.forEach(p => {
            parroquiaSelect.innerHTML += 
            `<option value="${p.nombre}">${p.nombre}</option>`;
        });
    });
});