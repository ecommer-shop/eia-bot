(function () {
  'use strict';

  var cfg = document.getElementById('cfg').dataset;
  var form = document.getElementById('form');
  var btn = document.getElementById('go');
  var statusEl = document.getElementById('status');
  var fbReady = false;
  var run = null;
  var runTimer = null;

  function show(kind, text) {
    statusEl.className = kind;
    statusEl.textContent = text;
  }

  // Meta documenta fbAsyncInit como el unico aviso fiable de que el SDK real ya
  // reemplazo al cargador provisional. Se define ANTES de insertar el script y
  // el boton solo se habilita desde ese callback (nunca por la existencia de
  // window.FB, que el cargador provisional ya define).
  window.fbAsyncInit = function () {
    window.FB.init({
      appId: cfg.appId,
      autoLogAppEvents: true,
      xfbml: false,
      version: cfg.version
    });
    fbReady = true;
    btn.disabled = false;
    btn.textContent = 'Conectar WhatsApp con Meta';
  };

  var sdk = document.createElement('script');
  sdk.src = 'https://connect.facebook.net/en_US/sdk.js';
  sdk.async = true;
  sdk.defer = true;
  sdk.crossOrigin = 'anonymous';
  sdk.onerror = function () {
    show('err', 'No se pudo cargar el SDK de Facebook. Revisa bloqueadores de anuncios o la conexión.');
  };
  document.body.appendChild(sdk);

  function finishRun() {
    run = null;
    clearTimeout(runTimer);
    btn.disabled = !fbReady;
    btn.textContent = 'Conectar WhatsApp con Meta';
  }

  function fail(text) {
    show('err', text);
    finishRun();
  }

  function trySubmit() {
    if (!run || !run.code || !run.data || run.submitted) return;
    run.submitted = true;
    show('info', 'Enviando datos a Chatwoot…');

    // El codigo de Meta vence a los 30 segundos: se envia de inmediato.
    var data = run.data;
    var body = {
      account_id: run.accountId,
      code: run.code,
      waba_id: String(data.waba_id || ''),
      business_id: data.business_id ? String(data.business_id) : null,
      phone_number_id: data.phone_number_id ? String(data.phone_number_id) : null,
      is_coexistence: run.coexistence
    };

    fetch('/onboarding/whatsapp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Onboarding-Token': run.token },
      body: JSON.stringify(body)
    }).then(function (resp) {
      return resp.json().catch(function () { return {}; }).then(function (json) {
        return { ok: resp.ok, json: json };
      });
    }).then(function (result) {
      if (result.ok && result.json.success) {
        show('ok',
          'Listo. Se creó la bandeja "' + result.json.inbox_name + '" (ID ' + result.json.inbox_id + ').\n' +
          'Siguientes pasos: asignar el bot SimetrIA a la bandeja y registrar al comercio en el gateway.');
        finishRun();
      } else {
        fail(result.json.detail || result.json.error || 'Chatwoot rechazó el alta.');
      }
    }).catch(function () {
      fail('No se pudo contactar al servidor.');
    });
  }

  function fromFacebook(origin) {
    try {
      var host = new URL(origin).hostname;
      return host === 'facebook.com' || /\.facebook\.com$/.test(host);
    } catch (e) {
      return false;
    }
  }

  function onMessage(event) {
    if (!run || !fromFacebook(event.origin)) return;

    var msg = event.data;
    if (typeof msg === 'string') {
      try { msg = JSON.parse(msg); } catch (e) { return; }
    }
    if (!msg || msg.type !== 'WA_EMBEDDED_SIGNUP') return;

    var name = String(msg.event || '');
    if (name === 'FINISH' || name === 'FINISH_WHATSAPP_BUSINESS_APP_ONBOARDING') {
      if (!msg.data || !msg.data.waba_id) {
        return fail('Meta no devolvió el identificador de la cuenta de WhatsApp Business.');
      }
      run.data = msg.data;
      trySubmit();
    } else if (name === 'CANCEL') {
      var step = msg.data && msg.data.current_step ? ' en el paso: ' + msg.data.current_step : '';
      fail('El registro se canceló' + step + '.');
    } else if (name.toUpperCase() === 'ERROR') {
      fail('Meta reportó un error: ' + ((msg.data && msg.data.error_message) || 'sin detalle') + '.');
    } else if (name.indexOf('FINISH_') === 0) {
      fail('Este tipo de registro (' + name + ') no crea una bandeja utilizable en Chatwoot.');
    }
  }

  window.addEventListener('message', onMessage);

  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    if (!fbReady || run) return;

    var token = document.getElementById('token').value.trim();
    var accountId = parseInt(document.getElementById('account').value, 10);
    if (!token || !(accountId > 0)) return show('err', 'Completa la clave y el ID de cuenta.');

    var coexistence = document.getElementById('coex').checked;
    var extras = { setup: {}, sessionInfoVersion: '3' };
    if (coexistence) extras.featureType = 'whatsapp_business_app_onboarding';

    run = { token: token, accountId: accountId, coexistence: coexistence, code: null, data: null, submitted: false };
    btn.disabled = true;
    btn.textContent = 'Esperando a Meta…';
    show('info', 'Completa el registro en la ventana de Meta.');
    runTimer = setTimeout(function () { fail('Se agotó el tiempo de espera. Intenta de nuevo.'); }, 180000);

    window.FB.login(function (response) {
      if (!run) return;
      if (response && response.authResponse && response.authResponse.code) {
        run.code = response.authResponse.code;
        trySubmit();
      } else {
        fail('El registro se cerró sin completarse.');
      }
    }, {
      config_id: cfg.configId,
      response_type: 'code',
      override_default_response_type: true,
      extras: extras
    });
  });
})();
