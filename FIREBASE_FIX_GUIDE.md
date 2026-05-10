# Firebase Notification 404 Error - Fix Guide

## Problem
When deploying to production, you're seeing this error:
```
Firebase push notification error: 404 Not Found
```

This means the notification is being created successfully, but **cannot sync to Firebase Realtime Database**.

## Root Causes

### ❌ Most Common Issues:
1. **FIREBASE_DATABASE_URL is not set or empty**
2. **FIREBASE_DATABASE_URL is malformed** (wrong format)
3. **Realtime Database doesn't exist** in Firebase Console
4. **Firebase credentials are invalid or incomplete**
5. **Firebase Realtime DB is in different project** than credentials

---

## ✅ Step-by-Step Fix

### Step 1: Verify Firebase Configuration

Run this command to diagnose your setup:
```bash
python manage.py test_firebase_config
```

This will show:
- ✅ Whether Firebase is initialized
- ✅ Whether Realtime Database is configured
- ✅ Whether credentials are set
- ✅ Actual error messages with details

### Step 2: Get Your Firebase Database URL

1. Go to **Firebase Console** → Your Project
2. Go to **Realtime Database**
3. Copy the Database URL (format: `https://PROJECT_ID.firebaseio.com`)

### Step 3: Set Environment Variables

#### Local Development (.env file)
```env
# Option A: If you have service account JSON file
FIREBASE_CREDENTIALS=zone-delevary-firebase-adminsdk-fbsvc-b0b84509c0.json

# Option B: Set individual credentials
FIREBASE_PROJECT_ID=zone-delevary
FIREBASE_PRIVATE_KEY_ID=fbsvc-b0b84509c0
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-fbsvc@zone-delevary.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=123456789

# REQUIRED: Database URL
FIREBASE_DATABASE_URL=https://zone-delevary.firebaseio.com
```

#### Production (Render.com, Heroku, etc.)
Add these **Environment Variables** in your platform's dashboard:

1. **FIREBASE_PROJECT_ID** = `zone-delevary`
2. **FIREBASE_PRIVATE_KEY_ID** = From service account JSON
3. **FIREBASE_PRIVATE_KEY** = From service account JSON (with newlines as `\n`)
4. **FIREBASE_CLIENT_EMAIL** = From service account JSON
5. **FIREBASE_CLIENT_ID** = From service account JSON
6. **FIREBASE_DATABASE_URL** = `https://zone-delevary.firebaseio.com`

### Step 4: Get Service Account JSON

1. Go to **Firebase Console** → **Project Settings** (gear icon)
2. Click **Service Accounts** tab
3. Click **Generate New Private Key**
4. Save the downloaded JSON file

The file contains:
```json
{
  "type": "service_account",
  "project_id": "zone-delevary",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@zone-delevary.iam.gserviceaccount.com",
  "client_id": "...",
  ...
}
```

### Step 5: Test the Connection

After setting environment variables, run:
```bash
python manage.py test_firebase_config
```

You should see:
```
✅ Firebase App initialized
✅ Database write test: SUCCESS
✅ Storage bucket accessible: zone-delevary.appspot.com
```

### Step 6: Restart Your Application

- **Local:** Restart Django development server
- **Production:** Redeploy or restart your server

---

## 🔧 Troubleshooting

### Error: "404 Not Found"
**Fix:** Check your FIREBASE_DATABASE_URL
```
❌ Wrong: https://zone-delevary.firebaseio.com/ (trailing slash)
✅ Correct: https://zone-delevary.firebaseio.com (no trailing slash)

❌ Wrong: https://zone-delivery.firebaseio.com (wrong project ID)
✅ Correct: https://zone-delevary.firebaseio.com
```

### Error: "FIREBASE_DATABASE_URL is not configured"
**Fix:** Add to your environment:
```bash
export FIREBASE_DATABASE_URL="https://zone-delevary.firebaseio.com"
```

Or add to `.env`:
```env
FIREBASE_DATABASE_URL=https://zone-delevary.firebaseio.com
```

### Error: "Firebase initialization error"
**Fix:** Ensure credentials are properly set:
```bash
python manage.py test_firebase_config
```

Check the diagnostic output for missing credentials.

### Error: "private_key format is invalid"
**Fix:** In environment variables, replace actual newlines with `\n`:

❌ Wrong:
```env
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
MIIEvQI...
-----END PRIVATE KEY-----"
```

✅ Correct:
```env
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nMIIEvQI...\n-----END PRIVATE KEY-----\n"
```

---

## 📊 Notification System Flow

```
Order Created
    ↓
create_notification()
    ↓
1. Create in Database ✅ (Always works)
    ↓
2. Sync to Firebase ⚠️ (May fail if not configured)
    ↓
3. Send Email ⚠️ (Depends on EMAIL_BACKEND)
    ↓
Notification Complete
```

**Important:** If Firebase sync fails, **the notification is still created** in your database. Only the real-time sync feature is affected.

---

## 📝 Firebase Security Rules

For proper security, set these rules in Firebase Console:

```json
{
  "rules": {
    "notifications": {
      "$uid": {
        ".read": "$uid === auth.uid",
        ".write": "root.child('users').child(auth.uid).child('role').val() === 'admin' || $uid === auth.uid"
      }
    },
    "locations": {
      "$uid": {
        ".read": true,
        ".write": "$uid === auth.uid || root.child('users').child(auth.uid).child('role').val() === 'admin'"
      }
    }
  }
}
```

---

## ✅ Verification Checklist

- [ ] FIREBASE_DATABASE_URL is set and correct format
- [ ] FIREBASE_PROJECT_ID matches the database URL
- [ ] Service account credentials are set (all required fields)
- [ ] `python manage.py test_firebase_config` shows all ✅
- [ ] Realtime Database exists in Firebase Console
- [ ] Security rules are properly configured
- [ ] Application has been restarted after env changes

---

## 🆘 Still Having Issues?

1. **Check browser console** for any client-side errors
2. **Check server logs** for Firebase initialization messages
3. **Run diagnostic command:** `python manage.py test_firebase_config`
4. **Check Firebase Console** for any database issues
5. **Verify credentials** by running: `echo $FIREBASE_DATABASE_URL`

---

## 📚 Additional Resources

- [Firebase Realtime Database Docs](https://firebase.google.com/docs/database)
- [Firebase Admin SDK Setup](https://firebase.google.com/docs/admin/setup)
- [Django-Firebase Integration](https://github.com/firebase/firebase-admin-python)
