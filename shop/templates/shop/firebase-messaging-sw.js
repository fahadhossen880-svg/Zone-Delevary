importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging.js');

const firebaseConfig = {
    apiKey: "{{ firebase_config.api_key|escapejs }}",
    authDomain: "{{ firebase_config.auth_domain|escapejs }}",
    projectId: "{{ firebase_config.project_id|escapejs }}",
    storageBucket: "{{ firebase_config.storage_bucket|escapejs }}",
    messagingSenderId: "{{ firebase_config.messaging_sender_id|escapejs }}",
    appId: "{{ firebase_config.app_id|escapejs }}",
    measurementId: "{{ firebase_config.measurement_id|escapejs }}"
};

firebase.initializeApp(firebaseConfig);
const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
    console.log('📨 Background FCM message received:', payload);

    const { title, body, data } = payload.notification || {};
    const icon = data?.icon || '/static/images/notification-icon.png';

    const notificationOptions = {
        body: body || 'You have a new notification from ZoneDelivery',
        icon: icon,
        badge: '/static/images/badge.png',
        tag: data?.notification_id || 'zonedelivery-notification',
        requireInteraction: true,
        silent: false,
        data: data || {}
    };

    return self.registration.showNotification(title || 'ZoneDelivery', notificationOptions);
});

self.addEventListener('notificationclick', (event) => {
    console.log('🔔 Notification clicked:', event);

    event.notification.close();
    const data = event.notification.data || {};
    let url = '/notifications/';

    if (data.order_id) {
        url = `/order/${data.order_id}/`;
    } else if (data.type === 'order_status') {
        url = '/my-orders/';
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                for (let client of windowClients) {
                    if (client.url.includes(url) && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

self.addEventListener('install', (event) => {
    console.log('🔧 FCM Service Worker installing');
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    console.log('🚀 FCM Service Worker activating');
    event.waitUntil(clients.claim());
});
