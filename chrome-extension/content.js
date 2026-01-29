console.log('🔌 Sydia MCP V5 - Modèles de mail Sydia');

const actionsHistory = [];

function createHistoryPanel() {
    const existing = document.getElementById('sydia-history-panel');
    if (existing) existing.remove();
    
    const panel = document.createElement('div');
    panel.id = 'sydia-history-panel';
    panel.innerHTML = `
        <div id="sydia-history-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;cursor:pointer;">
            <span style="font-weight:700;">🤖 Agent IA - Historique</span>
            <span id="sydia-history-toggle">▼</span>
        </div>
        <div id="sydia-history-content"></div>
    `;
    panel.style.cssText = `
        position: fixed !important;
        bottom: 20px !important;
        left: 20px !important;
        width: 320px;
        background: linear-gradient(145deg, #1e1e2e, #2d2d3f);
        color: white;
        padding: 16px;
        border-radius: 16px;
        font-family: system-ui, sans-serif;
        font-size: 12px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.4);
        z-index: 2147483647 !important;
        border: 1px solid rgba(139,92,246,0.3);
    `;
    document.body.appendChild(panel);
    
    document.getElementById('sydia-history-header').addEventListener('click', () => {
        const content = document.getElementById('sydia-history-content');
        const toggle = document.getElementById('sydia-history-toggle');
        if (content.style.display === 'none') {
            content.style.display = 'block';
            toggle.textContent = '▼';
        } else {
            content.style.display = 'none';
            toggle.textContent = '▶';
        }
    });
    
    return panel;
}

function addToHistory(icon, message, detail) {
    const now = new Date();
    const time = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    
    actionsHistory.unshift({ time, icon, message, detail });
    if (actionsHistory.length > 10) actionsHistory.pop();
    
    updateHistoryPanel();
}

function updateHistoryPanel() {
    const content = document.getElementById('sydia-history-content');
    if (!content) return;
    
    if (actionsHistory.length === 0) {
        content.innerHTML = '<div style="opacity:0.5;text-align:center;padding:10px;">Aucune action</div>';
        return;
    }
    
    content.innerHTML = actionsHistory.map(a => `
        <div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.1);display:flex;gap:10px;align-items:flex-start;">
            <span style="opacity:0.5;font-size:10px;">${a.time}</span>
            <span>${a.icon}</span>
            <div style="flex:1;">
                <div>${a.message}</div>
                ${a.detail ? '<div style="opacity:0.5;font-size:10px;margin-top:2px;">' + a.detail + '</div>' : ''}
            </div>
        </div>
    `).join('');
}

createHistoryPanel();
addToHistory('🔌', 'Extension chargée', 'En attente de connexion...');

const socket = io('http://localhost:5000', {
    transports: ['polling', 'websocket']
});

socket.on('connect', () => {
    console.log('✅ WebSocket connecté !');
    showToast('🟢 Agent IA connecté', 'info');
    addToHistory('🟢', 'Connecté au serveur', 'WebSocket actif');
});

socket.on('disconnect', () => {
    console.log('❌ WebSocket déconnecté');
    addToHistory('🔴', 'Déconnecté', 'Tentative de reconnexion...');
});

socket.on('sydia_update', (data) => {
    console.log('📡 MISE À JOUR REÇUE !', data);
    handleUpdate(data);
});

function handleUpdate(data) {
    const { action, endpoint, fields } = data;
    
    if (endpoint === 'assure/update' && fields) {
        updateFieldsLive(fields);
        const fieldNames = Object.keys(fields).join(', ');
        showToast('✅ ' + fieldNames + ' modifié(s)', 'success');
        addToHistory('✏️', fieldNames + ' modifié(s)', Object.entries(fields).map(([k,v]) => k + ': ' + v).join(', '));
    }
    else if (endpoint === 'sinistre/contact') {
        showToast('📞 Demande envoyée au gestionnaire', 'success');
        showModal('Demande créée', 'Le gestionnaire a été notifié et vous rappellera bientôt.');
        addToHistory('📞', 'Demande de rappel créée', 'Gestionnaire notifié');
    }
    else if (endpoint === 'sinistre/cloturer') {
        showToast('🔴 Dossier clôturé', 'warning');
        showModal('Dossier clôturé', 'Ce sinistre est maintenant fermé.', true);
        addToHistory('🔴', 'Sinistre clôturé', '');
    }
    else if (endpoint === 'ged/add') {
        showToast('📎 Document ajouté', 'success');
        addToHistory('📎', 'Document ajouté', '');
    }
    else if (endpoint === 'mail/prepare') {
        showToast('📧 Ouverture modale mail...', 'info');
        const mailData = data.data || data.fields || {};
        console.log('📧 Mail data:', mailData);
        openSydiaMailModal(mailData);
    }
    else if (endpoint === 'evenement/create') {
        showToast('📅 Ouverture modale événement...', 'info');
        const evtData = data.data || data.fields || {};
        console.log('📅 Event data:', evtData);
        openEventModal(evtData);
    }
    else {
        showToast('✅ ' + action, 'success');
        addToHistory('✅', action, '');
    }
}

function updateFieldsLive(fields) {
    const mapping = {
        'tel1': 'assure_tel1',
        'tel2': 'assure_tel2',
        'email': 'assure_email',
        'adresse': 'assure_adresse',
        'cp': 'assure_cp',
        'ville': 'assure_ville'
    };
    
    const labels = {
        'tel1': 'Téléphone',
        'tel2': 'Téléphone 2',
        'email': 'Email',
        'adresse': 'Adresse',
        'cp': 'Code postal',
        'ville': 'Ville'
    };
  
    Object.keys(fields).forEach((key, index) => {
        const inputId = mapping[key];
        if (!inputId) return;
        
        const input = document.getElementById(inputId);
        if (!input) {
            console.log('⚠️ Champ non trouvé:', inputId);
            return;
        }
        
        const oldValue = input.value;
        const newValue = fields[key];
        
        setTimeout(() => {
            input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            setTimeout(() => {
                showOldValueBadge(input, oldValue, newValue, labels[key] || key);
                
                setTimeout(() => {
                    input.value = newValue;
                    highlightField(input);
                }, 300);
                
            }, 500);
            
        }, index * 1000);
        
        console.log('✅ ' + key + ': ' + oldValue + ' → ' + newValue);
    });
}

function highlightField(input) {
    input.style.transition = 'all 0.3s ease';
    input.style.boxShadow = '0 0 0 3px #34d399, 0 0 20px #34d399';
    input.style.borderColor = '#34d399';
    input.style.backgroundColor = 'rgba(52, 211, 153, 0.1)';
    input.style.transform = 'scale(1.02)';
    
    let pulseCount = 0;
    const pulse = setInterval(() => {
        input.style.boxShadow = pulseCount % 2 === 0 
            ? '0 0 0 3px #34d399, 0 0 30px #34d399' 
            : '0 0 0 3px #34d399, 0 0 10px #34d399';
        pulseCount++;
        if (pulseCount > 6) clearInterval(pulse);
    }, 300);
    
    setTimeout(() => {
        input.style.boxShadow = '';
        input.style.borderColor = '';
        input.style.backgroundColor = '';
        input.style.transform = '';
    }, 4000);
}

function showOldValueBadge(input, oldValue, newValue, label) {
    document.querySelectorAll('.sydia-old-value').forEach(b => b.remove());
    
    const badge = document.createElement('div');
    badge.className = 'sydia-old-value';
    badge.innerHTML = `
        <div style="font-weight:600;margin-bottom:4px;">✏️ ${label} modifié par l'Agent IA</div>
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="text-decoration:line-through;opacity:0.6;">${oldValue || '(vide)'}</span>
            <span style="color:#34d399;">→</span>
            <span style="color:#34d399;font-weight:600;">${newValue}</span>
        </div>
    `;
    badge.style.cssText = `
        position: fixed !important;
        z-index: 2147483647 !important;
        background: linear-gradient(145deg, #1e1e2e, #2d2d3f);
        color: white;
        padding: 12px 16px;
        border-radius: 12px;
        font-family: system-ui, sans-serif;
        font-size: 12px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.4);
        border: 2px solid #34d399;
        animation: badgeIn 0.3s ease;
    `;
    
    const rect = input.getBoundingClientRect();
    badge.style.top = (rect.top - 70 + window.scrollY) + 'px';
    badge.style.left = rect.left + 'px';
    
    if (!document.getElementById('sydia-badge-style')) {
        const style = document.createElement('style');
        style.id = 'sydia-badge-style';
        style.textContent = '@keyframes badgeIn{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}';
        document.head.appendChild(style);
    }
    
    document.body.appendChild(badge);
    
    setTimeout(() => {
        badge.style.opacity = '0';
        badge.style.transition = 'opacity 0.3s';
        setTimeout(() => badge.remove(), 300);
    }, 5000);
}

function showToast(message, type) {
    const existing = document.getElementById('sydia-toast');
    if (existing) existing.remove();
    
    const colors = {
        success: 'linear-gradient(135deg, #10b981, #059669)',
        info: 'linear-gradient(135deg, #8b5cf6, #06b6d4)',
        warning: 'linear-gradient(135deg, #f59e0b, #d97706)',
        error: 'linear-gradient(135deg, #ef4444, #dc2626)'
    };
    
    const toast = document.createElement('div');
    toast.id = 'sydia-toast';
    toast.innerHTML = '<div style="display:flex;align-items:center;gap:10px;"><span style="font-size:20px;">🤖</span><span>' + message + '</span></div>';
    toast.style.cssText = `
        position: fixed !important;
        bottom: 30px !important;
        right: 30px !important;
        background: ${colors[type] || colors.info};
        color: white;
        padding: 16px 24px;
        border-radius: 12px;
        font-family: system-ui, sans-serif;
        font-size: 14px;
        font-weight: 600;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        z-index: 2147483647 !important;
        animation: slideIn 0.5s ease;
    `;
    
    if (!document.getElementById('sydia-toast-style')) {
        const style = document.createElement('style');
        style.id = 'sydia-toast-style';
        style.textContent = '@keyframes slideIn{from{opacity:0;transform:translateX(100px)}to{opacity:1;transform:translateX(0)}}@keyframes slideOut{from{opacity:1;transform:translateX(0)}to{opacity:0;transform:translateX(100px)}}';
        document.head.appendChild(style);
    }
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function showModal(title, message, isWarning) {
    const existing = document.getElementById('sydia-modal');
    if (existing) existing.remove();
    
    const modal = document.createElement('div');
    modal.id = 'sydia-modal';
    
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:2147483647;';
    overlay.addEventListener('click', () => modal.remove());
    
    const box = document.createElement('div');
    box.style.cssText = 'background:linear-gradient(145deg,#1e1e2e,#2d2d3f);color:white;padding:32px 40px;border-radius:20px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,0.4);max-width:400px;animation:modalIn 0.3s ease;';
    box.addEventListener('click', (e) => e.stopPropagation());
    
    box.innerHTML = `
        <div style="font-size:48px;margin-bottom:16px;">${isWarning ? '⚠️' : '✅'}</div>
        <h2 style="margin:0 0 12px 0;font-size:20px;">${title}</h2>
        <p style="margin:0 0 24px 0;opacity:0.7;font-size:14px;line-height:1.5;">${message}</p>
    `;
    
    const btn = document.createElement('button');
    btn.textContent = 'Compris !';
    btn.style.cssText = 'background:linear-gradient(135deg,#8b5cf6,#06b6d4);color:white;border:none;padding:12px 32px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;';
    btn.addEventListener('click', () => modal.remove());
    
    box.appendChild(btn);
    overlay.appendChild(box);
    modal.appendChild(overlay);
    
    if (!document.getElementById('sydia-modal-style')) {
        const style = document.createElement('style');
        style.id = 'sydia-modal-style';
        style.textContent = '@keyframes modalIn{from{opacity:0;transform:scale(0.9)}to{opacity:1;transform:scale(1)}}';
        document.head.appendChild(style);
    }
    
    document.body.appendChild(modal);
}

function openSydiaMailModal(data) {
    console.log('📧 Ouverture modale Sydia...', data);
    
    // Extraire l'ID du sinistre depuis l'URL
    const urlMatch = window.location.href.match(/sinistre[s]?\/(\d+)/);
    const idSinistre = urlMatch ? urlMatch[1] : null;
    
    if (!idSinistre) {
        console.log('ℹ️ Pas sur un dossier sinistre');
        showToast('📧 Ouvrez un dossier pour envoyer un mail', 'warning');
        addToHistory('⚠️', 'Mail non envoyé', 'Ouvrez un dossier sinistre');
        return;
    }
    
    console.log('📧 ID Sinistre:', idSinistre);
    console.log('📧 ID Modèle:', data.id_modele);
    
    if (typeof newEmail === 'function') {
        console.log('✅ Appel newEmail(' + idSinistre + ')');
        newEmail(idSinistre);
        
        if (data.id_modele) {
            setTimeout(() => {
                loadModele(data.id_modele, idSinistre, data.id_assure);
            }, 3000);
        } else {
            showToast('📧 Modale ouverte !', 'success');
            addToHistory('📧', 'Modale mail ouverte', 'Sélectionnez un modèle');
        }
    } else {
        const newEmailBtn = document.querySelector('a[onclick*="newEmail"], [data-original-title="Rédiger un email"]');
        if (newEmailBtn) {
            console.log('✅ Clic sur bouton newEmail');
            newEmailBtn.click();
            
            if (data.id_modele) {
                setTimeout(() => {
                    loadModele(data.id_modele, idSinistre);
                }, 1500);
            } else {
                showToast('📧 Modale ouverte !', 'success');
                addToHistory('📧', 'Modale mail ouverte', 'Sélectionnez un modèle');
            }
        } else {
            console.log('❌ Impossible d\'ouvrir la modale');
            showToast('❌ Bouton mail non trouvé', 'error');
        }
    }
}

function loadModele(idModele, idSinistre, idAssure) {
    console.log('📄 Chargement modèle:', idModele, 'sinistre:', idSinistre, 'assure:', idAssure);
    
    const assure = idAssure || 0;
    
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('inject.js');
    script.onload = function() {
        const event = new CustomEvent('sydia_load_modele', {
            detail: { idModele, idSinistre, assure }
        });
        window.dispatchEvent(event);
        this.remove();
    };
    (document.head || document.documentElement).appendChild(script);
    
    showToast('📧 Modèle chargé !', 'success');
    addToHistory('📧', 'Modèle mail chargé', 'ID: ' + idModele);
}

function openEventModal(data) {
    console.log('📅 Ouverture modale événement...', data);
    console.log('📅 Type événement:', data.type_evenement);
    console.log('📅 Date:', data.date);
    console.log('📅 Heure:', data.heure);
    
    const urlMatch = window.location.href.match(/sinistre[s]?\/(\d+)/);
    if (!urlMatch) {
        showToast('📅 Ouvrez un dossier pour créer un événement', 'warning');
        addToHistory('⚠️', 'Événement non créé', 'Ouvrez un dossier sinistre');
        return;
    }
    
    const script = document.createElement('script');
    script.src = chrome.runtime.getURL('inject.js');
    script.onload = function() {
        const event = new CustomEvent('sydia_new_event', {
            detail: { commentaire: data.commentaire }
        });
        window.dispatchEvent(event);
        this.remove();
    };
    (document.head || document.documentElement).appendChild(script);
    
    setTimeout(() => {
        if (data.type_evenement) {
            fillEventType(data.type_evenement);
        }
        if (data.date) {
            fillEventDate(data.date);
        }
        if (data.heure) {
            fillEventHeure(data.heure);
        }
        fillEventComment(data.commentaire);
    }, 1500);
    
    addToHistory('📅', 'Événement préparé', data.commentaire ? data.commentaire.substring(0, 50) + '...' : '');
}

function fillEventType(typeId) {
    if (!typeId) return;
    
    console.log('📝 Sélection type événement...', typeId);
    
    const select = document.getElementById('evt_type');
    
    if (select) {
        select.value = typeId;
        
        select.dispatchEvent(new Event('change', { bubbles: true }));
        
        const script = document.createElement('script');
        script.src = chrome.runtime.getURL('inject.js');
        script.onload = function() {
            const event = new CustomEvent('sydia_change_type', {
                detail: { typeId: typeId }
            });
            window.dispatchEvent(event);
            this.remove();
        };
        (document.head || document.documentElement).appendChild(script);
        
        console.log('✅ Type événement sélectionné:', typeId);
    } else {
        console.log('⚠️ Select evt_type non trouvé');
    }
}

function fillEventComment(commentaire) {
    if (!commentaire) return;
    
    console.log('📝 Remplissage commentaire événement...', commentaire);
    
    const textarea = document.getElementById('evt_commentaire');
    
    if (textarea) {
        console.log('✅ Textarea evt_commentaire trouvé !');
        
        textarea.focus();
        textarea.click();
        
        textarea.value = commentaire;
        
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
        textarea.dispatchEvent(new Event('keyup', { bubbles: true }));
        textarea.dispatchEvent(new Event('keydown', { bubbles: true }));
        textarea.dispatchEvent(new Event('blur', { bubbles: true }));
        
        textarea.setAttribute('value', commentaire);
        
        console.log('✅ Commentaire rempli !', textarea.value);
        showToast('📅 Événement pré-rempli !', 'success');
    } else {
        console.log('❌ Textarea evt_commentaire non trouvé !');
        showToast('📅 Modale ouverte, collez le commentaire', 'info');
    }
}
function fillEventDate(date) {
    if (!date) return;
    
    console.log('📅 Remplissage date événement...', date);
    
    const dateInput = document.getElementById('evt_date');
    
    if (dateInput) {
        dateInput.focus();
        dateInput.value = date;
        dateInput.dispatchEvent(new Event('input', { bubbles: true }));
        dateInput.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('✅ Date remplie:', date);
    } else {
        console.log('⚠️ Input evt_date non trouvé');
    }
}

function fillEventHeure(heure) {
    if (!heure) return;
    
    console.log('🕐 Remplissage heure événement...', heure);
    
    const heureInput = document.getElementById('evt_heure');
    
    if (heureInput) {
        heureInput.focus();
        heureInput.value = heure;
        heureInput.dispatchEvent(new Event('input', { bubbles: true }));
        heureInput.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('✅ Heure remplie:', heure);
    } else {
        console.log('⚠️ Input evt_heure non trouvé');
    }
}
console.log('🎉 Sydia MCP V5 - Prêt !');