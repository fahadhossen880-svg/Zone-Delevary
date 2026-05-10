// Firebase Service Worker for FCM Background Messages
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging.js');

// Firebase configuration (same as your web app)
const firebaseConfig = {
    apiKey: "your-api-key", // Will be replaced by Django template
    authDomain: "zone-delevary.firebaseapp.com",
    projectId: "zone-delevary",
    storageBucket: "zone-delevary.appspot.com",
    messagingSenderId: "your-sender-id",
    appId: "your-app-id"
};

// Initialize Firebase in service worker
firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// Handle background messages
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

    return self.registration.showNotification(
        title || 'ZoneDelivery',
        notificationOptions
    );
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
    console.log('🔔 Notification clicked:', event);

    event.notification.close();

    const data = event.notification.data || {};

    // Navigate based on notification type
    let url = '/notifications/';

    if (data.order_id) {
        url = `/order/${data.order_id}/`;
    } else if (data.type === 'order_status') {
        url = '/my-orders/';
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                // Check if there's already a window/tab open with the target URL
                for (let client of windowClients) {
                    if (client.url.includes(url) && 'focus' in client) {
                        return client.focus();
                    }
                }

                // If not, open a new window/tab
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

// Handle service worker installation
self.addEventListener('install', (event) => {
    console.log('🔧 FCM Service Worker installing');
    self.skipWaiting();
});

// Handle service worker activation
self.addEventListener('activate', (event) => {
    console.log('🚀 FCM Service Worker activating');
    event.waitUntil(clients.claim());
});