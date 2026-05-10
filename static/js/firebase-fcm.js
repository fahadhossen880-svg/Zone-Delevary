// Firebase SDK and FCM Configuration for Web
import { initializeApp } from 'https://www.gstatic.com/firebasejs/9.22.0/firebase-app.js';
import { getMessaging, getToken, onMessage } from 'https://www.gstatic.com/firebasejs/9.22.0/firebase-messaging.js';

// Firebase configuration is injected into the page from Django env variables.
let messaging = null;

function getFirebaseConfig() {
    if (!window.firebaseConfig) {
        console.error('Firebase config is not available on window.firebaseConfig');
        return null;
    }
    return window.firebaseConfig;
}

function getMessagingInstance() {
    if (messaging) {
        return messaging;
    }

    const firebaseConfig = getFirebaseConfig();
    if (!firebaseConfig || !firebaseConfig.apiKey) {
        throw new Error('Firebase configuration is missing or incomplete. apiKey is required.');
    }

    const app = initializeApp(firebaseConfig);
    messaging = getMessaging(app);
    return messaging;
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

// Request permission and get FCM token
export async function requestFCMPermission(serviceWorkerRegistration = null) {
    try {
        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            console.log('✅ Notification permission granted');

            const tokenOptions = {
                vapidKey: window.firebaseConfig?.vapidKey || 'your-vapid-key'
            };

            if (serviceWorkerRegistration) {
                tokenOptions.serviceWorkerRegistration = serviceWorkerRegistration;
            }

            const currentMessaging = getMessagingInstance();
            const token = await getToken(currentMessaging, tokenOptions);

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

// Handle foreground messages
try {
    const messagingInstance = getMessagingInstance();
    onMessage(messagingInstance, (payload) => {
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
} catch (error) {
    console.warn('Firebase foreground messaging not initialized:', error);
}

// Export for use in other scripts
window.firebaseFCM = {
    requestFCMPermission
};