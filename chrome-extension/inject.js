window.addEventListener('sydia_load_modele', function(e) {
    const { idModele, idSinistre, assure } = e.detail;
    console.log('🔧 inject.js: loadModeleMail(' + idModele + ',' + idSinistre + ',' + assure + ',0)');
    
    if (typeof loadModeleMail === 'function') {
        loadModeleMail(idModele, idSinistre, assure, 0);
        console.log('✅ Modèle chargé !');
    } else {
        console.log('❌ loadModeleMail non disponible');
    }
});

window.addEventListener('sydia_new_event', function(e) {
    console.log('🔧 inject.js: newEvt()');
    
    if (typeof newEvt === 'function') {
        newEvt();
        console.log('✅ Modale événement ouverte !');
    } else {
        console.log('❌ newEvt non disponible');
    }
});

window.addEventListener('sydia_change_type', function(e) {
    const { typeId } = e.detail;
    console.log('🔧 inject.js: typeChange(' + typeId + ')');
    
    if (typeof typeChange === 'function') {
        typeChange(typeId);
        console.log('✅ Type changé !');
    } else {
        console.log('❌ typeChange non disponible');
    }
});