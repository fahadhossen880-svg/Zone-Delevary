// Firebase SDK and FCM Configuration for Web
import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js';
import { getMessaging, getToken, onMessage } from 'https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging.js';

// Firebase configuration (same as your backend)
const firebaseConfig = {
    apiKey: "{{ firebase_config.api_key|default:'your-api-key' }}",
    authDomain: "{{ firebase_config.auth_domain|default:'your-project.firebaseapp.com' }}",
    projectId: "{{ firebase_config.project_id|default:'zone-delevary' }}",
    storageBucket: "{{ firebase_config.storage_bucket|default:'zone-delevary.appspot.com' }}",
    messagingSenderId: "{{ firebase_config.messaging_sender_id|default:'your-sender-id' }}",
    appId: "{{ firebase_config.app_id|default:'your-app-id' }}",
    measurementId: "{{ firebase_config.measurement_id|default:'your-measurement-id' }}"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const messaging = getMessaging(app);

// Request permission and get FCM token
export async function requestFCMPermission() {
    try {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            console.log('✅ Notification permission granted');

            const token = await getToken(messaging, {
                vapidKey: '{{ firebase_config.vapid_key|default:"your-vapid-key" }}'
            });

            if (token) {
                console.log('✅ FCM token obtained:', token);

                // Send token to your Django backend
                await registerFCMToken(token);
                return token;
            } else {
                console.log('❌ No FCM token available');
                return null;
            }
        } else {
            console.log('❌ Notification permission denied');
            return null;
        }
    } catch (error) {
        console.error('❌ Error getting FCM token:', error);
        return null;
    }
}

// Register FCM token with Django backend
async function registerFCMToken(token) {
    try {
        const response = await fetch('/api/register-fcm-token/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify({
                token: token,
                platform: 'web'
            })
        });

        if (response.ok) {
            console.log('✅ FCM token registered with backend');
        } else {
            console.error('❌ Failed to register FCM token');
        }
    } catch (error) {
        console.error('❌ Error registering FCM token:', error);
    }
}

// Handle foreground messages
onMessage(messaging, (payload) => {
    console.log('📨 Foreground FCM message received:', payload);

    const { title, body, data } = payload.notification || {};
    const icon = data?.icon || '/static/images/notification-icon.png';

    // Show browser notification
    if (Notification.permission === 'granted') {
        const notification = new Notification(title || 'ZoneDelivery', {
            body: body || 'You have a new notification',
            icon: icon,
            badge: '/static/images/badge.png',
            tag: data?.notification_id || 'zonedelivery-notification'
        });

        notification.onclick = function() {
            window.focus();
            notification.close();

            // Navigate based on notification type
            if (data?.order_id) {
                window.location.href = `/order/${data.order_id}/`;
            } else {
                window.location.href = '/notifications/';
            }
        };

        // Auto-close after 5 seconds
        setTimeout(() => notification.close(), 5000);
    }

    // Also show toast notification (your existing system)
    if (typeof showToastNotification === 'function') {
        showToastNotification(
            `${title}: ${body}`,
            'info',
            'fas fa-bell'
        );
    }

    // Play notification sound (your existing system)
    if (typeof playNotificationSound === 'function') {
        playNotificationSound('order-push.mp3');
    }
});

// Export for use in other scripts
window.firebaseFCM = {
    requestFCMPermission,
    messaging
};