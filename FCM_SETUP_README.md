# Firebase Cloud Messaging (FCM) Setup for ZoneDelivery

## 📋 Overview
এই setup এর মাধ্যমে আপনার ZoneDelivery website এ FCM push notifications enable হয়েছে। এখন web browsers এ push notifications পাঠানো যাবে।

## 🔧 Required Files Added

### 1. **static/js/firebase-fcm.js**
- Firebase JavaScript SDK integration
- FCM token request and registration
- Foreground message handling
- Browser notification display

### 2. **static/js/firebase-messaging-sw.js**
- Service worker for background FCM messages
- Background notification handling
- Notification click navigation

### 3. **static/manifest.json**
- PWA manifest for web app installation
- App icons and theme configuration

### 4. **shop/views.py** (Updated)
- `register_fcm_token()` API endpoint
- FCM token registration with Django backend

### 5. **shop/urls.py** (Updated)
- `/api/register-fcm-token/` endpoint added

### 6. **shop/context_processors.py** (Updated)
- `firebase_config()` context processor
- Firebase configuration for templates

### 7. **zonedelivery/settings.py** (Updated)
- Added firebase_config context processor

### 8. **shop/templates/shop/base.html** (Updated)
- Firebase FCM scripts included
- Service worker registration
- PWA manifest link

## ⚙️ Environment Variables Required

আপনার `.env` file এ এই variables add করুন:

```env
# Firebase Web Configuration
FIREBASE_API_KEY=your_api_key_here
FIREBASE_AUTH_DOMAIN=zone-delevary.firebaseapp.com
FIREBASE_PROJECT_ID=zone-delevary
FIREBASE_STORAGE_BUCKET=zone-delevary.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
FIREBASE_MEASUREMENT_ID=your_measurement_id
FIREBASE_VAPID_KEY=your_vapid_key
```

## 🔑 Firebase Console Setup

### 1. **VAPID Key Generate করুন:**
- Firebase Console → Project Settings → Cloud Messaging
- Web Push certificates → Generate Key pair
- VAPID key কপি করে `FIREBASE_VAPID_KEY` এ set করুন

### 2. **Web App Configuration:**
- Firebase Console → Project Settings → General → Your apps
- Web app add করুন (যদি না থাকে)
- Firebase config থেকে API keys কপি করুন

## 🧪 Testing FCM

### Command Line Test:
```bash
# FCM token register করুন
python manage.py test_fcm --username your_username --token YOUR_FCM_TOKEN

# Test notification পাঠান
python manage.py test_fcm --username your_username
```

### Browser Test:
1. Website এ login করুন
2. Browser console এ check করুন FCM initialization
3. Notification permission allow করুন
4. Test notification create করে দেখুন

## 📱 How It Works

### **Web Browser Notifications:**
1. User login করে
2. FCM permission request হয়
3. Token generate হয় এবং backend এ save হয়
4. Notification create হলে FCM এর মাধ্যমে push হয়

### **Dual Notification System:**
- **Foreground:** Browser notification + Toast + Sound
- **Background:** Service worker handles push notifications

### **Notification Flow:**
```
Django → FCM API → Firebase → Service Worker → Browser Notification
```

## 🚨 Important Notes

### **HTTPS Required:**
- FCM শুধু HTTPS websites এ কাজ করে
- Development এ `localhost` এ কাজ করবে

### **Browser Support:**
- Chrome, Firefox, Edge, Safari (partial)
- iOS Safari limited support

### **Token Management:**
- Tokens automatically refresh হয়
- Invalid tokens automatically remove হয়

### **Permission Handling:**
- User যদি block করে, তাহলে silently fail হয়
- Permission আবার request করার option নেই

## 🐛 Troubleshooting

### **FCM Not Working:**
1. Check Firebase config in environment variables
2. Verify VAPID key is correct
3. Check browser console for errors
4. Ensure HTTPS is enabled

### **Service Worker Issues:**
1. Check service worker registration in DevTools → Application
2. Verify firebase-messaging-sw.js is accessible
3. Check for service worker conflicts

### **Token Registration Failed:**
1. Check CSRF token in request
2. Verify user is authenticated
3. Check Django logs for errors

## 📊 Monitoring

- FCM delivery status check করুন Firebase Console এ
- Django logs এ notification errors দেখুন
- Browser DevTools → Application → Service Workers monitor করুন

---

**✅ Setup Complete!** আপনার ZoneDelivery এখন web FCM ready!